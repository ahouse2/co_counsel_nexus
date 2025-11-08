from fastapi import APIRouter, Depends, Query

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
