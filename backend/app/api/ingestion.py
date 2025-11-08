from fastapi import APIRouter, Depends, File, Form, UploadFile

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
    return await service.ingest_text(principal, request.document_id, request.text)


@router.get("/ingestion/{document_id}/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    document_id: str,
    principal: Principal = Depends(authorize_ingest_status),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestionStatusResponse:
    return await service.get_ingestion_status(principal, document_id)
