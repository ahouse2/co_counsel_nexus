from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Dict, Iterable, List

import yaml

from .schema import ScenarioDefinition, ScenarioMetadata


class ScenarioRegistryError(RuntimeError):
    """Raised when the scenario registry cannot fulfil a request."""


class ScenarioRegistry:
    """Filesystem-backed scenario registry with in-memory caching."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, ScenarioDefinition] = {}
        self._lock = RLock()
        self._loaded_fingerprints: Dict[str, float] = {}
        self._sources: Dict[str, str] = {}
        self.refresh()

    def refresh(self) -> None:
        """Reload the registry from disk if files have changed."""

        with self._lock:
            for path in self._scenario_paths():
                fingerprint = path.stat().st_mtime
                cached = self._loaded_fingerprints.get(path.name)
                if cached is not None and cached >= fingerprint:
                    continue
                data = yaml.safe_load(path.read_text())
                if not isinstance(data, dict):
                    raise ScenarioRegistryError(f"Scenario file {path} must define a mapping")
                try:
                    scenario = ScenarioDefinition.model_validate(data)
                except Exception as exc:  # pragma: no cover - validation surfaces in tests
                    raise ScenarioRegistryError(f"Invalid scenario payload in {path}: {exc}") from exc
                self._cache[scenario.id] = scenario
                self._loaded_fingerprints[path.name] = fingerprint
                self._sources[scenario.id] = path.name
            # purge removed files
            existing_files = {path.name for path in self._scenario_paths()}
            for scenario_id, source in list(self._sources.items()):
                if source not in existing_files:
                    self._sources.pop(scenario_id, None)
                    self._cache.pop(scenario_id, None)
                    self._loaded_fingerprints.pop(source, None)

    def list(self) -> List[ScenarioMetadata]:
        with self._lock:
            return [
                ScenarioMetadata(
                    id=scenario.id,
                    title=scenario.title,
                    description=scenario.description,
                    category=scenario.category,
                    difficulty=scenario.difficulty,
                    tags=list(scenario.tags),
                    participants=[participant.id for participant in scenario.participants],
                )
                for scenario in sorted(self._cache.values(), key=lambda item: item.title.lower())
            ]

    def get(self, scenario_id: str) -> ScenarioDefinition:
        with self._lock:
            try:
                return self._cache[scenario_id]
            except KeyError as exc:
                raise ScenarioRegistryError(f"Scenario {scenario_id} is not registered") from exc

    def save(self, scenario: ScenarioDefinition) -> Path:
        """Persist a scenario definition back to disk and refresh cache."""

        filename = self._sources.get(scenario.id, f"{scenario.id}.yaml")
        path = self.root / filename
        payload = json.loads(scenario.model_dump_json(indent=2))
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
        self._sources[scenario.id] = path.name
        self.refresh()
        return path

    def _scenario_paths(self) -> Iterable[Path]:
        return sorted(self.root.glob("*.yml")) + sorted(self.root.glob("*.yaml"))

__all__ = ["ScenarioRegistry", "ScenarioRegistryError"]
