from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .memory import CaseThreadMemory


@dataclass(slots=True)
class AgentContext:
    """Execution context flowing across Microsoft Agents SDK graph nodes."""

    case_id: str
    question: str
    top_k: int
    actor: Dict[str, Any]
    memory: CaseThreadMemory
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **kwargs: Any) -> AgentContext:
        payload = {**self.__dict__}
        payload.update(kwargs)
        return AgentContext(**payload)
