"""API endpoints for evidence mapping and analysis."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..security.dependencies import Principal, authorize_timeline
from ..services.evidence_map import EvidenceMapService, get_evidence_map_service


router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request for evidence analysis."""
    analysis_type: str = Field(..., description="Type of analysis: 'strength', 'gaps', 'path'")
    legal_theory: Optional[str] = Field(None, description="Legal theory for gap analysis")
    claim: Optional[str] = Field(None, description="Claim for argument path analysis")
    evidence_id: Optional[str] = Field(None, description="Evidence ID for strength analysis")


class EvidenceMapResponse(BaseModel):
    """Response containing evidence map."""
    case_id: str
    evidence_count: int
    mapping: Dict[str, Any]
    legal_elements: list[str]
    generated_at: str


@router.get("/evidence-map/{case_id}", response_model=EvidenceMapResponse)
async def get_evidence_map(
    case_id: str,
    _principal: Principal = Depends(authorize_timeline),
    service: EvidenceMapService = Depends(get_evidence_map_service),
):
    """
    Retrieve evidence map for a case.
    
    Returns mapping of evidence to legal elements with relationships.
    """
    try:
        result = await service.map_evidence_to_elements(case_id)
        return EvidenceMapResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate evidence map: {e}")


@router.post("/evidence-map/{case_id}/analyze")
async def analyze_evidence(
    case_id: str,
    request: AnalysisRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: EvidenceMapService = Depends(get_evidence_map_service),
):
    """
    Run evidence analysis.
    
    Supports:
    - strength: Calculate evidence strength
    - gaps: Find evidence gaps
    - path: Generate argument path
    """
    try:
        if request.analysis_type == "strength":
            if not request.evidence_id:
                raise HTTPException(status_code=400, detail="evidence_id required for strength analysis")
            
            strength = await service.calculate_evidence_strength(request.evidence_id)
            return {
                "analysis_type": "strength",
                "evidence_id": strength.evidence_id,
                "score": strength.score,
                "reliability": strength.reliability,
                "reasoning": strength.reasoning,
                "factors": strength.factors,
            }
        
        elif request.analysis_type == "gaps":
            if not request.legal_theory:
                raise HTTPException(status_code=400, detail="legal_theory required for gap analysis")
            
            gaps = await service.find_evidence_gaps(case_id, request.legal_theory)
            return {
                "analysis_type": "gaps",
                "case_id": case_id,
                "legal_theory": request.legal_theory,
                "gaps": [
                    {
                        "gap_id": gap.gap_id,
                        "description": gap.description,
                        "legal_element": gap.legal_element,
                        "severity": gap.severity,
                        "suggested_evidence": gap.suggested_evidence,
                    }
                    for gap in gaps
                ],
            }
        
        elif request.analysis_type == "path":
            if not request.claim:
                raise HTTPException(status_code=400, detail="claim required for path analysis")
            
            path = await service.generate_argument_path(case_id, request.claim)
            return {
                "analysis_type": "path",
                "case_id": case_id,
                "claim": path.claim,
                "evidence_chain": path.evidence_chain,
                "strength_score": path.strength_score,
                "weak_points": path.weak_points,
            }
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid analysis_type: {request.analysis_type}. Must be 'strength', 'gaps', or 'path'"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
