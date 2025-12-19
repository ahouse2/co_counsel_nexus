"""
Swarm API - REST endpoints for interacting with agent swarms.

Provides endpoints to:
- List available swarms
- Trigger swarm execution
- Get swarm status
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio
import logging

from backend.app.agents.swarms.registry import get_swarm_registry

logger = logging.getLogger(__name__)
router = APIRouter()


class SwarmTriggerRequest(BaseModel):
    """Request to trigger a swarm."""
    swarm_name: str
    case_id: str
    params: Dict[str, Any] = {}


class SwarmResponse(BaseModel):
    """Response from swarm execution."""
    success: bool
    swarm_name: str
    case_id: str
    result: Dict[str, Any] = {}
    error: Optional[str] = None


@router.get("/swarms")
async def list_swarms():
    """List all available swarms with agent counts."""
    registry = get_swarm_registry()
    return {
        "swarms": registry.list_swarms(),
        "total_agents": registry.total_agents()
    }


@router.post("/swarms/trigger", response_model=SwarmResponse)
async def trigger_swarm(request: SwarmTriggerRequest):
    """Trigger a swarm to run on a case."""
    try:
        registry = get_swarm_registry()
        swarm = registry.get_swarm(request.swarm_name)
        
        result = {}
        
        # Call the appropriate swarm method based on type
        if request.swarm_name == "ingestion":
            # Requires document data
            doc_data = request.params.get("document", {})
            result = await swarm.process_document(doc_data, request.case_id)
            
        elif request.swarm_name == "narrative":
            result = await swarm.analyze_case(request.case_id)
            
        elif request.swarm_name == "trial_prep":
            case_theory = request.params.get("case_theory", "")
            result = await swarm.prepare_for_trial(request.case_id, case_theory)
            
        elif request.swarm_name == "forensics":
            doc_id = request.params.get("doc_id", "")
            doc_data = request.params.get("document", {})
            result = await swarm.analyze_document(doc_id, doc_data, request.case_id)
            
        elif request.swarm_name == "context_engine":
            query = request.params.get("query", "")
            result = await swarm.retrieve_context(query, request.case_id)
            
        elif request.swarm_name == "legal_research":
            query = request.params.get("query", "")
            jurisdiction = request.params.get("jurisdiction", "california")
            result = await swarm.research(query, request.case_id, jurisdiction)
            
        elif request.swarm_name == "drafting":
            doc_type = request.params.get("doc_type", "letter")
            instructions = request.params.get("instructions", "")
            result = await swarm.draft_document(doc_type, request.case_id, instructions)
            
        elif request.swarm_name == "asset_hunter":
            target = request.params.get("target", "")
            result = await swarm.investigate(target, request.case_id)
            
        elif request.swarm_name == "simulation":
            result = await swarm.run_simulation(request.case_id)
            
        elif request.swarm_name == "research":
            doc_id = request.params.get("doc_id", "")
            doc_text = request.params.get("doc_text", "")
            metadata = request.params.get("metadata", {})
            result = await swarm.research_for_document(doc_id, doc_text, metadata, request.case_id)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown swarm: {request.swarm_name}")
        
        return SwarmResponse(
            success=True,
            swarm_name=request.swarm_name,
            case_id=request.case_id,
            result=result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Swarm execution failed: {e}", exc_info=True)
        return SwarmResponse(
            success=False,
            swarm_name=request.swarm_name,
            case_id=request.case_id,
            error=str(e)
        )


@router.get("/swarms/{swarm_name}/agents")
async def get_swarm_agents(swarm_name: str):
    """Get details about agents in a specific swarm."""
    registry = get_swarm_registry()
    
    agent_details = {
        "ingestion": ["RouterAgent", "PrivilegeDetectorAgent", "HotDocumentAgent", "MetadataEnricherAgent", "GraphLinkerAgent", "QAValidatorAgent"],
        "research": ["CourtListenerResearchAgent", "CaliforniaCodesResearchAgent", "FederalCodesResearchAgent", "ResearchSynthesizer"],
        "narrative": ["TimelineBuilderAgent", "ContradictionDetectorAgent", "StoryArcAgent", "CausationAnalystAgent"],
        "trial_prep": ["MockTrialAgent", "JurySentimentAgent", "CrossExamAgent", "WitnessCredibilityAgent"],
        "forensics": ["TamperDetectionAgent", "MetadataForensicsAgent", "ChainOfCustodyAgent", "RedactionDetectorAgent", "TimelineForensicsAgent"],
        "context_engine": ["QueryUnderstandingAgent", "HybridRetrievalAgent", "RerankingAgent", "ContextSynthesisAgent"],
        "legal_research": ["CaseLawAgent", "StatuteAgent", "SecondarySourceAgent", "CitationAnalysisAgent", "SynthesisAgent"],
        "drafting": ["TemplateSelectionAgent", "FactGatheringAgent", "ArgumentStructureAgent", "ContentDraftingAgent", "CitationInsertionAgent", "ProofreadingAgent"],
        "asset_hunter": ["EntitySearchAgent", "PropertySearchAgent", "CryptoTracingAgent", "FinancialDiscrepancyAgent", "SchemeDetectorAgent"],
        "simulation": ["ScenarioBuilderAgent", "OutcomePredictorAgent", "SettlementAnalyzerAgent", "RiskAssessorAgent", "StrategyRecommenderAgent"]
    }
    
    if swarm_name not in agent_details:
        raise HTTPException(status_code=404, detail=f"Swarm not found: {swarm_name}")
    
    return {
        "swarm_name": swarm_name,
        "agents": agent_details[swarm_name],
        "agent_count": len(agent_details[swarm_name])
    }
