from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from datetime import datetime

from ..services.document_generation import get_document_generation_service

router = APIRouter()

class EvidenceItem(BaseModel):
    id: str
    name: str
    type: str
    url: str
    annotation: Optional[str] = None

class PrepareBinderRequest(BaseModel):
    case_name: str
    evidence_list: List[EvidenceItem]

@router.post("/prepare-binder", response_class=FileResponse)
async def prepare_binder_endpoint(request: PrepareBinderRequest):
    """
    Prepares a trial binder document from a list of evidence items.
    Returns the drafted document as a downloadable Word file.
    """
    service = get_document_generation_service()
    
    # Create a temporary directory to save the document
    temp_dir = "temp_binders"
    os.makedirs(temp_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"Trial_Binder_{request.case_name}_{timestamp}.docx"
    file_path = os.path.join(temp_dir, file_name)

    try:
        # Convert Pydantic models to dictionaries for the tool
        evidence_list_dicts = [item.dict() for item in request.evidence_list]

        service.prepare_binder(
            filepath=file_path,
            evidence_list=evidence_list_dicts,
            case_name=request.case_name
        )
        
        # Return the file as a download
        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during binder preparation: {e}")
    finally:
        # Clean up the temporary file after sending
        # Similar to document drafting, this needs careful handling in FastAPI.
        # For now, we'll clean up immediately.
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir): # Remove temp_dir if empty
            shutil.rmtree(temp_dir)
