from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from backend.app.services.evidence_map_service import EvidenceMapService

router = APIRouter()

@router.post("/analyze/{case_id}", summary="Extract geospatial data from timeline")
async def analyze_locations(case_id: str) -> List[Dict[str, Any]]:
    """
    Analyzes the case timeline to extract location data for the Evidence Map.
    """
    try:
        service = EvidenceMapService()
        return service.analyze_locations(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
