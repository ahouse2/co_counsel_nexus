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

class PrecedentMatchRequest(BaseModel):
    case_facts: str
    jurisdiction: str = "federal"

class PrecedentMatchResult(BaseModel):
    case_name: str
    citation: str
    similarity_score: float
    reasoning: str

@router.post("/legal_theory/match_precedents", response_model=List[PrecedentMatchResult])
async def match_precedents(
    request: PrecedentMatchRequest,
    _principal: Principal = Depends(authorize_query),
):
    """
    Finds relevant precedents based on case facts using LLM.
    """
    from backend.app.services.llm_service import get_llm_service
    import json
    
    llm_service = get_llm_service()
    
    prompt = f"""
    You are an expert legal researcher. Based on the following case facts and jurisdiction, identify 3-5 relevant legal precedents.
    
    CASE FACTS:
    {request.case_facts}
    
    JURISDICTION: {request.jurisdiction}
    
    For each precedent, provide:
    - case_name: Full case name
    - citation: Legal citation (e.g., "123 F.3d 456 (2010)")
    - similarity_score: Float between 0.0 and 1.0 indicating relevance
    - reasoning: Brief explanation of why this precedent is relevant
    
    Return the result as a JSON list.
    
    JSON OUTPUT:
    """
    
    try:
        response_text = await llm_service.generate_text(prompt)
        response_text = response_text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            data = json.loads(response_text)
            return [
                PrecedentMatchResult(
                    case_name=item.get("case_name", "Unknown Case"),
                    citation=item.get("citation", "Unknown Citation"),
                    similarity_score=float(item.get("similarity_score", 0.5)),
                    reasoning=item.get("reasoning", "")
                )
                for item in data
            ]
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return [
                PrecedentMatchResult(
                    case_name="LLM Response Error",
                    citation="N/A",
                    similarity_score=0.0,
                    reasoning=f"Failed to parse LLM response: {response_text[:200]}"
                )
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Precedent matching failed: {e}")

class JuryResonanceRequest(BaseModel):
    argument: str
    jury_demographics: Dict[str, str]

class JuryResonanceResult(BaseModel):
    score: float
    feedback: str
    demographic_breakdown: Dict[str, float]

@router.post("/legal_theory/jury_resonance", response_model=JuryResonanceResult)
async def calculate_jury_resonance(
    request: JuryResonanceRequest,
    _principal: Principal = Depends(authorize_query),
):
    """
    Calculates how well an argument resonates with a specific jury demographic using LLM.
    """
    from backend.app.services.llm_service import get_llm_service
    import json
    
    llm_service = get_llm_service()
    
    # Format demographics for prompt
    demographics_str = ", ".join([f"{k}: {v}" for k, v in request.jury_demographics.items()])
    
    prompt = f"""
    You are an expert jury consultant. Analyze how well the following legal argument would resonate with a jury of the specified demographics.
    
    ARGUMENT:
    {request.argument}
    
    JURY DEMOGRAPHICS:
    {demographics_str}
    
    Provide your analysis in the following JSON format:
    {{
        "score": <float 0.0 to 1.0 overall resonance score>,
        "feedback": "<brief analysis of argument strengths and weaknesses for this jury>",
        "demographic_breakdown": {{
            "<demographic_key_1>": <float 0.0 to 1.0>,
            "<demographic_key_2>": <float 0.0 to 1.0>,
            ...
        }}
    }}
    
    The demographic_breakdown should include an estimated resonance score for each demographic category provided.
    
    JSON OUTPUT:
    """
    
    try:
        response_text = await llm_service.generate_text(prompt)
        response_text = response_text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        try:
            data = json.loads(response_text)
            return JuryResonanceResult(
                score=float(data.get("score", 0.5)),
                feedback=data.get("feedback", "Analysis unavailable."),
                demographic_breakdown={
                    k: float(v) for k, v in data.get("demographic_breakdown", {}).items()
                }
            )
        except json.JSONDecodeError:
            return JuryResonanceResult(
                score=0.5,
                feedback=f"Failed to parse LLM response: {response_text[:200]}",
                demographic_breakdown={}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jury resonance analysis failed: {e}")

