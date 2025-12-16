from fastapi import APIRouter, Depends, HTTPException
from backend.app.services.document_drafting_service import (
    DocumentDraftingService, get_document_drafting_service,
    DraftingRequest, ToneCheckRequest, ToneCheckResult
)

router = APIRouter(prefix="/api/drafting", tags=["drafting"])

@router.post("/autocomplete")
async def autocomplete(
    request: DraftingRequest,
    service: DocumentDraftingService = Depends(get_document_drafting_service)
):
    """
    Generates a text completion based on the current cursor position and context.
    """
    try:
        completion = await service.autocomplete(request)
        return {"completion": completion}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tone-check", response_model=ToneCheckResult)
async def tone_check(
    request: ToneCheckRequest,
    service: DocumentDraftingService = Depends(get_document_drafting_service)
):
    """
    Analyzes and rewrites text to match a specific tone.
    """
    try:
        return await service.check_tone(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
