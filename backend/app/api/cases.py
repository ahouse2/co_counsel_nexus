from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.document import Document as DocumentModel

router = APIRouter()

class Case(BaseModel):
    id: str

@router.get("/cases", response_model=List[Case])
async def get_cases(db: Session = Depends(get_db)):
    """
    Get all cases.
    """
    # This is a simplified implementation. In a real application, you would have a separate "cases" table.
    # For now, we will just get the distinct case_ids from the documents.
    cases = db.query(DocumentModel.case_id).distinct().all()
    return [{"id": case[0]} for case in cases]
