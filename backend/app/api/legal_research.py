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

@router.get("/query", response_model=QueryResponse)
def query_legal_data(
    query: str,
    _principal: Principal = Depends(authorize_query),
    service: RetrievalService = Depends(get_retrieval_service),
    mode: RetrievalMode = Query(RetrievalMode.SEMANTIC, description="Retrieval mode"),
) -> QueryResponse:
    return service.query(query, mode)

from backend.app.services.legal_research_service import (
    LegalResearchService, get_legal_research_service,
    ShepardizeRequest, ShepardizeResult,
    JudgeProfileRequest, JudgeProfileResult
)

@router.post("/shepardize", response_model=ShepardizeResult)
async def shepardize(
    request: ShepardizeRequest,
    service: LegalResearchService = Depends(get_legal_research_service)
):
    """
    Checks if a case citation is still good law.
    """
    return await service.shepardize(request)

@router.post("/judge-profile", response_model=JudgeProfileResult)
async def profile_judge(
    request: JudgeProfileRequest,
    service: LegalResearchService = Depends(get_legal_research_service)
):
    """
    Generates a profile for a specific judge.
    """
    return await service.profile_judge(request)
