from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Header, BackgroundTasks, Form
from typing import List, Optional

from backend.app.services.document_service import DocumentService
from backend.app.storage.document_store import DocumentStore
from backend.ingestion.loader_registry import LoaderRegistry
from backend.ingestion.settings import build_runtime_config
from backend.app.config import Settings, get_settings
from pathlib import Path

router = APIRouter()

def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    """
    Dependency to get DocumentService instance.
    """
    document_store = DocumentStore(base_dir=Path(settings.storage_dir))
    loader_registry = LoaderRegistry()
    runtime_config = build_runtime_config(settings)
    materialized_root = Path(settings.storage_dir) / "materialized"
    materialized_root.mkdir(parents=True, exist_ok=True)
    return DocumentService(
        document_store=document_store,
        loader_registry=loader_registry,
        runtime_config=runtime_config,
        materialized_root=materialized_root
    )

@router.post("/upload", summary="Upload a new document for a case")
async def upload_document(
    case_id: str,
    doc_type: str, # "my_documents" or "opposition_documents"
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None, # Add BackgroundTasks
    relative_path: Optional[str] = None, # New parameter for relative path
    author: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    custom_metadata: Optional[dict] = None,
    x_gemini_api_key: Optional[str] = Header(None),
    x_courtlistener_api_key: Optional[str] = Header(None),
    document_service: DocumentService = Depends(get_document_service)
):
    if doc_type not in ["my_documents", "opposition_documents"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document type.")

    file_content = await file.read()
    
    api_keys = {}
    if x_gemini_api_key:
        api_keys["gemini_api_key"] = x_gemini_api_key
    if x_courtlistener_api_key:
        api_keys["courtlistener_api_key"] = x_courtlistener_api_key

    # Upload document but skip immediate pipeline execution
    result = await document_service.upload_document(
        case_id,
        doc_type,
        file_content,
        file.filename,
        author,
        keywords,
        tags,
        custom_metadata,
        relative_path, # Pass relative_path to the service
        api_keys=api_keys, # Pass API keys
        run_pipeline=False # Run pipeline in background
    )

    # Schedule ingestion in background
    if background_tasks:
        background_tasks.add_task(
            document_service.process_ingestion,
            result["doc_id"],
            result["ingestion_source"],
            result["origin"],
            result["api_keys"]
        )

    return {"message": "Document uploaded and ingestion queued successfully", "data": result}

@router.post("/upload_directory", summary="Upload a directory of documents")
async def upload_directory(
    case_id: str,
    file: UploadFile = File(...),
    document_id: str = Form(...),
    background_tasks: BackgroundTasks = None,
    x_gemini_api_key: Optional[str] = Header(None),
    x_courtlistener_api_key: Optional[str] = Header(None),
    document_service: DocumentService = Depends(get_document_service)
):
    file_content = await file.read()
    
    api_keys = {}
    if x_gemini_api_key:
        api_keys["gemini_api_key"] = x_gemini_api_key
    if x_courtlistener_api_key:
        api_keys["courtlistener_api_key"] = x_courtlistener_api_key

    try:
        results = await document_service.upload_directory(
            case_id=case_id,
            zip_content=file_content,
            api_keys=api_keys
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Schedule ingestion for all uploaded documents
    if background_tasks:
        for result in results:
            background_tasks.add_task(
                document_service.process_ingestion,
                result["doc_id"],
                result["ingestion_source"],
                result["origin"],
                result["api_keys"]
            )

    return {"message": f"Successfully uploaded {len(results)} documents from directory", "data": results}

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
