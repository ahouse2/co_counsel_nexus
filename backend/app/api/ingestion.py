from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..models.api import (
    IngestionRequest,
    IngestionResponse,
    IngestionStatusResponse,
)
from ..services.ingestion import (
    IngestionService,
    get_ingestion_service,
)
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_ingest_enqueue,
    authorize_ingest_status,
)

router = APIRouter()

@router.post("/ingestion", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    principal: Principal = Depends(authorize_ingest_enqueue),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    return await service.ingest_document(principal, document_id, file)


@router.post("/ingestion/text", response_model=IngestionResponse)
async def ingest_text(
    request: IngestionRequest,
    principal: Principal = Depends(authorize_ingest_enqueue),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    if not request.document_id or not request.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id and text are required for text ingestion",
        )
    return await service.ingest_text(principal, request.document_id, request.text)


@router.post("/ingestion/upload_directory", response_model=IngestionResponse)
async def upload_directory(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    principal: Principal = Depends(authorize_ingest_enqueue),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    return await service.ingest_directory(principal, document_id, file)


@router.get("/ingestion/{document_id}/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    document_id: str,
    principal: Principal = Depends(authorize_ingest_status),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionStatusResponse:
    return await service.get_ingestion_status(principal, document_id)


async def get_dev_principal() -> Principal:
    return Principal(
        client_id="dev-user",
        subject="dev-user",
        tenant_id="dev-tenant",
        roles={"CaseCoordinator"},
        token_roles=set(),
        certificate_roles=set(),
        scopes={"ingest:enqueue"},
        case_admin=True,
        attributes={}
    )

@router.post("/ingestion/ingest_local_path", response_model=IngestionResponse)
async def ingest_local_path(
    source_path: str = Form(...),
    document_id: str = Form(...),
    recursive: bool = Form(default=True),
    sync: bool = Form(default=False),
    principal: Principal = Depends(get_dev_principal),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionResponse:
    """
    Ingest files from local file system or network share.
    No upload required - instant ingestion!
    
    Args:
        source_path: Local file path or directory (e.g., "I:\\legal_documents")
        document_id: Document identifier
        recursive: Scan subdirectories (default: True)
        sync: If True, skips files that have already been ingested (matching path and hash).
    """
    return await service.ingest_local_path(principal, document_id, source_path, recursive, sync)
