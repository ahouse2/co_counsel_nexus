from fastapi import APIRouter, Depends

from ..models.api import (
    CostEventModel,
    CostSummaryMetricModel,
    CostSummaryResponse,
)
from ..services.cost import CostService, get_cost_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_billing_admin,
)

router = APIRouter()

@router.get("/cost/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    principal: Principal = Depends(authorize_billing_admin),
    service: CostService = Depends(get_cost_service),
) -> CostSummaryResponse:
    return await service.get_cost_summary(principal)


@router.get("/cost/events", response_model=list[CostEventModel])
async def get_cost_events(
    principal: Principal = Depends(authorize_billing_admin),
    service: CostService = Depends(get_cost_service),
) -> list[CostEventModel]:
    return await service.get_cost_events(principal)


@router.get("/cost/metrics", response_model=list[CostSummaryMetricModel])
async def get_cost_metrics(
    principal: Principal = Depends(authorize_billing_admin),
    service: CostService = Depends(get_cost_service),
) -> list[CostSummaryMetricModel]:
    return await service.get_cost_metrics(principal)
