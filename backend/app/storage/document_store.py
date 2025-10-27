from __future__ import annotations

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..utils.storage import atomic_write_json, read_json, safe_path


class DocumentStore:
    """File-backed document metadata store with traversal safeguards."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, doc_id: str) -> Path:
        return safe_path(self.root, doc_id)

    def write_document(self, doc_id: str, payload: Dict[str, object]) -> None:
        path = self._path(doc_id)
        atomic_write_json(path, payload)

    def read_document(self, doc_id: str) -> Dict[str, object]:
        path = self._path(doc_id)
        if not path.exists():
            raise FileNotFoundError(f"Document {doc_id} missing from store")
        return read_json(path)

    def list_documents(self) -> List[Dict[str, object]]:
        documents: List[Dict[str, object]] = []
        for file in sorted(self.root.glob("*.json")):
            try:
                documents.append(read_json(file))
            except (ValueError, FileNotFoundError, OSError):
                continue
        return documents

    def remove(self, doc_id: str) -> None:
        path = self._path(doc_id)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        for file in self.root.glob("*.json"):
            file.unlink()

