"""Lightweight test stub for the microsoft-autogen package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List


@dataclass
class ConversableAgent:
    name: str
    llm_config: Any = None
    system_message: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        self.history: List[dict[str, Any]] = []


@dataclass
class GroupChat:
    agents: List[ConversableAgent]
    messages: List[dict[str, Any]] = field(default_factory=list)
    speaker_selection_method: str = "manual"
    max_round: int = 12

    def __init__(
        self,
        agents: Iterable[ConversableAgent],
        messages: Iterable[dict[str, Any]] | None = None,
        speaker_selection_method: str = "manual",
        max_round: int = 12,
    ) -> None:
        self.agents = list(agents)
        self.messages = list(messages or [])
        self.speaker_selection_method = speaker_selection_method
        self.max_round = max_round


__all__ = ["ConversableAgent", "GroupChat"]
