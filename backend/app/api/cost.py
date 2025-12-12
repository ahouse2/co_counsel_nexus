from fastapi import APIRouter, Depends

from ..models.api import (
    CostEventModel,
    CostSummaryMetricModel,
    CostSummaryResponse,
)
from ..services.costs import CostTrackingService, get_cost_tracking_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_billing_admin,
)

router = APIRouter()

@router.get("/cost/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    window_hours: float = 24.0,
    principal: Principal = Depends(authorize_billing_admin),
    service: CostTrackingService = Depends(get_cost_tracking_service),
) -> CostSummaryResponse:
    summary = service.summarise(window_hours=window_hours, tenant_id=principal.tenant_id)
    # Convert dataclass to Pydantic model if needed, or rely on FastAPI/Pydantic compatibility
    return summary


@router.get("/cost/events", response_model=list[CostEventModel])
async def get_cost_events(
    limit: int = 100,
    principal: Principal = Depends(authorize_billing_admin),
    service: CostTrackingService = Depends(get_cost_tracking_service),
) -> list[CostEventModel]:
    events = service.list_events(limit=limit, tenant_id=principal.tenant_id)
    # Convert dataclass to Pydantic model
    return [
        CostEventModel(
            id=e.event_id,
            timestamp=e.timestamp,
            category=e.category,
            name=e.name,
            amount=e.amount,
            unit=e.unit,
            metadata=e.metadata
        ) for e in events
    ]


# @router.get("/cost/metrics", response_model=list[CostSummaryMetricModel])
# async def get_cost_metrics(
#     principal: Principal = Depends(authorize_billing_admin),
#     service: CostTrackingService = Depends(get_cost_tracking_service),
# ) -> list[CostSummaryMetricModel]:
#     # Not implemented in CostTrackingService
#     return []
