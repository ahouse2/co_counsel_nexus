import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

async def event_generator() -> AsyncGenerator[str, None]:
    """
    Generates Server-Sent Events (SSE) for live agent activity.
    In a real implementation, this would subscribe to an event bus or Redis channel.
    """
    while True:
        # Mock data for demonstration
        # In production, replace this with real event consumption
        data = {
            "timestamp": asyncio.get_event_loop().time(),
            "type": "agent_activity",
            "agent": "DocumentIngestionSupervisor",
            "action": "delegating",
            "target": "DocumentPreprocessingTool",
            "message": "Processing new batch of documents..."
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(3)  # Send an event every 3 seconds

@router.get("/stream")
async def stream_agents():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
