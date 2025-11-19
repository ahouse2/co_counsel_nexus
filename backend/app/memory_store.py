from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Dict

class CaseMemoryStore:
    def __init__(self, root: Path = Path("storage/memory")) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, case_id: str) -> Path:
        return self.root / f"{case_id}.json"

    def load(self, case_id: str) -> Dict[str, Any]:
        path = self._path(case_id)
        if not path.exists():
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, case_id: str, data: Dict[str, Any]) -> None:
        path = self._path(case_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
