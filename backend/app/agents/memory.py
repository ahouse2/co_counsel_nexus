from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from ..storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord
from .types import AgentThread


@dataclass(slots=True)
class CaseThreadMemory:
    """Shared memory abstraction aligned with Microsoft Agents SDK semantics."""

    thread: AgentThread
    store: AgentMemoryStore
    state: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.state.setdefault("plan", {})
        self.state.setdefault("insights", {})
        self.state.setdefault("artifacts", {})
        self.state.setdefault("qa", {})
        self.state.setdefault("notes", [])

    def update(self, namespace: str, payload: Dict[str, Any]) -> None:
        entry = self.state.setdefault(namespace, {})
        entry.update(payload)

    def append_note(self, note: str) -> None:
        notes = self.state.setdefault("notes", [])
        notes.append(note)

    def record_turn(self, turn_payload: Dict[str, Any]) -> None:
        turns = self.state.setdefault("turns", [])
        turns.append(turn_payload)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "plan": dict(self.state.get("plan", {})),
            "insights": dict(self.state.get("insights", {})),
            "artifacts": dict(self.state.get("artifacts", {})),
            "qa": dict(self.state.get("qa", {})),
            "notes": list(self.state.get("notes", [])),
            "turns": list(self.state.get("turns", [])),
        }

    def persist(self) -> None:
        self.thread.memory = self.snapshot()
        payload = self.thread.to_payload()
        record = AgentThreadRecord(thread_id=self.thread.thread_id, payload=payload)
        self.store.write(record)

    def mark_updated(self) -> None:
        tz = self.thread.created_at.tzinfo or timezone.utc
        self.thread.updated_at = datetime.now(tz)
        self.persist()
