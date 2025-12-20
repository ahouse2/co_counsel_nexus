from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel

from backend.app.services.devils_advocate_service import DevilsAdvocateService, CaseWeakness, CrossExamQuestion
from backend.app.services.timeline_service import TimelineService
from backend.app.storage.document_store import DocumentStore
from backend.app.config import Settings, get_settings

router = APIRouter(tags=["devils_advocate"])

def get_document_store(settings: Settings = Depends(get_settings)) -> DocumentStore:
    return DocumentStore(base_dir=settings.document_storage_path, encryption_key=settings.encryption_key)

def get_devils_advocate_service(
    store: DocumentStore = Depends(get_document_store),
) -> DevilsAdvocateService:
    timeline_service = TimelineService()
    return DevilsAdvocateService(timeline_service, store)

class CrossExamRequest(BaseModel):
    witness_statement: str
    witness_profile: str = ""

class ReviewRequest(BaseModel):
    case_theory: str = ""

@router.post("/{case_id}/review", response_model=List[CaseWeakness])
async def review_case(
    case_id: str,
    request: ReviewRequest,
    service: DevilsAdvocateService = Depends(get_devils_advocate_service)
):
    """
    Triggers a Devil's Advocate review of the case to find weaknesses, optionally based on a provided theory.
    """
    return await service.review_case(case_id, request.case_theory)

@router.post("/cross-examine", response_model=List[CrossExamQuestion])
async def generate_cross_examination(
    request: CrossExamRequest,
    service: DevilsAdvocateService = Depends(get_devils_advocate_service)
):
    """
    Generates cross-examination questions for a witness statement.
    """
    return await service.generate_cross_examination(request.witness_statement, request.witness_profile)

class MotionToDismissRequest(BaseModel):
    grounds: List[str]

class MotionToDismissResponse(BaseModel):
    motion_text: str
    likelihood_of_success: float

@router.post("/{case_id}/motion_to_dismiss", response_model=MotionToDismissResponse)
async def generate_motion_to_dismiss(
    case_id: str,
    request: MotionToDismissRequest,
    service: DevilsAdvocateService = Depends(get_devils_advocate_service)
):
    """
    Generates a draft Motion to Dismiss based on identified weaknesses/grounds.
    """
    # Mock logic
    return MotionToDismissResponse(
        motion_text=f"COMES NOW the Defendant, by and through undersigned counsel, and moves this Court to dismiss... based on {', '.join(request.grounds)}...",
        likelihood_of_success=0.45
    )

@router.get("/{case_id}/evidence_graph")
async def get_evidence_graph(
    case_id: str,
    service: DevilsAdvocateService = Depends(get_devils_advocate_service)
):
    """
    Returns evidence support graph from Knowledge Graph for visualization.
    Includes nodes (causes, evidence) and edges (support/contradiction relationships).
    """
    return await service.get_evidence_graph(case_id)

