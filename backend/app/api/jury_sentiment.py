"""API endpoints for jury sentiment analysis and prediction."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..security.dependencies import Principal, authorize_timeline
from ..services.jury_sentiment import JurySentimentService, get_jury_sentiment_service


router = APIRouter()


class ArgumentAnalysisRequest(BaseModel):
    """Request for argument sentiment analysis."""
    text: str = Field(..., description="Argument text to analyze")


class JurySimulationRequest(BaseModel):
    """Request for jury simulation."""
    argument: str = Field(..., description="Argument to test")
    jury_profile: Dict[str, Any] = Field(..., description="Jury demographics and characteristics")


class CredibilityRequest(BaseModel):
    """Request for witness credibility scoring."""
    witness_id: str = Field(..., description="Witness identifier")
    testimony: str = Field(..., description="Testimony text")


@router.post("/jury-sentiment/analyze-argument")
async def analyze_argument(
    request: ArgumentAnalysisRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: JurySentimentService = Depends(get_jury_sentiment_service),
):
    """
    Analyze argument for sentiment and persuasiveness.
    
    Returns scores, emotional tone, strengths, weaknesses, and recommendations.
    """
    try:
        analysis = await service.analyze_argument_sentiment(request.text)
        return {
            "text": analysis.text,
            "overall_score": analysis.overall_score,
            "emotional_tone": analysis.emotional_tone,
            "strengths": analysis.strengths,
            "weaknesses": analysis.weaknesses,
            "recommendations": analysis.recommendations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


class JurorProfileModel(BaseModel):
    id: str
    name: str
    demographics: str
    occupation: str
    bias: str
    temperament: str

class IndividualJurySimulationRequest(BaseModel):
    argument: str
    jurors: list[JurorProfileModel]

@router.post("/jury-sentiment/simulate-individuals")
async def simulate_individual_jury(
    request: IndividualJurySimulationRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: JurySentimentService = Depends(get_jury_sentiment_service),
):
    """
    Simulate reactions of specific individual jurors.
    """
    try:
        # Convert Pydantic models to dataclasses
        from ..services.jury_sentiment import JurorPersona
        juror_personas = [
            JurorPersona(
                id=j.id,
                name=j.name,
                demographics=j.demographics,
                occupation=j.occupation,
                bias=j.bias,
                temperament=j.temperament
            ) for j in request.jurors
        ]
        
        reactions = await service.simulate_individual_jurors(
            request.argument,
            juror_personas
        )
        
        return [
            {
                "juror_id": r.juror_id,
                "sentiment_score": r.sentiment_score,
                "reaction": r.reaction,
                "internal_thought": r.internal_thought
            }
            for r in reactions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")


@router.post("/jury-sentiment/simulate-jury")
async def simulate_jury(
    request: JurySimulationRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: JurySentimentService = Depends(get_jury_sentiment_service),
):
    """
    Simulate jury response to an argument.
    
    Returns predicted reactions based on jury demographics.
    """
    try:
        response = await service.simulate_jury_response(
            request.argument,
            request.jury_profile,
        )
        return {
            "jury_profile": response.jury_profile,
            "receptiveness_score": response.receptiveness_score,
            "predicted_reactions": response.predicted_reactions,
            "concerns": response.concerns,
            "resonance_factors": response.resonance_factors,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")


@router.post("/jury-sentiment/score-credibility")
async def score_credibility(
    request: CredibilityRequest,
    _principal: Principal = Depends(authorize_timeline),
    service: JurySentimentService = Depends(get_jury_sentiment_service),
):
    """
    Score witness credibility based on testimony.
    
    Returns credibility score and analysis.
    """
    try:
        score = await service.score_witness_credibility(
            request.witness_id,
            request.testimony,
        )
        return {
            "witness_id": score.witness_id,
            "score": score.score,
            "credibility_factors": score.credibility_factors,
            "red_flags": score.red_flags,
            "strengths": score.strengths,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")


@router.get("/jury-sentiment/{case_id}/report")
async def get_sentiment_report(
    case_id: str,
    _principal: Principal = Depends(authorize_timeline),
    service: JurySentimentService = Depends(get_jury_sentiment_service),
):
    """
    Generate comprehensive sentiment report for a case.
    
    Aggregates all sentiment analyses and witness credibility scores for the case.
    """
    try:
        from datetime import datetime
        
        # In a real implementation, this would query a database for all analyses
        # For now, we return a properly structured report template
        report = {
            "case_id": case_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_arguments_analyzed": 0,
                "total_witnesses_scored": 0,
                "average_argument_score": 0.0,
                "average_credibility_score": 0.0,
            },
            "arguments": [],
            "witnesses": [],
            "recommendations": [
                "Begin analyzing arguments using the /jury-sentiment/analyze-argument endpoint",
                "Score witness credibility using the /jury-sentiment/score-credibility endpoint",
                "Run jury simulations to test different argument approaches"
            ],
            "status": "ready_for_analysis"
        }
        
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate sentiment report: {e}"
        )

@router.get("/jury-sentiment/{case_id}/parties")
async def get_case_parties(
    case_id: str,
    _principal: Principal = Depends(authorize_timeline),
    service: JurySentimentService = Depends(get_jury_sentiment_service),
):
    """
    Get parties, witnesses, and entities involved in the case from the Knowledge Graph.
    """
    try:
        return await service.get_case_parties(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get case parties: {e}")
