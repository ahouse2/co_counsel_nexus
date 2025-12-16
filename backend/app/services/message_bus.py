from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

import redis.asyncio as redis
from backend.app.config import get_settings
from backend.app.agents.types import AgentMessage

logger = logging.getLogger(__name__)

class MessageBus:
    """
    Asynchronous Message Bus using Redis Pub/Sub for inter-agent communication.
    """

    def __init__(self):
        self.settings = get_settings()
        # Use the redis service name from docker-compose
        self.redis_url = self.settings.redis_url or "redis://redis:6379/0"
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.handlers: Dict[str, List[Callable[[AgentMessage], Any]]] = {}
        self._is_connected = False

    async def connect(self):
        """Connects to Redis."""
        if self._is_connected:
            return

        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            self._is_connected = True
            logger.info("Connected to Message Bus (Redis).")
        except Exception as e:
            logger.error(f"Failed to connect to Message Bus: {e}")
            raise

    async def disconnect(self):
        """Disconnects from Redis."""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        self._is_connected = False
        logger.info("Disconnected from Message Bus.")

    async def publish(self, message: AgentMessage, channel: str = "agent_events"):
        """Publishes a message to a specific channel."""
        if not self._is_connected:
            await self.connect()

        try:
            payload = json.dumps(message.to_dict())
            await self.redis.publish(channel, payload)
            logger.debug(f"Published message {message.message_id} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")

    async def subscribe(self, channel: str, handler: Callable[[AgentMessage], Any]):
        """Subscribes a handler to a channel."""
        if not self._is_connected:
            await self.connect()

        if channel not in self.handlers:
            self.handlers[channel] = []
            # If this is the first handler for this channel, subscribe in Redis
            if not self.pubsub:
                self.pubsub = self.redis.pubsub()
                asyncio.create_task(self._listen())
            
            await self.pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

        self.handlers[channel].append(handler)

    async def _listen(self):
        """Internal listener loop for Redis Pub/Sub."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    try:
                        payload = json.loads(data)
                        # Reconstruct AgentMessage from dict
                        # Note: timestamp parsing might be needed if not handled by fromisoformat
                        agent_message = AgentMessage(
                            message_id=payload["message_id"],
                            sender=payload["sender"],
                            recipient=payload["recipient"],
                            intent=payload["intent"],
                            payload=payload["payload"],
                            context=payload.get("context", {}),
                            timestamp=datetime.fromisoformat(payload["timestamp"]),
                            correlation_id=payload.get("correlation_id")
                        )
                        
                        if channel in self.handlers:
                            for handler in self.handlers[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(handler):
                                        await handler(agent_message)
                                    else:
                                        handler(agent_message)
                                except Exception as e:
                                    logger.error(f"Error in message handler for {channel}: {e}")
                                    
                    except Exception as e:
                        logger.error(f"Failed to process message from {channel}: {e}")
        except Exception as e:
            logger.error(f"Message Bus listener error: {e}")
            self._is_connected = False

_message_bus: Optional[MessageBus] = None

def get_message_bus() -> MessageBus:
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
    return _message_bus
