"""
API Endpoints for Autonomous CourtListener Monitoring

Provides REST API for managing CourtListener monitors and execution.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from ..services.autonomous_courtlistener_service import (
    AutonomousCourtListenerService,
    get_autonomous_courtlistener_service
)
from ..security.dependencies import authorize_research_access
from ..security.authz import Principal


router = APIRouter(prefix="/autonomous-courtlistener", tags=["Autonomous CourtListener"])


class AddMonitorRequest(BaseModel):
    monitor_type: str = Field(..., description="Monitor type: 'keyword' or 'citation'")
    value: str = Field(..., description="Keyword string or citation (e.g., '550 U.S. 544')")
    requested_by: str = Field(..., description="Team/user requesting monitoring")
    check_interval_hours: int = Field(default=6, description="Check interval in hours")
    priority: str = Field(default='normal', description="Priority: high, normal, low")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class MonitorResponse(BaseModel):
    monitor_id: str
    monitor_type: str
    value: str
    requested_by: str
    check_interval_hours: int
    priority: str
    enabled: bool
    last_check: Optional[str]
    last_results_count: int
    created_at: str


class MonitorResultResponse(BaseModel):
    success: bool
    monitor_id: Optional[str] = None
    monitor_type: Optional[str] = None
    value: Optional[str] = None
    new_opinions: Optional[int] = None
    ingested: Optional[int] = None
    total_results: Optional[int] = None
    error: Optional[str] = None


@router.post("/monitors", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    request: AddMonitorRequest,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousCourtListenerService = Depends(get_autonomous_courtlistener_service)
):
    """
    Create a new CourtListener monitor.
    
    - **keyword**: Monitor for opinions matching specific keywords
    - **citation**: Track opinions citing a specific case
    
    Monitors run automatically at specified intervals.
    """
    monitor = await service.add_monitor(
        monitor_type=request.monitor_type,
        value=request.value,
        requested_by=request.requested_by,
        check_interval_hours=request.check_interval_hours,
        priority=request.priority,
        metadata=request.metadata
    )
    
    return MonitorResponse(
        monitor_id=monitor.monitor_id,
        monitor_type=monitor.monitor_type,
        value=monitor.value,
        requested_by=monitor.requested_by,
        check_interval_hours=monitor.check_interval_hours,
        priority=monitor.priority,
        enabled=monitor.enabled,
        last_check=monitor.last_check.isoformat() if monitor.last_check else None,
        last_results_count=monitor.last_results_count,
        created_at=monitor.created_at.isoformat()
    )


@router.post("/monitors/{monitor_id}/execute", response_model=MonitorResultResponse)
async def execute_monitor(
    monitor_id: str,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousCourtListenerService = Depends(get_autonomous_courtlistener_service)
):
    """
    Execute a monitor check on-demand.
    
    Queries CourtListener API for new opinions and ingests to knowledge graph.
    """
    result = await service.execute_monitor(monitor_id)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Monitor execution failed')
        )
    
    return MonitorResultResponse(**result)


@router.delete("/monitors/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_monitor(
    monitor_id: str,
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousCourtListenerService = Depends(get_autonomous_courtlistener_service)
):
    """Remove a CourtListener monitor and its schedule."""
    success = service.remove_monitor(monitor_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitor {monitor_id} not found"
        )


@router.get("/monitors", response_model=List[MonitorResponse])
async def list_monitors(
    _principal: Principal = Depends(authorize_research_access),
    service: AutonomousCourtListenerService = Depends(get_autonomous_courtlistener_service)
):
    """List all active CourtListener monitors."""
    monitors = service.list_monitors()
    return [MonitorResponse(**m) for m in monitors]
