from fastapi import APIRouter, Depends, Query

from ..models.api import (
    QueryResponse,
)
from ..services.retrieval import RetrievalMode, RetrievalService, get_retrieval_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_query,
)

router = APIRouter()

@router.get("/retrieval", response_model=QueryResponse)
def query_retrieval_data(
    query: str,
    _principal: Principal = Depends(authorize_query),
    service: RetrievalService = Depends(get_retrieval_service),
    mode: RetrievalMode = Query(RetrievalMode.PRECISION, description="Retrieval mode"),
) -> QueryResponse:
    return service.query(query, mode)
