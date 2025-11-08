from pathlib import Path
from typing import List, Optional, Union
import uuid

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
        origin: str = "upload",
    ) -> dict:
        doc_id = str(uuid.uuid4())
        version = self.document_store.save_document(
            doc_type,
            case_id,
            doc_id,
            file_content,
            author,
            keywords,
            tags,
            custom_metadata
        )

        # Trigger ingestion pipeline
        # For simplicity, we're creating a basic IngestionSource here.
        # In a real app, more metadata would be passed.
        ingestion_source = IngestionSource(
            source_id=doc_id,
            type=SourceType.FILE,
            uri=str(self.document_store.get_document_path(doc_type, case_id, doc_id, version)),
            metadata={
                "case_id": case_id,
                "doc_type": doc_type,
                "file_name": file_name,
                "version": version,
                "author": author,
                "keywords": keywords,
                "tags": tags,
                "custom_metadata": custom_metadata,
            }
        )

        # The run_ingestion_pipeline expects a Path for materialized_root
        # We need to ensure the document is accessible by the pipeline.
        # For now, we'll assume the pipeline can read from the encrypted path.
        # A more robust solution might involve decrypting to a temp location for ingestion.
        pipeline_result = run_ingestion_pipeline(
            job_id=doc_id, # Use doc_id as job_id for now
            materialized_root=self.materialized_root, # This needs to be the base path for ingestion
            source=ingestion_source,
            origin=origin,
            registry=self.loader_registry,
            runtime_config=self.runtime_config,
        )

        return {
            "doc_id": doc_id,
            "version": version,
            "case_id": case_id,
            "doc_type": doc_type,
            "file_name": file_name,
            "ingestion_status": "completed",
            "pipeline_result": pipeline_result.documents[0].categories if pipeline_result.documents else [],
        }

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
