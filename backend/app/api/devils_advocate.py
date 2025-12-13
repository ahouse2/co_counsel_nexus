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

@router.get("/{case_id}/review", response_model=List[CaseWeakness])
async def review_case(
    case_id: str,
    service: DevilsAdvocateService = Depends(get_devils_advocate_service)
):
    """
    Triggers a Devil's Advocate review of the case to find weaknesses.
    """
    return await service.review_case(case_id)

@router.post("/cross-examine", response_model=List[CrossExamQuestion])
async def generate_cross_examination(
    request: CrossExamRequest,
    service: DevilsAdvocateService = Depends(get_devils_advocate_service)
):
    """
    Generates cross-examination questions for a witness statement.
    """
    return await service.generate_cross_examination(request.witness_statement, request.witness_profile)
