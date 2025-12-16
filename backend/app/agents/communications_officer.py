from __future__ import annotations

import logging
from typing import Any, Dict, List
from datetime import datetime, timezone
import uuid

from backend.app.agents.types import AgentMessage
from backend.app.services.message_bus import get_message_bus, MessageBus
from backend.app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

class CommunicationsOfficerAgent:
    """
    Agent responsible for routing messages, summarizing context, and managing
    Human-in-the-Loop interactions.
    """

    def __init__(self):
        self.message_bus = get_message_bus()
        self.llm_service = get_llm_service()
        self.agent_id = "communications_officer"
        self.subscribed_channels = ["agent_events", "human_interaction"]

    async def start(self):
        """Starts the agent and subscribes to channels."""
        await self.message_bus.connect()
        for channel in self.subscribed_channels:
            await self.message_bus.subscribe(channel, self.handle_message)
        logger.info(f"{self.agent_id} started and listening.")

    async def handle_message(self, message: AgentMessage):
        """Main message handler."""
        # Ignore messages sent by self to avoid loops
        if message.sender == self.agent_id:
            return

        logger.info(f"Comm Officer received message: {message.intent} from {message.sender}")

        if message.intent == "REQUEST_HUMAN_INTERVENTION":
            await self.handle_human_intervention(message)
        elif message.intent == "BROADCAST_UPDATE":
            await self.handle_broadcast(message)
        # Add more routing logic here

    async def handle_human_intervention(self, message: AgentMessage):
        """
        Handles requests for human intervention.
        In a real scenario, this would push a notification to the frontend.
        """
        logger.info(f"Human intervention requested by {message.sender}: {message.payload}")
        
        # For now, we just acknowledge it and log it.
        # Future: Push to WebSocket / Notification Service
        
        response = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=message.sender,
            intent="HUMAN_INTERVENTION_ACK",
            payload={"status": "queued", "message": "User notified (simulated)."},
            correlation_id=message.message_id
        )
        await self.message_bus.publish(response, channel=f"agent_inbox_{message.sender}")

    async def handle_broadcast(self, message: AgentMessage):
        """
        Broadcasts important updates to all relevant agents.
        """
        # Example: Summarize the update using LLM before broadcasting
        summary = await self._summarize_update(message.payload.get("content", ""))
        
        broadcast_msg = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient="all",
            intent="SYSTEM_UPDATE",
            payload={"summary": summary, "original_source": message.sender},
            correlation_id=message.message_id
        )
        await self.message_bus.publish(broadcast_msg, channel="global_broadcast")

    async def _summarize_update(self, content: str) -> str:
        """Uses LLM to summarize content."""
        if not content:
            return "No content to summarize."
            
        prompt = f"Summarize the following system update for other agents:\n\n{content}"
        try:
            return await self.llm_service.generate_text(prompt)
        except Exception as e:
            logger.error(f"Failed to summarize: {e}")
            return content[:100] + "..."

_comm_officer: CommunicationsOfficerAgent | None = None

def get_communications_officer() -> CommunicationsOfficerAgent:
    global _comm_officer
    if _comm_officer is None:
        _comm_officer = CommunicationsOfficerAgent()
    return _comm_officer
