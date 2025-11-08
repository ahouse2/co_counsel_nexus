from fastapi import APIRouter, Depends

from ..models.api import (
    DevAgentApplyRequest,
    DevAgentApplyResponse,
    DevAgentMetricsModel,
    DevAgentProposalListResponse,
    DevAgentProposalModel,
    DevAgentTaskModel,
)
from ..services.dev_agent import DevAgentService, get_dev_agent_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_dev_agent_admin,
)

router = APIRouter()

@router.get("/dev_agent/metrics", response_model=DevAgentMetricsModel)
async def get_dev_agent_metrics(
    principal: Principal = Depends(authorize_dev_agent_admin),
    service: DevAgentService = Depends(get_dev_agent_service),
) -> DevAgentMetricsModel:
    return await service.get_metrics(principal)


@router.get("/dev_agent/proposals", response_model=DevAgentProposalListResponse)
async def list_dev_agent_proposals(
    principal: Principal = Depends(authorize_dev_agent_admin),
    service: DevAgentService = Depends(get_dev_agent_service),
) -> DevAgentProposalListResponse:
    return await service.list_proposals(principal)


@router.get("/dev_agent/proposals/{proposal_id}", response_model=DevAgentProposalModel)
async def get_dev_agent_proposal(
    proposal_id: str,
    principal: Principal = Depends(authorize_dev_agent_admin),
    service: DevAgentService = Depends(get_dev_agent_service),
) -> DevAgentProposalModel:
    return await service.get_proposal(principal, proposal_id)


@router.post("/dev_agent/proposals/{proposal_id}/apply", response_model=DevAgentApplyResponse)
async def apply_dev_agent_proposal(
    proposal_id: str,
    request: DevAgentApplyRequest,
    principal: Principal = Depends(authorize_dev_agent_admin),
    service: DevAgentService = Depends(get_dev_agent_service),
) -> DevAgentApplyResponse:
    return await service.apply_proposal(principal, proposal_id, request)


@router.get("/dev_agent/tasks/{task_id}", response_model=DevAgentTaskModel)
async def get_dev_agent_task(
    task_id: str,
    principal: Principal = Depends(authorize_dev_agent_admin),
    service: DevAgentService = Depends(get_dev_agent_service),
) -> DevAgentTaskModel:
    return await service.get_task(principal, task_id)
