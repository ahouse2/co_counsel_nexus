from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass(slots=True)
class AgentTurn:
    """Structured record of an agent turn emitted by the Microsoft Agents graph."""

    role: str
    action: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    started_at: datetime
    completed_at: datetime
    metrics: Dict[str, Any] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)

    def duration_ms(self) -> float:
        return (self.completed_at - self.started_at).total_seconds() * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        metrics = dict(self.metrics)
        metrics.setdefault("duration_ms", round(self.duration_ms(), 2))
        payload = {
            "role": self.role,
            "action": self.action,
            "input": self.input,
            "output": self.output,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "metrics": metrics,
        }
        if self.annotations:
            payload["annotations"] = self.annotations
        return payload


@dataclass(slots=True)
class AgentThread:
    """In-memory representation of a Microsoft Agents SDK session thread."""

    thread_id: str
    case_id: str
    question: str
    created_at: datetime
    updated_at: datetime
    status: str = "pending"
    turns: List[AgentTurn] = field(default_factory=list)
    final_answer: str = ""
    citations: List[Dict[str, Any]] = field(default_factory=list)
    qa_scores: Dict[str, float] = field(default_factory=dict)
    qa_notes: List[str] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)
    errors: List[Any] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "case_id": self.case_id,
            "question": self.question,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "turns": [turn.to_dict() for turn in self.turns],
            "final_answer": self.final_answer,
            "citations": self.citations,
            "qa_scores": self.qa_scores,
            "qa_notes": self.qa_notes,
            "telemetry": self.telemetry,
            "errors": [error.to_dict() if hasattr(error, "to_dict") else error for error in self.errors],
            "memory": self.memory,
        }
