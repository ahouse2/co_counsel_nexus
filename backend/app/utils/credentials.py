from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class CredentialRegistry:
    """Lazy-loading credential registry backed by JSON for deterministic tests."""

    def __init__(self, path: Path | None) -> None:
        self._path = Path(path).expanduser().resolve() if path else None
        self._registry: Dict[str, Dict[str, Any]] | None = None

    def _load(self) -> None:
        if self._registry is not None:
            return
        if self._path is None or not self._path.exists():
            self._registry = {}
            return
        payload = json.loads(self._path.read_text())
        if not isinstance(payload, dict):
            raise ValueError("Credential registry must be a JSON object mapping credRef to payload")
        registry: Dict[str, Dict[str, Any]] = {}
        for key, value in payload.items():
            if not isinstance(value, dict):
                raise ValueError(f"Credential entry for {key} must be an object")
            registry[str(key)] = value
        self._registry = registry

    def get(self, reference: str) -> Dict[str, Any]:
        self._load()
        assert self._registry is not None
        if reference not in self._registry:
            raise KeyError(reference)
        return dict(self._registry[reference])

    def available(self) -> Dict[str, Dict[str, Any]]:
        self._load()
        assert self._registry is not None
        return dict(self._registry)
