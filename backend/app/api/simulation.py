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
