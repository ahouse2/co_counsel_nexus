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
