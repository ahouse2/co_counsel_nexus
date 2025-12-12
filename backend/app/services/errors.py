from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict


class WorkflowComponent(str, Enum):
    """Enumeration of orchestrator components participating in agent workflows."""

    ORCHESTRATOR = "orchestrator"
    STRATEGY = "strategy"
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    GRAPH = "graph"
    FORENSICS = "forensics"
    QA = "qa"
    TIMELINE = "timeline"
    MEMORY = "memory"
    TELEMETRY = "telemetry"
    AUDIT = "audit"
    SECURITY = "security"
    SCENARIO = "scenario"
    TTS = "tts"
    ECHO = "echo"


class WorkflowSeverity(str, Enum):
    """Severity ladder for workflow errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(slots=True)
class WorkflowError:
    component: WorkflowComponent
    code: str
    message: str
    severity: WorkflowSeverity = WorkflowSeverity.ERROR
    retryable: bool = False
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempt: int = 1
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component.value,
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "occurred_at": self.occurred_at.isoformat(),
            "attempt": self.attempt,
            "context": dict(self.context),
        }


class WorkflowException(Exception):
    """Base exception conveying a structured workflow error."""

    def __init__(self, error: WorkflowError, *, status_code: int | None = None) -> None:
        super().__init__(error.message)
        self.error = error
        self.status_code = status_code


class CircuitOpenError(WorkflowException):
    """Raised when a circuit breaker prevents execution."""


class WorkflowAbort(WorkflowException):
    """Raised when a workflow stage cannot progress."""


def http_status_for_error(error: WorkflowError) -> int:
    """Map a workflow error to an HTTP status code."""

    if error.severity is WorkflowSeverity.CRITICAL:
        return 503
    if error.retryable:
        return 503
    return 400


__all__ = [
    "WorkflowComponent",
    "WorkflowSeverity",
    "WorkflowError",
    "WorkflowException",
    "WorkflowAbort",
    "CircuitOpenError",
    "http_status_for_error",
]
