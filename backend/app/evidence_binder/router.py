from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

# Placeholder for database interaction
# In a real application, this would interact with your PostgreSQL database

class EvidenceItem(BaseModel):
    document_id: str
    name: str
    description: Optional[str] = None
    added_at: datetime = Field(default_factory=datetime.now)

class EvidenceBinder(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    items: List[EvidenceItem] = Field(default_factory=list)

class EvidenceBinderCreate(BaseModel):
    name: str
    description: Optional[str] = None

class EvidenceBinderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

router = APIRouter()

# In-memory store for demonstration purposes
binders_db: List[EvidenceBinder] = []

@router.post("/evidence-binders", response_model=EvidenceBinder, status_code=status.HTTP_201_CREATED)
async def create_evidence_binder(binder_data: EvidenceBinderCreate):
    new_binder = EvidenceBinder(name=binder_data.name, description=binder_data.description)
    binders_db.append(new_binder)
    return new_binder

@router.get("/evidence-binders", response_model=List[EvidenceBinder])
async def get_all_evidence_binders():
    return binders_db

@router.get("/evidence-binders/{binder_id}", response_model=EvidenceBinder)
async def get_evidence_binder(binder_id: UUID):
    for binder in binders_db:
        if binder.id == binder_id:
            return binder
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence binder not found")

@router.put("/evidence-binders/{binder_id}", response_model=EvidenceBinder)
async def update_evidence_binder(binder_id: UUID, binder_data: EvidenceBinderUpdate):
    for idx, binder in enumerate(binders_db):
        if binder.id == binder_id:
            if binder_data.name is not None:
                binders_db[idx].name = binder_data.name
            if binder_data.description is not None:
                binders_db[idx].description = binder_data.description
            binders_db[idx].updated_at = datetime.now()
            return binders_db[idx]
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence binder not found")

@router.delete("/evidence-binders/{binder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence_binder(binder_id: UUID):
    global binders_db
    initial_len = len(binders_db)
    binders_db = [binder for binder in binders_db if binder.id != binder_id]
    if len(binders_db) == initial_len:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence binder not found")
    return

@router.post("/evidence-binders/{binder_id}/items", response_model=EvidenceBinder)
async def add_item_to_binder(binder_id: UUID, item: EvidenceItem):
    for binder in binders_db:
        if binder.id == binder_id:
            binder.items.append(item)
            binder.updated_at = datetime.now()
            return binder
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence binder not found")
