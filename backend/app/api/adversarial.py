from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any
from backend.app.agents.adversarial_agent import AdversarialAgent

router = APIRouter()

class ChallengeRequest(BaseModel):
    case_theory: str

@router.post("/{case_id}/challenge", summary="Generate adversarial challenge")
async def challenge_theory(case_id: str, request: ChallengeRequest) -> Dict[str, Any]:
    """
    Submits a case theory to the Adversarial Agent for critique.
    """
    try:
        agent = AdversarialAgent()
        return agent.generate_challenge(case_id, request.case_theory)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
