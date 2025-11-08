
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.app.testing_harness.harness import TestingHarnessService

router = APIRouter()
testing_hservice = TestingHarnessService()

@router.post("/run_scenario/{scenario_name}", response_model=Dict[str, Any])
async def run_scenario(scenario_name: str) -> Dict[str, Any]:
    """
    Loads and runs a specific test scenario against the agent orchestrator.
    """
    try:
        scenario = testing_hservice.load_scenario(scenario_name)
        agent_result = await testing_hservice.run_test(scenario)
        evaluation_result = testing_hservice.evaluate_output(agent_result, scenario.get("expected_output", {}))
        
        return {
            "scenario_name": scenario_name,
            "agent_result": agent_result,
            "evaluation_result": evaluation_result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

