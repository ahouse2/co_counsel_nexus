from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from ..models.api import (
    QueryResponse,
)
from ..services.retrieval import RetrievalMode, RetrievalService, get_retrieval_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_query,
)

from ..services.legal_theory_engine import LegalTheoryEngine

router = APIRouter()

class LegalTheorySuggestion(BaseModel):
    cause: str
    score: float
    elements: List[Dict[str, Any]]
    defenses: List[str]
    indicators: List[str]
    missing_elements: List[str]

class LegalTheorySubgraph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

@router.get("/legal_theory", response_model=QueryResponse)
def get_legal_theory(
    query: str,
    _principal: Principal = Depends(authorize_query),
    service: RetrievalService = Depends(get_retrieval_service),
    mode: RetrievalMode = Query(RetrievalMode.SEMANTIC, description="Retrieval mode"),
) -> QueryResponse:
    return service.query(query, mode)

@router.get("/legal_theory/suggestions", response_model=List[LegalTheorySuggestion])
async def get_legal_theory_suggestions(
    case_id: str = Query(None, description="Case ID to fetch context from"),
    _principal: Principal = Depends(authorize_query),
):
    """
    Returns ranked candidate legal theories based on factual support.
    Uses the LegalResearchCrew via SwarmsRunner.
    """
    from backend.app.agents.swarms_runner import get_swarms_runner
    import asyncio
    import json
    
    runner = get_swarms_runner()
    
    prompt = f"""
    Context: Legal Research for Case {case_id or 'Hypothetical'}.
    Role: You are the Research Coordinator.
    
    Task:
    1. Use the LegalTheoryEngine (via tools) or your own knowledge to suggest 3 legal theories.
    2. If a case_id is provided, query the Knowledge Graph for facts first.
    3. Return the result as a JSON list of objects with the following keys:
        - cause: str (Name of the legal theory)
        - score: float (Confidence score 0.0-1.0)
        - elements: list of objects {{name: str, description: str}}
        - defenses: list of strings
        - indicators: list of strings (Facts that support this theory)
        - missing_elements: list of strings
    
    Ensure the output is valid JSON.
    """
    
    loop = asyncio.get_event_loop()
    try:
        # Route to 'legal_research'
        response_text = await loop.run_in_executor(None, runner.route_and_run, prompt)
        
        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        return json.loads(response_text.strip())
        
    except Exception as e:
        print(f"Swarms Execution Failed: {e}")
        # Fallback to direct engine call if Swarms fails
        engine = LegalTheoryEngine()
        try:
            return await engine.suggest_theories(case_id)
        finally:
            engine.close()

@router.get("/legal_theory/{cause}/subgraph", response_model=LegalTheorySubgraph)
async def get_legal_theory_subgraph(
    cause: str,
    _principal: Principal = Depends(authorize_query),
):
    """
    Exposes subgraph retrieval for a specific cause of action.
    """
    engine = LegalTheoryEngine()
    try:
        nodes, edges = await engine.get_theory_subgraph(cause)
        return LegalTheorySubgraph(nodes=nodes, edges=edges)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving subgraph: {e}")
    finally:
        engine.close()
