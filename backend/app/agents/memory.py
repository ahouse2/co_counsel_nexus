from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, MutableMapping

from ..storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord
from .types import AgentThread


@dataclass(slots=True)
class MemoryNamespace:
    """Mutable namespace mirroring Microsoft Agents SDK memory semantics."""

    name: str
    data: Any

    def update(self, payload: MutableMapping[str, Any]) -> None:
        if not isinstance(self.data, MutableMapping):
            raise TypeError(f"Namespace '{self.name}' does not support dict updates")
        self.data.update(payload)

    def extend(self, items: Iterable[Any]) -> None:
        if not isinstance(self.data, list):
            raise TypeError(f"Namespace '{self.name}' does not support list operations")
        for item in items:
            self.data.append(item)

    def append(self, item: Any) -> None:
        if not isinstance(self.data, list):
            raise TypeError(f"Namespace '{self.name}' does not support list operations")
        self.data.append(item)

    def snapshot(self) -> Any:
        if isinstance(self.data, list):
            return [item if not isinstance(item, MutableMapping) else dict(item) for item in self.data]
        if isinstance(self.data, MutableMapping):
            return dict(self.data)
        return self.data


@dataclass(slots=True)
class CaseThreadMemory:
    """Shared memory abstraction aligned with Microsoft Agents SDK semantics."""

    thread: AgentThread
    store: AgentMemoryStore
    state: Dict[str, Any] = field(default_factory=dict)
    _namespaces: Dict[str, MemoryNamespace] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        # Restore persisted state when resuming a thread.
        if not self.state and self.thread.memory:
            self.state.update(self.thread.memory)
        self.state.setdefault("plan", {})
        self.state.setdefault("insights", {})
        self.state.setdefault("artifacts", {})
        self.state.setdefault("qa", {})
        self.state.setdefault("notes", [])
        self.state.setdefault("directives", {})
        self.state.setdefault("conversation", [])
        self.state.setdefault("turns", [])
        self._namespaces = {
            name: MemoryNamespace(name, self.state[name]) for name in self.state.keys()
        }

    def namespace(self, name: str) -> MemoryNamespace:
        if name not in self._namespaces:
            if name in {"notes", "conversation", "turns"}:
                self.state[name] = []
            else:
                self.state[name] = {}
            self._namespaces[name] = MemoryNamespace(name, self.state[name])
        return self._namespaces[name]

    @property
    def plan(self) -> MemoryNamespace:
        return self.namespace("plan")

    @property
    def insights(self) -> MemoryNamespace:
        return self.namespace("insights")

    @property
    def artifacts(self) -> MemoryNamespace:
        return self.namespace("artifacts")

    @property
    def qa(self) -> MemoryNamespace:
        return self.namespace("qa")

    @property
    def notes(self) -> MemoryNamespace:
        return self.namespace("notes")

    @property
    def conversation(self) -> MemoryNamespace:
        return self.namespace("conversation")

    @property
    def turns(self) -> MemoryNamespace:
        return self.namespace("turns")

    def update(self, namespace: str, payload: Dict[str, Any]) -> None:
        self.namespace(namespace).update(payload)

    def append_note(self, note: str) -> None:
        self.notes.append(note)

    def record_turn(self, turn_payload: Dict[str, Any]) -> None:
        self.turns.append(turn_payload)

    def append_conversation(self, entry: Dict[str, Any]) -> None:
        self.conversation.append(entry)

    def snapshot(self) -> Dict[str, Any]:
        return {
            name: namespace.snapshot()
            for name, namespace in self._namespaces.items()
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
