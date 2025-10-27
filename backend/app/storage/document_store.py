from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class DocumentStore:
    """File-backed document metadata store.

    Documents are persisted as prettified JSON payloads named by their identifier.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, doc_id: str) -> Path:
        safe_id = doc_id.replace("/", "_")
        return self.root / f"{safe_id}.json"

    def write_document(self, doc_id: str, payload: Dict[str, object]) -> None:
        path = self._path(doc_id)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def read_document(self, doc_id: str) -> Dict[str, object]:
        path = self._path(doc_id)
        if not path.exists():
            raise FileNotFoundError(f"Document {doc_id} missing from store")
        return json.loads(path.read_text())

    def list_documents(self) -> List[Dict[str, object]]:
        documents: List[Dict[str, object]] = []
        for file in sorted(self.root.glob("*.json")):
            try:
                documents.append(json.loads(file.read_text()))
            except json.JSONDecodeError:
                continue
        return documents

    def remove(self, doc_id: str) -> None:
        path = self._path(doc_id)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        for file in self.root.glob("*.json"):
            file.unlink()

