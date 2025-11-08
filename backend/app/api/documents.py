from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from typing import List, Optional

from backend.app.services.document_service import DocumentService
from backend.app.storage.document_store import DocumentStore
from backend.ingestion.loader_registry import LoaderRegistry
from backend.ingestion.settings import build_runtime_config
from backend.app.config import Settings, get_settings
from pathlib import Path

router = APIRouter()

# Dependency to get DocumentService
async def get_document_service(
    settings: Settings = Depends(get_settings)
) -> DocumentService:
    # This is a simplified dependency. In a real application, these would be
    # managed by a proper dependency injection framework or application lifecycle.
    encryption_key = settings.encryption_key # Assuming encryption_key is in settings
    if not encryption_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption key not configured.")

    document_store = DocumentStore(base_dir=settings.document_storage_path, encryption_key=encryption_key)
    loader_registry = LoaderRegistry() # Initialize with default loaders
    runtime_config = build_runtime_config(settings)
    materialized_root = Path(settings.ingestion_workspace_dir) # Assuming this is where pipeline expects temp files

    return DocumentService(
        document_store=document_store,
        loader_registry=loader_registry,
        runtime_config=runtime_config,
        materialized_root=materialized_root,
    )

@router.post("/upload", summary="Upload a new document for a case")
async def upload_document(
    case_id: str,
    doc_type: str, # "my_documents" or "opposition_documents"
    file: UploadFile = File(...),
    author: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    custom_metadata: Optional[dict] = None,
    document_service: DocumentService = Depends(get_document_service)
):
    if doc_type not in ["my_documents", "opposition_documents"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type.")

    file_content = await file.read()
    result = await document_service.upload_document(
        case_id,
        doc_type,
        file_content,
        file.filename,
        author,
        keywords,
        tags,
        custom_metadata
    )
    return {"message": "Document uploaded and ingestion initiated successfully", "data": result}

@router.get("/{case_id}/{doc_type}/{doc_id}", summary="Retrieve a document")
async def get_document(
    case_id: str,
    doc_type: str,
    doc_id: str,
    version: Optional[str] = None,
    document_service: DocumentService = Depends(get_document_service)
):
    if doc_type not in ["my_documents", "opposition_documents"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type.")

    content = document_service.get_document(case_id, doc_type, doc_id, version)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return {"content": content}

@router.get("/{case_id}/{doc_type}/{doc_id}/versions", summary="List all versions of a document")
async def list_document_versions(
    case_id: str,
    doc_type: str,
    doc_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> List[str]:
    if doc_type not in ["my_documents", "opposition_documents"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type.")
    
    versions = document_service.list_document_versions(case_id, doc_type, doc_id)
    if not versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No versions found for this document.")
    return versions

@router.delete("/{case_id}/{doc_type}/{doc_id}", summary="Delete a document or a specific version")
async def delete_document(
    case_id: str,
    doc_type: str,
    doc_id: str,
    version: Optional[str] = None,
    document_service: DocumentService = Depends(get_document_service)
):
    if doc_type not in ["my_documents", "opposition_documents"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type.")

    document_service.delete_document(case_id, doc_type, doc_id, version)
    return {"message": "Document(s) deleted successfully."}

@router.get("/{case_id}/documents", summary="List all documents for a case")
async def list_case_documents(
    case_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> List[dict]:
    """
    List all documents for a given case.
    """
    documents = document_service.list_all_documents(case_id)
    return documents
