"""Microsoft Agents SDK orchestration primitives for the backend."""

from __future__ import annotations

from .runner import MicrosoftAgentsOrchestrator, get_orchestrator

__all__ = ["MicrosoftAgentsOrchestrator", "get_orchestrator"]

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = ["AdaptiveAgentsOrchestrator", "get_orchestrator"]


if TYPE_CHECKING:  # pragma: no cover - import only for static analysis
    from .runner import AdaptiveAgentsOrchestrator, get_orchestrator  # noqa: F401


def __getattr__(name: str) -> Any:  # pragma: no cover - thin proxy
    if name in {"AdaptiveAgentsOrchestrator", "get_orchestrator"}:
        module = import_module(".runner", __name__)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
