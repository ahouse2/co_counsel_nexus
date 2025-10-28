from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from typing import Any, Dict

_IDENTIFIER_PATTERN = re.compile(r"[^A-Za-z0-9._-]")


def sanitise_identifier(value: str) -> str:
    """Normalise identifiers used for file names to prevent traversal."""

    cleaned = _IDENTIFIER_PATTERN.sub("_", value)
    cleaned = cleaned.strip("._")
    if not cleaned:
        cleaned = sha256(value.encode("utf-8")).hexdigest()
    return cleaned


def safe_path(root: Path, name: str, suffix: str = ".json") -> Path:
    root = root.resolve()
    safe_name = sanitise_identifier(name)
    candidate = (root / f"{safe_name}{suffix}").resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"Resolved path {candidate} escapes storage root {root}")
    return candidate


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    temp_path.replace(path)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())
