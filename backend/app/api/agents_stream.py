import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.services.event_bus import get_agent_event_broadcaster

router = APIRouter()

async def event_generator() -> AsyncGenerator[str, None]:
    """
    Generates Server-Sent Events (SSE) for live agent activity using the real event broadcaster.
    """
    broadcaster = get_agent_event_broadcaster()
    async for event in broadcaster.subscribe():
        yield f"data: {json.dumps(event)}\n\n"

@router.get("/stream")
async def stream_agents():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
