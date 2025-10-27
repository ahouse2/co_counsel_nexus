from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..utils.storage import atomic_write_json, read_json, safe_path


class JobStore:
    """Persistence layer for ingestion job manifests with traversal safeguards."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return safe_path(self.root, job_id)

    def write_job(self, job_id: str, payload: Dict[str, object]) -> None:
        path = self._path(job_id)
        atomic_write_json(path, payload)

    def read_job(self, job_id: str) -> Dict[str, object]:
        path = self._path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Job {job_id} missing from store")
        return read_json(path)

    def list_jobs(self) -> List[Dict[str, object]]:
        manifests: List[Dict[str, object]] = []
        for file in sorted(self.root.glob("*.json")):
            try:
                manifests.append(read_json(file))
            except (ValueError, FileNotFoundError, OSError):
                continue
        return manifests

    def clear(self) -> None:
        for file in self.root.glob("*.json"):
            file.unlink()

