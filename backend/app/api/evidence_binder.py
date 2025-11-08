from fastapi import APIRouter, Depends

from ..models.api import (
    ForensicsResponse,
)
from ..services.forensics import ForensicsService, get_forensics_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_forensics_document,
    authorize_forensics_financial,
    authorize_forensics_image,
)

router = APIRouter()

@router.get("/forensics/document/{document_id}", response_model=ForensicsResponse)
def get_document_forensics(
    document_id: str,
    _principal: Principal = Depends(authorize_forensics_document),
    service: ForensicsService = Depends(get_forensics_service),
) -> ForensicsResponse:
    return service.get_document_forensics(document_id)


@router.get("/forensics/image/{image_id}", response_model=ForensicsResponse)
def get_image_forensics(
    image_id: str,
    _principal: Principal = Depends(authorize_forensics_image),
    service: ForensicsService = Depends(get_forensics_service),
) -> ForensicsResponse:
    return service.get_image_forensics(image_id)


@router.get("/forensics/financial/{transaction_id}", response_model=ForensicsResponse)
def get_financial_forensics(
    transaction_id: str,
    _principal: Principal = Depends(authorize_forensics_financial),
    service: ForensicsService = Depends(get_forensics_service),
) -> ForensicsResponse:
    return service.get_financial_forensics(transaction_id)
