from pathlib import Path
from typing import List, Optional, Union, Dict, BinaryIO
import asyncio
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
        import hashlib
        
        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        
        # Extract basic forensic metadata
        forensic_metadata = {
            "size_bytes": len(file_content),
            "sha256": sha256_hash,
            "magic_bytes": file_content[:16].hex(), # First 16 bytes for file type verification
        }

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
            relative_path,
            hash_sha256=sha256_hash,
            forensic_metadata=forensic_metadata
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
                "hash_sha256": sha256_hash,
                "forensic_metadata": forensic_metadata,
            }
        )

        pipeline_result = None
        if run_pipeline:
            pipeline_result = await self.process_ingestion(doc_id, ingestion_source, origin, api_keys)

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

    async def process_ingestion(
        self,
        doc_id: str,
        source: IngestionSource,
        origin: str,
        api_keys: Optional[Dict[str, str]] = None
    ):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Starting ingestion for doc_id={doc_id}, origin={origin}")
        
        # Update runtime config with API keys if provided
        current_config = self.runtime_config
        if api_keys:
            key_to_use = api_keys.get("gemini_api_key") or api_keys.get("courtlistener_api_key")
            
            if key_to_use:
                logger.debug(f"Using API key for doc_id={doc_id}")
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
            logger.info(f"Updating status to 'processing' for doc_id={doc_id}")
            self.document_store.update_document_status(
                source.metadata.get("doc_type"),
                source.metadata.get("case_id"),
                doc_id,
                "processing"
            )

            logger.info(f"Running ingestion pipeline for doc_id={doc_id}, file={source.uri}")
            
            # Run the synchronous pipeline in a separate thread to avoid blocking the event loop
            import asyncio
            pipeline_result = await asyncio.to_thread(
                run_ingestion_pipeline,
                job_id=doc_id, 
                materialized_root=job_dir, 
                source=source,
                origin=origin,
                registry=self.loader_registry,
                runtime_config=current_config,
            )
            
            # Check for suspicious documents and trigger deep forensics
            if pipeline_result and pipeline_result.documents:
                for doc_result in pipeline_result.documents:
                    if doc_result.screening_result and doc_result.screening_result.is_suspicious:
                        logger.warning(f"Document {doc_id} flagged as suspicious. Triggering deep forensics.")
                        # We need to trigger this asynchronously.
                        # Since `process_ingestion` is already async/background, we can just call it?
                        # Or better, spawn another task to not block this one if we want "fire and forget".
                        # But `process_ingestion` is the background task.
                        # Let's instantiate ForensicsService and run it.
                        
                        from backend.app.services.forensics_service import ForensicsService
                        forensics_service = ForensicsService(self.settings, self.document_store)
                        
                        # We can await it here, effectively making it part of the ingestion flow for flagged docs.
                        # Or we can use `asyncio.create_task` to let it run in parallel/background.
                        # User said "separate, asynch 'branch'".
                        import asyncio
                        asyncio.create_task(forensics_service.run_deep_forensics(
                            doc_id=doc_id, 
                            case_id=source.metadata.get("case_id")
                        ))

            # Update status to completed
            logger.info(f"Ingestion completed successfully for doc_id={doc_id}")
            self.document_store.update_document_status(
                source.metadata.get("doc_type"),
                source.metadata.get("case_id"),
                doc_id,
                "completed"
            )
            
            # Trigger Intelligence Service
            try:
                from backend.app.services.intelligence_service import IntelligenceService
                intelligence_service = IntelligenceService()
                
                # Extract text from pipeline result
                doc_text = ""
                if pipeline_result and pipeline_result.documents:
                    doc_text = pipeline_result.documents[0].loaded.text
                
                if doc_text:
                    # Run in background to not block response if this was awaited directly (though process_ingestion is usually background)
                    # Since process_ingestion is already a background task, we can await it or spawn another task.
                    # Spawning another task is safer to isolate failures and speed up this function's return if it was awaited.
                    asyncio.create_task(intelligence_service.on_document_ingested(
                        case_id=source.metadata.get("case_id"),
                        doc_id=doc_id,
                        doc_text=doc_text,
                        metadata=source.metadata
                    ))
            except Exception as e:
                logger.error(f"Failed to trigger intelligence service for {doc_id}: {e}", exc_info=True)
            
            return pipeline_result
        except Exception as e:
            # Update status to failed
            logger.error(f"Ingestion failed for doc_id={doc_id}: {str(e)}", exc_info=True)
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
        zip_content: Union[bytes, BinaryIO],
        api_keys: Optional[Dict[str, str]] = None,
    ) -> List[dict]:
        import zipfile
        import io
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Starting directory upload for case_id={case_id}")
        
        results = []
        try:
            if isinstance(zip_content, bytes):
                f = io.BytesIO(zip_content)
            else:
                f = zip_content

            with zipfile.ZipFile(f) as z:
                file_list = z.namelist()
                logger.info(f"Zip contains {len(file_list)} entries")
                
                for idx, filename in enumerate(file_list):
                    # Yield control to event loop to prevent blocking
                    await asyncio.sleep(0)
                    
                    # Skip directories and system files
                    if filename.endswith('/') or filename.startswith('__MACOSX') or filename.startswith('.'):
                        logger.debug(f"Skipping {filename} (directory or system file)")
                        continue
                    
                    try:
                        file_content = z.read(filename)
                        # Use the filename as the relative path if it contains directories
                        relative_path = str(Path(filename).parent) if '/' in filename else None
                        base_filename = Path(filename).name
                        
                        logger.info(f"Processing file {idx+1}/{len(file_list)}: {filename} ({len(file_content)} bytes)")
                        
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
                        logger.debug(f"Successfully queued {base_filename} for ingestion (doc_id={result['doc_id']})")
                        
                    except Exception as e:
                        logger.error(f"Failed to process file {filename}: {str(e)}", exc_info=True)
                        # Continue processing other files even if one fails
                        continue
                        
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file received for case_id={case_id}: {str(e)}")
            raise ValueError("Invalid zip file")
        except Exception as e:
            logger.error(f"Unexpected error during directory upload: {str(e)}", exc_info=True)
            raise
            
        logger.info(f"Directory upload completed: {len(results)} files queued for ingestion")
        return results
    async def ingest_local_directory(
        self,
        case_id: str,
        directory_path: str,
        api_keys: Optional[Dict[str, str]] = None,
    ) -> List[dict]:
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        # Ensure path is within /data for security (basic check)
        base_path = Path("/data")
        target_path = base_path / directory_path
        
        if not str(target_path).startswith(str(base_path)):
             raise ValueError("Access denied: Path must be within /data")
             
        if not target_path.exists() or not target_path.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")

        logger.info(f"Starting local directory ingestion for case_id={case_id}, path={target_path}")
        
        results = []
        for root, dirs, files in os.walk(target_path):
            for filename in files:
                # Skip system files
                if filename.startswith('.'):
                    continue
                    
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(target_path).parent
                
                try:
                    file_content = file_path.read_bytes()
                    
                    logger.info(f"Processing local file: {filename} ({len(file_content)} bytes)")
                    
                    result = await self.upload_document(
                        case_id=case_id,
                        doc_type="my_documents",
                        file_content=file_content,
                        file_name=filename,
                        relative_path=str(relative_path) if str(relative_path) != "." else None,
                        origin="local_ingestion",
                        api_keys=api_keys,
                        run_pipeline=False # Queue for background processing
                    )
                    results.append(result)
                    logger.debug(f"Successfully queued {filename} for ingestion (doc_id={result['doc_id']})")
                    
                except Exception as e:
                    logger.error(f"Failed to process file {filename}: {str(e)}", exc_info=True)
                    continue
        
        logger.info(f"Local directory ingestion completed: {len(results)} files queued")
        return results
