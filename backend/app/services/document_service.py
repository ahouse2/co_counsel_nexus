from pathlib import Path
from typing import List, Optional, Union, Dict
import uuid
import dataclasses

from backend.app.storage.document_store import DocumentStore
from backend.app.models.api import IngestionSource, SourceType
from backend.ingestion.pipeline import run_ingestion_pipeline
from backend.ingestion.loader_registry import LoaderRegistry
from backend.ingestion.settings import LlamaIndexRuntimeConfig

class DocumentService:
    """
    Service layer for managing documents, including storage, retrieval, and ingestion.
    """
    def __init__(
        self, 
        document_store: DocumentStore, 
        loader_registry: LoaderRegistry,
        runtime_config: LlamaIndexRuntimeConfig,
        materialized_root: Path,
    ):
        self.document_store = document_store
        self.loader_registry = loader_registry
        self.runtime_config = runtime_config
        self.materialized_root = materialized_root

    async def upload_document(
        self,
        case_id: str,
        doc_type: str,
        file_content: bytes,
        file_name: str,
        author: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        custom_metadata: Optional[dict] = None,
        relative_path: Optional[str] = None,
        origin: str = "upload",
        api_keys: Optional[Dict[str, str]] = None,
        run_pipeline: bool = True,
    ) -> dict:
        doc_id = str(uuid.uuid4())
        version = self.document_store.save_document(
            doc_type,
            case_id,
            doc_id,
            file_content,
            file_name,
            author,
            keywords,
            tags,
            custom_metadata,
            relative_path 
        )

        # Stage the file for ingestion in the materialized_root
        job_dir = self.materialized_root / doc_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        staged_file_path = job_dir / file_name
        staged_file_path.write_bytes(file_content)

        ingestion_source = IngestionSource(
            source_id=doc_id,
            type=SourceType.FILE,
            uri=str(staged_file_path),
            metadata={
                "case_id": case_id,
                "doc_type": doc_type,
                "file_name": file_name,
                "version": version,
                "author": author,
                "keywords": keywords,
                "tags": tags,
                "custom_metadata": custom_metadata,
                "relative_path": relative_path,
            }
        )

        pipeline_result = None
        if run_pipeline:
            pipeline_result = self.process_ingestion(doc_id, ingestion_source, origin, api_keys)

        return {
            "doc_id": doc_id,
            "version": version,
            "case_id": case_id,
            "doc_type": doc_type,
            "file_name": file_name,
            "ingestion_status": "completed" if run_pipeline else "queued",
            "pipeline_result": pipeline_result.documents[0].categories if pipeline_result and pipeline_result.documents else [],
            "ingestion_source": ingestion_source,
            "origin": origin,
            "api_keys": api_keys,
        }

    def process_ingestion(
        self,
        doc_id: str,
        source: IngestionSource,
        origin: str,
        api_keys: Optional[Dict[str, str]] = None
    ):
        # Update runtime config with API keys if provided
        current_config = self.runtime_config
        if api_keys:
            key_to_use = api_keys.get("gemini_api_key") or api_keys.get("courtlistener_api_key")
            
            if key_to_use:
                new_llm_config = dataclasses.replace(
                    current_config.llm, 
                    api_key=key_to_use
                )
                new_embedding_config = dataclasses.replace(
                    current_config.embedding,
                    api_key=key_to_use
                )
                new_ocr_config = dataclasses.replace(
                    current_config.ocr,
                    api_key=key_to_use,
                    vision_model=current_config.default_vision_model
                )
                current_config = dataclasses.replace(
                    current_config,
                    llm=new_llm_config,
                    embedding=new_embedding_config,
                    ocr=new_ocr_config
                )

        job_dir = self.materialized_root / doc_id
        
        try:
            # Update status to processing
            self.document_store.update_document_status(
                source.metadata.get("doc_type"),
                source.metadata.get("case_id"),
                doc_id,
                "processing"
            )

            pipeline_result = run_ingestion_pipeline(
                job_id=doc_id, 
                materialized_root=job_dir, 
                source=source,
                origin=origin,
                registry=self.loader_registry,
                runtime_config=current_config,
            )
            
            # Update status to completed
            self.document_store.update_document_status(
                source.metadata.get("doc_type"),
                source.metadata.get("case_id"),
                doc_id,
                "completed"
            )
            
            return pipeline_result
        except Exception as e:
            # Update status to failed
            self.document_store.update_document_status(
                source.metadata.get("doc_type"),
                source.metadata.get("case_id"),
                doc_id,
                "failed"
            )
            raise e
        finally:
            # Cleanup staged file after ingestion (optional)
            pass

    def get_document(self, case_id: str, doc_type: str, doc_id: str, version: Optional[str] = None) -> Optional[str]:
        return self.document_store.get_document(doc_type, case_id, doc_id, version)

    def list_document_versions(self, case_id: str, doc_type: str, doc_id: str) -> List[str]:
        return self.document_store.list_document_versions(doc_type, case_id, doc_id)

    def delete_document(self, case_id: str, doc_type: str, doc_id: str, version: Optional[str] = None):
        self.document_store.delete_document(doc_type, case_id, doc_id, version)

    def list_all_documents(self, case_id: str) -> List[dict]:
        """
        Lists all documents for a given case.
        """
        return self.document_store.list_all_documents(case_id)

    async def upload_directory(
        self,
        case_id: str,
        zip_content: bytes,
        api_keys: Optional[Dict[str, str]] = None,
    ) -> List[dict]:
        import zipfile
        import io
        
        results = []
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                for filename in z.namelist():
                    if filename.endswith('/') or filename.startswith('__MACOSX') or filename.startswith('.'):
                        continue
                    
                    file_content = z.read(filename)
                    # Use the filename as the relative path if it contains directories
                    relative_path = str(Path(filename).parent) if '/' in filename else None
                    base_filename = Path(filename).name
                    
                    result = await self.upload_document(
                        case_id=case_id,
                        doc_type="my_documents",
                        file_content=file_content,
                        file_name=base_filename,
                        relative_path=relative_path,
                        origin="folder_upload",
                        api_keys=api_keys,
                        run_pipeline=False # Queue for background processing
                    )
                    results.append(result)
        except zipfile.BadZipFile:
            raise ValueError("Invalid zip file")
            
        return results
