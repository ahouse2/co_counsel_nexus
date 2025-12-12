from dataclasses import dataclass
from typing import Any, Dict

from backend.app.agents.context import AgentContext
from backend.app.agents.base_tools import AgentTool, ToolInvocation
from backend.app.agents.types import AgentTurn
from backend.ingestion.llama_index_factory import BaseLlmService
from datetime import datetime, timezone

from backend.app.services.errors import WorkflowComponent

class EchoTool(AgentTool):
    def __init__(self, llm_service: BaseLlmService):
        super().__init__(
            name="echo",
            description="Echoes the user input using an LLM.",
            component=WorkflowComponent.ECHO,
        )
        self.llm_service = llm_service

    def invoke(self, context: AgentContext) -> ToolInvocation:
        started = datetime.now(timezone.utc)
        question = context.question
        
        # Use the LLM service to echo the question
        try:
            llm_response = self.llm_service.generate_text(f"Echo this back: {question}")
        except Exception as e:
            llm_response = f"Error echoing with LLM: {e}"
            # In a real scenario, you might want to handle this error more gracefully
            # or log it. For this PoC, we'll just return the error message.

        completed = datetime.now(timezone.utc)

        turn = AgentTurn(
            role="echo",
            action="echo_message",
            input={"question": question},
            output={"response": llm_response},
            started_at=started,
            completed_at=completed,
        )

        return ToolInvocation(
            turn=turn,
            payload={"response": llm_response},
            message=llm_response,
            metadata={"llm_used": self.llm_service.__class__.__name__},
        )
