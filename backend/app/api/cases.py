from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.case_service import CaseService

router = APIRouter()

class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class CaseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

def get_case_service(db: Session = Depends(get_db)) -> CaseService:
    return CaseService(db)

@router.post("/cases", response_model=CaseResponse)
async def create_case(
    case: CaseCreate,
    service: CaseService = Depends(get_case_service)
):
    return service.create_case(case.name, case.description)

@router.get("/cases", response_model=List[CaseResponse])
async def list_cases(
    service: CaseService = Depends(get_case_service)
):
    cases = service.list_cases()
    # Convert datetime objects to strings for Pydantic
    return [
        CaseResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            status=c.status,
            created_at=c.created_at.isoformat() if c.created_at else None
        ) for c in cases
    ]

@router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    service: CaseService = Depends(get_case_service)
):
    case = service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(
        id=case.id,
        name=case.name,
        description=case.description,
        status=case.status,
        created_at=case.created_at.isoformat() if case.created_at else None
    )

@router.put("/cases/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    service: CaseService = Depends(get_case_service)
):
    case = service.update_case(case_id, case_update.name, case_update.description, case_update.status)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(
        id=case.id,
        name=case.name,
        description=case.description,
        status=case.status,
        created_at=case.created_at.isoformat() if case.created_at else None
    )

@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: str,
    service: CaseService = Depends(get_case_service)
):
    success = service.delete_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted successfully"}

@router.get("/cases/{case_id}/export")
async def export_case(
    case_id: str,
    service: CaseService = Depends(get_case_service)
):
    zip_content = service.export_case(case_id)
    if not zip_content:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=case_{case_id}_export.zip"}
    )

@router.post("/cases/import", response_model=CaseResponse)
async def import_case(
    file: UploadFile = File(...),
    service: CaseService = Depends(get_case_service)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")
    
    content = await file.read()
    try:
        case = service.import_case(content)
        return CaseResponse(
            id=case.id,
            name=case.name,
            description=case.description,
            status=case.status,
            created_at=case.created_at.isoformat() if case.created_at else None
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@router.get("/current", response_model=CaseResponse)
async def get_current_case(service: CaseService = Depends(get_case_service)):
    """Return a plausible current case for bootstrap."""
    cases = service.list_cases()
    if not cases:
        # Create default case if none exists
        return CaseResponse(
            id="default-case",
            name="Default Case",
            description="Auto-generated default case",
            status="active",
            created_at=None
        )
    
    # Return the first active case
    c = cases[0]
    return CaseResponse(
        id=c.id,
        name=c.name,
        description=c.description,
        status=c.status,
        created_at=c.created_at.isoformat() if c.created_at else None
    )
