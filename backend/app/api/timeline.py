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
from toolsnteams_previous.timeline_manager import TimelineManager

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
    timeline_manager = TimelineManager()
    try:
        # The upsert_event_from_text method expects an int for case_id,
        # but our frontend sends a string. We need to convert it.
        # Also, the method expects the case_id to be part of the text,
        # or passed as a separate int. Let's adjust the call.
        
        # For now, we'll pass the case_id as an int, assuming it can be converted.
        # A more robust solution would involve modifying upsert_event_from_text
        # to accept case_id as a separate parameter.
        
        # If the event_text already contains "case:ID", it will override this.
        event_data = timeline_manager.upsert_event_from_text(
            text=f"case:{case_id} {request.event_text}",
            case_id=int(case_id) # Pass case_id as int
        )
        if not event_data:
            raise HTTPException(status_code=400, detail="Failed to parse event text or create event.")
        
        # Convert event_data to TimelineEventModel
        return TimelineEventModel(
            id=str(event_data["id"]), # Ensure ID is string
            event_date=event_data["date"],
            description=event_data["description"],
            links=event_data["links"]
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
    timeline_manager = TimelineManager()
    try:
        events = timeline_manager.get_timeline(case_id=int(case_id))
        return [
            TimelineEventModel(
                id=str(event["id"]),
                event_date=event["date"],
                description=event["description"],
                links=event["links"]
            ) for event in events
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid case ID: {e}")
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
                event_date=event.ts.isoformat(),
                description=event.summary, # Map summary to description
                links=event.citations
            ) for event in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate timeline: {e}")
