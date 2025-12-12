from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any

from backend.app.services.intelligence_service import IntelligenceService

router = APIRouter()

def get_intelligence_service():
    return IntelligenceService()

@router.post("/{case_id}/analyze", summary="Trigger full case analysis")
async def trigger_case_analysis(
    case_id: str,
    background_tasks: BackgroundTasks,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """
    Manually triggers a full intelligence analysis for a case.
    This includes timeline extraction, legal theory generation, etc.
    """
    background_tasks.add_task(service.run_full_case_analysis, case_id)
    return {"message": "Full case analysis triggered in background"}

@router.post("/{case_id}/timeline/generate", summary="Force timeline generation")
async def generate_timeline(
    case_id: str,
    background_tasks: BackgroundTasks,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """
    Forces regeneration of the case timeline from all documents.
    """
    # For now, we reuse the full analysis or implement specific method
    # Let's assume full analysis covers it, or we add a specific method later.
    # For MVP, we'll just trigger full analysis which includes timeline.
    background_tasks.add_task(service.run_full_case_analysis, case_id)
    return {"message": "Timeline generation triggered in background"}
