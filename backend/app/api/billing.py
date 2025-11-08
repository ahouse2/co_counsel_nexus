from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from ..telemetry.billing import (
    BILLING_PLANS,
    export_customer_health,
    export_plan_catalogue,
)
from ..models.api import (
    BillingPlanListResponse,
    BillingUsageResponse,
)
from ..services.costs import CostTrackingService, get_cost_tracking_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_billing_admin,
)

router = APIRouter()

@router.get("/billing/plans", response_model=BillingPlanListResponse)
def list_billing_plans() -> BillingPlanListResponse:
    return export_plan_catalogue()


@router.get("/billing/usage", response_model=BillingUsageResponse)
def get_billing_usage(
    principal: Principal = Depends(authorize_billing_admin),
    service: CostTrackingService = Depends(get_cost_tracking_service),
    start_date: datetime = Query(
        ..., description="Start date for usage aggregation (UTC)"
    ),
    end_date: datetime = Query(
        ..., description="End date for usage aggregation (UTC)"
    ),
) -> BillingUsageResponse:
    return service.get_usage_summary(principal, start_date, end_date)


@router.get("/billing/health")
def get_billing_health(
    principal: Principal = Depends(authorize_billing_admin),
) -> JSONResponse:
    return export_customer_health(principal)
