"""
Agent Console API - Backend endpoints for swarm observability.

Provides endpoints for the Agent Console frontend module:
- Real-time activity feed
- Swarm status
- Cross-swarm message log
- Pipeline progress
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SwarmStatus(BaseModel):
    """Status of a swarm."""
    name: str
    agent_count: int
    status: str  # idle, running, complete, error
    last_activity: Optional[str] = None
    pending_messages: int = 0


class ActivityEntry(BaseModel):
    """An activity log entry."""
    timestamp: str
    type: str
    swarm: Optional[str] = None
    details: str


class MessageEntry(BaseModel):
    """A cross-swarm message."""
    timestamp: str
    from_swarm: str
    to_swarm: str
    message_type: str
    content_preview: str


class PipelineStatus(BaseModel):
    """Status of autonomous pipeline."""
    case_id: str
    stage: int
    total_stages: int
    current_stage_name: str
    progress_pct: float
    completed_stages: List[str]


@router.get("/agent-console/activity")
async def get_activity_feed(limit: int = 50) -> List[Dict[str, Any]]:
    """Get the recent activity feed from all swarms and orchestrator."""
    try:
        from backend.app.services.autonomous_orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        activities = orchestrator.get_activity_log()
        
        # Also gather from CommsAgents
        from backend.app.agents.swarms.comms_agent import get_comms_agent
        swarm_names = ["ingestion", "research", "narrative", "trial_prep", 
                       "forensics", "context_engine", "legal_research", 
                       "drafting", "asset_hunter", "simulation"]
        
        for swarm_name in swarm_names:
            try:
                comms = get_comms_agent(swarm_name)
                activities.extend(comms.get_activity_log())
            except:
                pass
        
        # Sort by timestamp descending
        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get activity feed: {e}")
        return []


@router.get("/agent-console/messages")
async def get_message_log(limit: int = 100) -> List[Dict[str, Any]]:
    """Get the cross-swarm message log."""
    try:
        from backend.app.services.autonomous_orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        return orchestrator.get_message_log()[-limit:]
        
    except Exception as e:
        logger.error(f"Failed to get message log: {e}")
        return []


@router.get("/agent-console/swarms")
async def get_all_swarm_status() -> List[SwarmStatus]:
    """Get status of all swarms."""
    from backend.app.agents.swarms.registry import get_swarm_registry
    from backend.app.agents.swarms.comms_agent import get_comms_agent
    
    registry = get_swarm_registry()
    swarms_info = registry.list_swarms()
    
    statuses = []
    for swarm_name, agent_count in swarms_info.items():
        try:
            comms = get_comms_agent(swarm_name)
            activity_log = comms.get_activity_log()
            last_activity = activity_log[-1]["timestamp"] if activity_log else None
            pending = len(comms.message_queue)
        except:
            last_activity = None
            pending = 0
        
        statuses.append(SwarmStatus(
            name=swarm_name,
            agent_count=agent_count,
            status="idle",  # Could be enhanced with actual tracking
            last_activity=last_activity,
            pending_messages=pending
        ))
    
    return statuses


@router.get("/agent-console/swarm/{swarm_name}")
async def get_swarm_details(swarm_name: str) -> Dict[str, Any]:
    """Get detailed status for a specific swarm."""
    from backend.app.agents.swarms.comms_agent import get_comms_agent
    
    try:
        comms = get_comms_agent(swarm_name)
        
        return {
            "name": swarm_name,
            "activity_log": comms.get_activity_log()[-20:],
            "pending_messages": len(comms.message_queue),
            "sent_messages": len(comms.sent_messages),
            "message_queue": [
                {
                    "from": m.from_swarm,
                    "type": m.message_type,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in comms.message_queue[-10:]
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Swarm not found: {swarm_name}")


@router.post("/agent-console/trigger-pipeline/{case_id}")
async def trigger_autonomous_pipeline(case_id: str) -> Dict[str, Any]:
    """Manually trigger the full autonomous pipeline for a case."""
    from backend.app.services.autonomous_orchestrator import get_orchestrator, SystemEvent, EventType
    
    try:
        orchestrator = get_orchestrator()
        
        # Publish batch complete event to trigger full pipeline
        await orchestrator.publish(SystemEvent(
            event_type=EventType.BATCH_INGESTION_COMPLETE,
            case_id=case_id,
            source_service="AgentConsole",
            payload={"doc_count": 0, "manual_trigger": True}
        ))
        
        return {
            "success": True,
            "message": f"Autonomous pipeline triggered for case {case_id}",
            "case_id": case_id
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-console/orchestrator")
async def get_orchestrator_status() -> Dict[str, Any]:
    """Get orchestrator status and stats."""
    from backend.app.services.autonomous_orchestrator import get_orchestrator
    
    try:
        orchestrator = get_orchestrator()
        
        return {
            "running": orchestrator._running,
            "processed_events": orchestrator._processed_count,
            "pending_events": orchestrator._event_queue.qsize(),
            "registered_handlers": len(orchestrator._handlers),
            "message_queue_size": len(orchestrator._message_log),
            "recent_activity": orchestrator.get_activity_log()[-10:]
        }
        
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        return {"error": str(e)}
