from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from backend.app.services.timeline import TimelineService, get_timeline_service, TimelineEvent

router = APIRouter()

@router.post("/weave/{case_id}", summary="Auto-generate narrative timeline")
async def weave_narrative(
    case_id: str,
    service: TimelineService = Depends(get_timeline_service)
) -> List[TimelineEvent]:
    """
    Triggers the AI to read case documents and construct a master timeline.
    """
    try:
        return service.weave_narrative(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contradictions/{case_id}", summary="Detect contradictions in timeline")
async def detect_contradictions(
    case_id: str,
    service: TimelineService = Depends(get_timeline_service)
) -> List[Dict[str, Any]]:
    """
    Analyzes the timeline for logical inconsistencies and witness contradictions.
    """
    try:
        return service.detect_contradictions(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
