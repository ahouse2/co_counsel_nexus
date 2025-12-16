from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.simulation_service import SimulationService
from ..security.authz import Principal
from ..security.dependencies import authorize_timeline # Reusing timeline auth for now

router = APIRouter()

class MootCourtRequest(BaseModel):
    case_brief: str
    agent_role: str = "prosecutor"
    objectives: List[str]
    initial_statement: str
    max_turns: int = 3

def get_simulation_service() -> SimulationService:
    return SimulationService()

@router.post("/simulation/moot_court")
async def run_moot_court(
    request: MootCourtRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: SimulationService = Depends(get_simulation_service),
):
    """
    Runs a moot court simulation.
    """
    scenario = {
        "case_brief": request.case_brief,
        "agent_role": request.agent_role,
        "objectives": request.objectives,
        "initial_statement": request.initial_statement,
        "max_turns": request.max_turns
    }
    
    try:
        return await service.run_mock_court_simulation(scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")

class JurorChatRequest(BaseModel):
    juror_profile: Dict[str, Any]
    chat_history: List[Dict[str, str]] # [{"role": "user"|"juror", "content": "..."}]
    user_message: str
    case_context: str

@router.post("/simulation/juror_chat")
async def chat_with_juror(
    request: JurorChatRequest,
    service: SimulationService = Depends(get_simulation_service),
    _principal: Principal = Depends(authorize_timeline)
):
    """
    Chat with a specific virtual juror.
    """
    try:
        response = await service.chat_with_juror(
            request.juror_profile,
            request.chat_history,
            request.user_message,
            request.case_context
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Juror chat failed: {e}")
