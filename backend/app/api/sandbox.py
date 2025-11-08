from fastapi import APIRouter, Depends

from ..models.api import (
    SandboxCommandResultModel,
    SandboxExecutionModel,
)
from ..services.sandbox import SandboxService, get_sandbox_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_dev_agent_admin,
)

router = APIRouter()

@router.post("/sandbox/execute", response_model=SandboxCommandResultModel)
async def execute_sandbox_command(
    request: SandboxExecutionModel,
    principal: Principal = Depends(authorize_dev_agent_admin),
    service: SandboxService = Depends(get_sandbox_service),
) -> SandboxCommandResultModel:
    return await service.execute_command(principal, request.command)
