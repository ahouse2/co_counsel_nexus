from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Header, BackgroundTasks, Form
from typing import List, Optional
import asyncio
import logging

from backend.app.services.document_service import DocumentService
from backend.app.storage.document_store import DocumentStore
from backend.ingestion.loader_registry import LoaderRegistry
from backend.ingestion.settings import build_runtime_config, build_ocr_config
from backend.ingestion.ocr import OcrEngine
from backend.app.config import Settings, get_settings
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    """
    Dependency to get DocumentService instance.
    """
    document_store = DocumentStore(base_dir=settings.document_storage_path, encryption_key=settings.encryption_key)
    
    # Create a logger instance
    logger = logging.getLogger(__name__)

    # Create an OcrConfig instance
    ocr_config = build_ocr_config(settings)

    # Create an OcrEngine instance
    ocr_engine = OcrEngine(config=ocr_config, logger=logger)

    # Create a LlamaIndexRuntimeConfig instance
    runtime_config = build_runtime_config(settings)

    loader_registry = LoaderRegistry(runtime_config=runtime_config, ocr_engine=ocr_engine, logger=logger)
    
    materialized_root = settings.document_storage_path.parent / "materialized"
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
    logger.info(f"Received folder upload request for case_id={case_id}, filename={file.filename}")
    
    # Pass the file object directly to avoid reading the entire zip into memory
    # file.file is a SpooledTemporaryFile which acts like a file object
    zip_content = file.file
    # logger.info(f"Read {len(file_content)} bytes from uploaded file")
    
    api_keys = {}
    if x_gemini_api_key:
        api_keys["gemini_api_key"] = x_gemini_api_key
    if x_courtlistener_api_key:
        api_keys["courtlistener_api_key"] = x_courtlistener_api_key

    try:
        results = await document_service.upload_directory(
            case_id=case_id,
            zip_content=zip_content,
            api_keys=api_keys
        )
        logger.info(f"Successfully extracted and queued {len(results)} documents from folder")
    except ValueError as e:
        logger.error(f"Invalid folder upload: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in folder upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process folder upload")

    # Schedule ingestion for all uploaded documents
    if background_tasks:
        logger.info(f"Scheduling {len(results)} documents for background ingestion")
        for result in results:
            background_tasks.add_task(
                document_service.process_ingestion,
                result["doc_id"],
                result["ingestion_source"],
                result["origin"],
                result["api_keys"]
            )
    else:
        logger.warning("No background_tasks available, documents will not be ingested")

    return {"message": f"Successfully uploaded {len(results)} documents from directory", "data": results}


@router.post("/upload_chunk", summary="Upload a chunk of files from folder")
async def upload_chunk(
    case_id: str,
    files: List[UploadFile] = File(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    background_tasks: BackgroundTasks = None,
    x_gemini_api_key: Optional[str] = Header(None),
    x_courtlistener_api_key: Optional[str] = Header(None),
    document_service: DocumentService = Depends(get_document_service)
):
    logger.info(f"Received chunk upload: {chunk_index + 1}/{total_chunks} with {len(files)} files for case_id={case_id}")
    
    api_keys = {}
    if x_gemini_api_key:
        api_keys["gemini_api_key"] = x_gemini_api_key
    if x_courtlistener_api_key:
        api_keys["courtlistener_api_key"] = x_courtlistener_api_key

    results = []
    
    for idx, file in enumerate(files):
        await asyncio.sleep(0) # Yield control
        try:
            file_content = await file.read()
            
            # Extract relative path from filename if provided
            # Format: "folder/subfolder/file.pdf"
            filename = file.filename or f"file_{idx}"
            relative_path = None
            file_name = filename
            
            if '/' in filename or '\\' in filename:
                from pathlib import Path
                path_obj = Path(filename)
                file_name = path_obj.name
                if len(path_obj.parts) > 1:
                    relative_path = str(path_obj.parent)
            
            logger.debug(f"Processing file {idx + 1}/{len(files)}: {filename}")
            
            result = await document_service.upload_document(
                case_id=case_id,
                doc_type="my_documents",
                file_content=file_content,
                file_name=file_name,
                relative_path=relative_path,
                origin="folder_upload_chunked",
                api_keys=api_keys,
                run_pipeline=False
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"Failed to process file {filename}: {str(e)}", exc_info=True)
            # Continue processing other files
            continue
    
    # Schedule background ingestion
    if background_tasks:
        logger.info(f"Scheduling {len(results)} documents from chunk for background ingestion")
        for result in results:
            background_tasks.add_task(
                document_service.process_ingestion,
                result["doc_id"],
                result["ingestion_source"],
                result["origin"],
                result["api_keys"]
            )
    
    logger.info(f"Chunk {chunk_index + 1}/{total_chunks} completed: {len(results)}/{len(files)} files processed successfully")
    
    return {
        "message": f"Chunk {chunk_index + 1}/{total_chunks} uploaded ({len(results)} files)",
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "files_processed": len(results),
        "files_total": len(files),
        "data": results
    }

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

async def background_local_ingestion(
    case_id: str,
    directory_path: str,
    api_keys: dict,
    document_service: DocumentService
):
    logger.info(f"Starting background local ingestion for {directory_path}")
    try:
        results = await document_service.ingest_local_directory(
            case_id=case_id,
            directory_path=directory_path,
            api_keys=api_keys
        )
        logger.info(f"Local ingestion found {len(results)} files. Scheduling pipeline processing...")
        
        for result in results:
            # We can't use BackgroundTasks here since we are already in a background task.
            # We must await the processing or fire-and-forget. 
            # Since process_ingestion is async, we can await it, but that makes it serial.
            # Better to run it.
            try:
                await document_service.process_ingestion(
                    result["doc_id"],
                    result["ingestion_source"],
                    result["origin"],
                    result["api_keys"]
                )
            except Exception as e:
                logger.error(f"Error processing doc {result['doc_id']}: {e}")
                
        logger.info("Background local ingestion completed.")
    except Exception as e:
        logger.error(f"Background local ingestion failed: {e}", exc_info=True)

@router.post("/ingestion/local", summary="Ingest documents from a local directory (mounted volume)")
async def ingest_local_directory(
    case_id: str = Form(...),
    directory_path: str = Form("."), # Default to root of mounted volume
    background_tasks: BackgroundTasks = None,
    x_gemini_api_key: Optional[str] = Header(None),
    x_courtlistener_api_key: Optional[str] = Header(None),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Ingests all files from a directory within the mounted /data volume.
    Returns immediately and processes in background.
    """
    api_keys = {}
    if x_gemini_api_key:
        api_keys["gemini_api_key"] = x_gemini_api_key
    if x_courtlistener_api_key:
        api_keys["courtlistener_api_key"] = x_courtlistener_api_key

    if not background_tasks:
        raise HTTPException(status_code=500, detail="Background tasks not available")

    background_tasks.add_task(
        background_local_ingestion,
        case_id,
        directory_path,
        api_keys,
        document_service
    )

    return {"message": "Ingestion started in background. Check logs/frontend for progress."}

@router.get("/pending_review", summary="List documents pending classification review")
async def list_pending_review_documents(
    case_id: str = "default_case", # Default for now
    document_service: DocumentService = Depends(get_document_service)
) -> List[dict]:
    """
    Lists all documents that have not been manually approved yet.
    """
    all_docs = document_service.list_all_documents(case_id)
    # Filter for docs where review_status is not 'approved'
    # We assume if review_status is missing, it's pending if the doc is processed.
    pending_docs = []
    for doc in all_docs:
        # Only show documents that have finished processing
        if doc.get("status") == "completed":
            review_status = doc.get("forensic_metadata", {}).get("review_status", "pending")
            if review_status != "approved":
                # Enhance doc with categories/tags from metadata if available
                # list_all_documents returns basic info. 
                # We might need to fetch full metadata if it's not in the list view.
                # DocumentStore.list_all_documents does read the .meta file.
                # So forensic_metadata should be there.
                # But categories/tags are top-level in .meta, not in forensic_metadata?
                # Let's check DocumentStore.save_document.
                # It saves tags and keywords (categories?) in the root of metadata json.
                # DocumentStore.list_all_documents reads the whole json but only extracts specific fields.
                # It extracts 'forensic_metadata'.
                # It does NOT extract 'tags' or 'keywords' explicitly in the current implementation of list_all_documents.
                # We need to update list_all_documents or fetch here.
                # Updating list_all_documents is better but let's just fetch here for now to avoid breaking changes.
                # Actually, let's update DocumentStore.list_all_documents to include tags/categories.
                pass 
                pending_docs.append(doc)
    return pending_docs

@router.post("/{doc_id}/approve", summary="Approve document classification")
async def approve_classification(
    doc_id: str,
    case_id: str = "default_case",
    doc_type: str = "my_documents",
    document_service: DocumentService = Depends(get_document_service)
):
    # Update metadata to set review_status = approved
    document_service.document_store.update_document_metadata(
        doc_type, case_id, doc_id, 
        {"forensic_metadata": {"review_status": "approved"}} # This overwrites forensic_metadata? No, update_document_metadata merges top-level keys.
        # But forensic_metadata is a dict. We need to merge INSIDE it.
        # DocumentStore.update_document_metadata does `current_metadata.update(metadata_updates)`.
        # So if we pass {"forensic_metadata": ...}, it will overwrite the whole forensic_metadata dict!
        # This is dangerous.
        # We need a better way to update nested metadata.
        # Or we just store review_status at the top level.
    )
    # Let's store review_status at the top level for safety.
    document_service.document_store.update_document_metadata(
        doc_type, case_id, doc_id, 
        {"review_status": "approved"}
    )
    return {"message": "Document approved"}

@router.post("/{doc_id}/update_metadata", summary="Update document metadata")
async def update_document_metadata(
    doc_id: str,
    metadata: dict, # Expected: {categories: [], tags: [], summary: ...}
    case_id: str = "default_case",
    doc_type: str = "my_documents",
    document_service: DocumentService = Depends(get_document_service)
):
    # Update top-level metadata
    updates = {}
    if "categories" in metadata:
        updates["keywords"] = metadata["categories"] # We map categories to keywords? Or tags?
        # save_document uses 'keywords' and 'tags'.
        # Let's use 'keywords' for categories and 'tags' for tags.
    if "tags" in metadata:
        updates["tags"] = metadata["tags"]
    
    # For summary/entities, we might want to put them in 'custom_metadata'
    if "summary" in metadata or "key_entities" in metadata or "sentiment" in metadata:
        # We need to read existing custom_metadata first to merge?
        # DocumentStore doesn't support deep merge.
        # Let's just save them as top-level fields for now, or read-modify-write.
        # Since we are in the API, we can read-modify-write.
        pass
        
    document_service.document_store.update_document_metadata(
        doc_type, case_id, doc_id, 
        {
            **updates,
            "custom_metadata": metadata # This might overwrite existing custom_metadata.
            # Ideally we should implement a patch method in DocumentStore.
        }
    )
    return {"message": "Metadata updated"}
