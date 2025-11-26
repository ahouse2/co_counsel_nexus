import asyncio
from typing import AsyncGenerator, Dict, Any, List
import json
from dataclasses import dataclass, field

@dataclass
class AgentEventBroadcaster:
    """
    A simple in-memory event bus for broadcasting agent events to multiple subscribers.
    """
    _subscribers: List[asyncio.Queue] = field(default_factory=list)

    async def publish(self, event: Dict[str, Any]) -> None:
        """
        Publishes an event to all active subscribers.
        """
        # Create a copy of the list to iterate safely
        for queue in list(self._subscribers):
            try:
                # Put the event in the queue without blocking
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # If a subscriber is too slow, we might drop events or disconnect them
                # For now, we just log/ignore to avoid blocking the publisher
                pass

    async def subscribe(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribes to the event stream. Yields events as they are published.
        """
        queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

# Global singleton instance
_broadcaster = AgentEventBroadcaster()

def get_agent_event_broadcaster() -> AgentEventBroadcaster:
    return _broadcaster
