from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class JobStore:
    """Persistence layer for ingestion job manifests."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        safe_id = job_id.replace("/", "_")
        return self.root / f"{safe_id}.json"

    def write_job(self, job_id: str, payload: Dict[str, object]) -> None:
        self._path(job_id).write_text(json.dumps(payload, indent=2, sort_keys=True))

    def read_job(self, job_id: str) -> Dict[str, object]:
        path = self._path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Job {job_id} missing from store")
        return json.loads(path.read_text())

    def list_jobs(self) -> List[Dict[str, object]]:
        manifests: List[Dict[str, object]] = []
        for file in sorted(self.root.glob("*.json")):
            try:
                manifests.append(json.loads(file.read_text()))
            except json.JSONDecodeError:
                continue
        return manifests

    def clear(self) -> None:
        for file in self.root.glob("*.json"):
            file.unlink()

