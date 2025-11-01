"""Test helper to provide a lightweight fallback ``oso`` implementation."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Iterable


def ensure_oso_stub() -> None:
    """Install an ``oso`` stub when the optional dependency is unavailable."""
    try:  # pragma: no cover - exercised via import side-effects
        importlib.import_module("oso")
        return
    except ModuleNotFoundError:  # pragma: no cover - fallback for test envs
        stub = types.ModuleType("oso")

    class Oso:  # type: ignore[too-many-ancestors]
        def __init__(self) -> None:
            self._registered: list[type] = []
            self._policies: list[str] = []

        def register_class(self, cls: type) -> None:  # noqa: D401 - simple stub
            """Record the registered class for inspection in tests."""
            self._registered.append(cls)

        def load_files(self, paths: Iterable[str]) -> None:  # noqa: D401 - stub
            """Record the policy paths for inspection in tests."""
            self._policies.extend(paths)

        def is_allowed(self, principal: object, action: str, resource: object) -> bool:
            raise RuntimeError("Authorization checks require the real 'oso' package in tests")

    stub.Oso = Oso
    sys.modules["oso"] = stub


ensure_oso_stub()
