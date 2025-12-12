from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.app.config import Settings, get_settings
from backend.app.services.context_service import ContextService

router = APIRouter()

class ContextQueryRequest(BaseModel):
    query: str
    case_id: str
    top_k: int = 5

class ContextQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    count: int

def get_context_service(settings: Settings = Depends(get_settings)) -> ContextService:
    return ContextService(settings)

@router.post("/query", response_model=ContextQueryResponse, summary="Query document context")
async def query_context(
    request: ContextQueryRequest,
    context_service: ContextService = Depends(get_context_service)
):
    """
    Queries the vector store for relevant context based on the provided query and case ID.
    """
    try:
        result = await context_service.query_context(
            query=request.query,
            case_id=request.case_id,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
