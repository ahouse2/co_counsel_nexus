from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

from ..models.api import (
    TimelineEventModel,
    TimelinePaginationModel,
    TimelineResponse,
)
from ..services.timeline import TimelineService, get_timeline_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_timeline,
)



router = APIRouter()

class TimelineEventRequest(BaseModel):
    event_text: str
    case_id: Optional[str] = None # Make case_id optional in the request body

@router.get("/timeline", response_model=TimelineResponse)
def get_timeline(
    _principal: Principal = Depends(authorize_timeline),
    service: TimelineService = Depends(get_timeline_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> TimelineResponse:
    events = service.get_events(page=page, page_size=page_size)
    total_events = service.get_total_events()
    return TimelineResponse(
        events=events,
        pagination=TimelinePaginationModel(
            total=total_events, page=page, page_size=page_size
        ),
    )

@router.post("/timeline/{case_id}/event", response_model=TimelineEventModel)
async def upsert_timeline_event(
    case_id: str,
    request: TimelineEventRequest,
    _principal: Principal = Depends(authorize_timeline),
):
    """
    Creates or updates a timeline event for a given case.
    """
    service = get_timeline_service()
    try:
        # Create event using service
        event = service.create_event(
            text=request.event_text,
            case_id=case_id
        )
        
        # Convert to TimelineEventModel
        return TimelineEventModel(
            id=str(event.id),
            ts=event.ts,
            title=event.title,
            summary=event.summary,
            citations=event.citations,
            entity_highlights=event.entity_highlights,
            relation_tags=event.relation_tags,
            confidence=event.confidence,
            risk_score=event.risk_score,
            risk_band=event.risk_band,
            outcome_probabilities=event.outcome_probabilities,
            recommended_actions=event.recommended_actions,
            motion_deadline=event.motion_deadline,
            type=event.event_type,
            related_ids=event.related_event_ids
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.get("/timeline/{case_id}", response_model=list[TimelineEventModel])
async def get_timeline_for_case(
    case_id: str,
    _principal: Principal = Depends(authorize_timeline),
):
    """
    Retrieves all timeline events for a given case.
    """
    service = get_timeline_service()
    try:
        result = service.list_events(case_id=case_id, limit=100) # Default limit
        return [
            TimelineEventModel(
                id=str(event.id),
                ts=event.ts,
                title=event.title,
                summary=event.summary,
                citations=event.citations,
                entity_highlights=event.entity_highlights,
                relation_tags=event.relation_tags,
                confidence=event.confidence,
                risk_score=event.risk_score,
                risk_band=event.risk_band,
                outcome_probabilities=event.outcome_probabilities,
                recommended_actions=event.recommended_actions,
                motion_deadline=event.motion_deadline,
                type=event.event_type,
                related_ids=event.related_event_ids
            ) for event in result.events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

class TimelineGenerateRequest(BaseModel):
    prompt: str
    case_id: str

@router.post("/timeline/generate", response_model=list[TimelineEventModel])
async def generate_timeline(
    request: TimelineGenerateRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: TimelineService = Depends(get_timeline_service),
):
    """
    Generates a timeline based on a natural language prompt.
    """
    try:
        events = service.generate_timeline_from_prompt(request.prompt, request.case_id)
        return [
            TimelineEventModel(
                id=str(event.id),
                ts=event.ts,
                title=event.title,
                summary=event.summary,
                citations=event.citations,
                entity_highlights=event.entity_highlights,
                relation_tags=event.relation_tags,
                confidence=event.confidence,
                risk_score=event.risk_score,
                risk_band=event.risk_band,
                outcome_probabilities=event.outcome_probabilities,
                recommended_actions=event.recommended_actions,
                motion_deadline=event.motion_deadline,
                type=event.event_type,
                related_ids=event.related_event_ids
            ) for event in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate timeline: {e}")

@router.post("/timeline/{case_id}/weave", response_model=list[TimelineEventModel])
async def weave_narrative(
    case_id: str,
    _principal: Principal = Depends(authorize_timeline),
    service: TimelineService = Depends(get_timeline_service),
):
    """
    Weaves a narrative from the case events.
    """
    try:
        events = service.weave_narrative(case_id)
        return [
            TimelineEventModel(
                id=str(event.id),
                ts=event.ts,
                title=event.title,
                summary=event.summary,
                citations=event.citations,
                entity_highlights=event.entity_highlights,
                relation_tags=event.relation_tags,
                confidence=event.confidence,
                risk_score=event.risk_score,
                risk_band=event.risk_band,
                outcome_probabilities=event.outcome_probabilities,
                recommended_actions=event.recommended_actions,
                motion_deadline=event.motion_deadline,
                type=event.event_type,
                related_ids=event.related_event_ids
            ) for event in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to weave narrative: {e}")

@router.get("/timeline/{case_id}/contradictions")
async def detect_contradictions(
    case_id: str,
    _principal: Principal = Depends(authorize_timeline),
    service: TimelineService = Depends(get_timeline_service),
):
    """
    Detects contradictions in the case timeline.
    """
    try:
        return service.detect_contradictions(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect contradictions: {e}")
