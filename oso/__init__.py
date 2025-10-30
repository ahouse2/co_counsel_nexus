"""Minimal stub of the oso authorization engine for testing."""

from __future__ import annotations

from typing import Any, Iterable, List


class Oso:
    def __init__(self) -> None:
        self._classes: List[type] = []
        self._policies: List[str] = []

    def register_class(self, cls: type) -> None:
        self._classes.append(cls)

    def load_files(self, paths: Iterable[str]) -> None:
        self._policies.extend(list(paths))

    def is_allowed(self, principal: Any, action: str, resource: Any) -> bool:
        return True


__all__ = ["Oso"]
