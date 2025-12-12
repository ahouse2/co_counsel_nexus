"""
API Endpoints for Autonomous Web Scraping

Provides REST API for managing autonomous scraping triggers and execution.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from ..services.autonomous_scraper_service import (
    AutonomousScraperService,
    get_autonomous_scraper_service
)
from ..security.dependencies import authorize_research_access
from ..security.authz import Principal


router = APIRouter(prefix="/autonomous-scraping", tags=["Autonomous Scraping"])


class AddTriggerRequest(BaseModel):
    source: str = Field(..., description="Scraper source (california_codes, ecfr)")
    query: str = Field(..., description="Search query or topic")
    frequency: str = Field(..., description="Frequency: 'daily' or 'on-demand'")
    requested_by: str = Field(..., description="Team name (strategy, research, etc.)")
    priority: str = Field(default='normal', description="Priority: high, normal, low")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class TriggerResponse(BaseModel):
    trigger_id: str
    source: str
    query: str
    frequency: str
    requested_by: str
    priority: str
    enabled: bool
    last_run: Optional[str]
    created_at: str


class ScrapingResultResponse(BaseModel):
    success: bool
    source: Optional[str] = None
    query: Optional[str] = None
    total_results: Optional[int] = None
    ingested: Optional[int] = None
    skipped: Optional[int] = None
    trigger_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/triggers", response_model=TriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_scraping_trigger(
    request: AddTriggerRequest,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousScraperService = Depends(get_autonomous_scraper_service)
):
    """
    Create a new autonomous scraping trigger.
    
    - **On-demand**: Trigger can be executed manually
    - **Daily**: Automatically runs at scheduled time (2 AM for normal, 1 AM for high priority)
    """
    trigger = await service.add_trigger(
        source=request.source,
        query=request.query,
        frequency=request.frequency,
        requested_by=request.requested_by,
        priority=request.priority,
        metadata=request.metadata
    )
    
    return TriggerResponse(
        trigger_id=trigger.trigger_id,
        source=trigger.source,
        query=trigger.query,
        frequency=trigger.frequency,
        requested_by=trigger.requested_by,
        priority=trigger.priority,
        enabled=trigger.enabled,
        last_run=trigger.last_run.isoformat() if trigger.last_run else None,
        created_at=trigger.created_at.isoformat()
    )


@router.post("/triggers/{trigger_id}/execute", response_model=ScrapingResultResponse)
async def execute_trigger(
    trigger_id: str,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousScraperService = Depends(get_autonomous_scraper_service)
):
    """
    Execute a specific trigger on-demand.
    
    Scrapes content and automatically ingests to knowledge graph.
    """
    result = await service.execute_trigger(trigger_id)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Trigger execution failed')
        )
    
    return ScrapingResultResponse(**result)


@router.delete("/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_trigger(
    trigger_id: str,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousScraperService = Depends(get_autonomous_scraper_service)
):
    """Remove a scraping trigger and its schedule."""
    success = service.remove_trigger(trigger_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger {trigger_id} not found"
        )


@router.get("/triggers", response_model=List[TriggerResponse])
async def list_triggers(
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousScraperService = Depends(get_autonomous_scraper_service)
):
    """List all active scraping triggers."""
    triggers = service.list_triggers()
    return [TriggerResponse(**t) for t in triggers]


@router.post("/scrape", response_model=ScrapingResultResponse)
async def manual_scrape(
    source: str,
    query: str,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousScraperService = Depends(get_autonomous_scraper_service)
):
    """
    Execute a one-time manual scrape without creating a trigger.
    
    Useful for ad-hoc research requests.
    """
    result = await service.scrape_and_ingest(source=source, query=query)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Scraping failed')
        )
    
    return ScrapingResultResponse(**result)
