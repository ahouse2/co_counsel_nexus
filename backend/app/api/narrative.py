from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel

from backend.app.services.narrative_service import NarrativeService, Contradiction
from backend.app.services.timeline_service import TimelineService
from backend.app.storage.document_store import DocumentStore
from backend.app.config import Settings, get_settings

router = APIRouter(tags=["narrative"])

def get_document_store(settings: Settings = Depends(get_settings)) -> DocumentStore:
    return DocumentStore(base_dir=settings.document_storage_path, encryption_key=settings.encryption_key)

def get_narrative_service(
    store: DocumentStore = Depends(get_document_store),
) -> NarrativeService:
    timeline_service = TimelineService()
    return NarrativeService(timeline_service, store)

class NarrativeResponse(BaseModel):
    narrative: str

@router.get("/{case_id}/generate", response_model=NarrativeResponse)
async def generate_case_narrative(
    case_id: str,
    service: NarrativeService = Depends(get_narrative_service)
):
    """
    Generates a narrative summary for the specified case.
    """
    narrative = await service.generate_narrative(case_id)
    return NarrativeResponse(narrative=narrative)

@router.get("/{case_id}/contradictions", response_model=List[Contradiction])
async def detect_case_contradictions(
    case_id: str,
    service: NarrativeService = Depends(get_narrative_service)
):
    """
    Detects contradictions in the specified case.
    """
    contradictions = await service.detect_contradictions(case_id)
    return contradictions

class BranchingNarrativeRequest(BaseModel):
    pivot_point: str
    alternative_fact: str

class BranchingNarrativeResponse(BaseModel):
    scenario_id: str
    narrative: str
    implications: List[str]

@router.post("/{case_id}/branching", response_model=BranchingNarrativeResponse)
async def generate_branching_narrative(
    case_id: str,
    request: BranchingNarrativeRequest,
    service: NarrativeService = Depends(get_narrative_service)
):
    """
    Generates an alternative narrative based on a "what if" scenario.
    """
    result = await service.generate_branching_narrative(
        case_id=case_id,
        pivot_point=request.pivot_point,
        alternative_fact=request.alternative_fact
    )
    return BranchingNarrativeResponse(
        scenario_id=result.get("scenario_id", "unknown"),
        narrative=result.get("narrative", ""),
        implications=result.get("implications", [])
    )

class StoryArcPoint(BaseModel):
    timestamp: str
    event: str
    tension_level: float # 0.0 to 1.0

class StoryArcResponse(BaseModel):
    points: List[StoryArcPoint]

@router.get("/{case_id}/story_arc", response_model=StoryArcResponse)
async def get_story_arc(
    case_id: str,
    service: NarrativeService = Depends(get_narrative_service)
):
    """
    Returns data points for visualizing the narrative arc (tension/drama over time).
    """
    arc_data = await service.generate_story_arc(case_id)
    points = [
        StoryArcPoint(
            timestamp=item.get("timestamp", ""),
            event=item.get("event", ""),
            tension_level=float(item.get("tension_level", 0.5))
        )
        for item in arc_data
    ]
    return StoryArcResponse(points=points)

