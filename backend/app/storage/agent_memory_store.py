from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from ..utils.storage import atomic_write_json, safe_path


@dataclass
class AgentThreadRecord:
    """In-memory representation of a multi-agent thread."""

    thread_id: str
    payload: Dict[str, object]

    def to_json(self) -> Dict[str, object]:
        return dict(self.payload)


class AgentMemoryStore:
    """Filesystem-backed persistence for agent conversation threads."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, thread_id: str) -> Path:
        return safe_path(self.root, thread_id)

    def write(self, record: AgentThreadRecord) -> None:
        path = self._path(record.thread_id)
        atomic_write_json(path, record.to_json())

    def read(self, thread_id: str) -> Dict[str, object]:
        path = self._path(thread_id)
        if not path.exists():
            raise FileNotFoundError(f"Agent thread {thread_id} not found")
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Thread payload for {thread_id} is not a JSON object")
        return data

    def list_threads(self) -> List[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    def purge(self, thread_ids: Iterable[str]) -> None:
        for thread_id in thread_ids:
            path = self._path(thread_id)
            if path.exists():
                path.unlink()

