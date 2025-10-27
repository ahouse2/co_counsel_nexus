"""Configuration loader for the ACE automation toolkit."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import ACE_PACKAGE_ROOT


@dataclass(frozen=True)
class Thresholds:
    """Gating thresholds for rubric evaluation."""

    average_min: float
    category_min: float


@dataclass(frozen=True)
class CommandConfig:
    """Configuration for a command executed during a stage."""

    name: str
    command: List[str]
    optional: bool = False
    working_directory: str = "."
    env: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanCommandConfig:
    """Command that will be synthesised into the planner output."""

    name: str
    description: str
    command: List[str]
    rubric_categories: List[str]
    continue_on_error: bool = False


@dataclass(frozen=True)
class ACEConfig:
    """Top-level configuration for ACE."""

    thresholds: Thresholds
    static_analysis: List[CommandConfig]
    planner_commands: List[PlanCommandConfig]
    rubric_categories: List[str]


def _default_config_path() -> Path:
    env_value = os.environ.get("ACE_CONFIG_PATH")
    if env_value:
        candidate = Path(env_value)
        if candidate.is_dir():
            raise IsADirectoryError(
                f"ACE_CONFIG_PATH points to a directory, expected file: {candidate}"
            )
        return candidate
    return Path(ACE_PACKAGE_ROOT) / "config" / "default.json"


def _load_raw_config(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"ACE configuration file not found: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("ACE configuration must be a JSON object")
    return payload


def _coerce_command(entry: Dict[str, object], *, kind: str) -> CommandConfig:
    name = str(entry["name"])
    command = [str(part) for part in entry["command"]]
    optional = bool(entry.get("optional", False))
    working_directory = str(entry.get("working_directory", "."))
    env_mapping: Dict[str, str] = {}
    if "env" in entry:
        env_mapping = {str(k): str(v) for k, v in dict(entry["env"]).items()}
    return CommandConfig(
        name=name,
        command=command,
        optional=optional,
        working_directory=working_directory,
        env=env_mapping,
    )


def _coerce_plan_command(entry: Dict[str, object]) -> PlanCommandConfig:
    name = str(entry["name"])
    command = [str(part) for part in entry["command"]]
    rubric_categories = [str(item) for item in entry.get("rubric_categories", [])]
    description = str(entry.get("description", name))
    continue_on_error = bool(entry.get("continue_on_error", False))
    if not rubric_categories:
        raise ValueError(f"Planner command '{name}' is missing rubric categories")
    return PlanCommandConfig(
        name=name,
        description=description,
        command=command,
        rubric_categories=rubric_categories,
        continue_on_error=continue_on_error,
    )


def _load_thresholds(raw: Dict[str, object]) -> Thresholds:
    average_min = float(os.environ.get("ACE_AVERAGE_MIN", raw["average_min"]))
    category_min = float(os.environ.get("ACE_CATEGORY_MIN", raw["category_min"]))
    return Thresholds(average_min=average_min, category_min=category_min)


def load_config(path: Optional[Path] = None) -> ACEConfig:
    """Load ACE configuration from disk, applying environment overrides."""

    config_path = path or _default_config_path()
    raw = _load_raw_config(config_path)

    thresholds = _load_thresholds(dict(raw.get("thresholds", {})))

    static_analysis_entries: Iterable[Dict[str, object]] = raw.get("static_analysis", [])
    static_analysis = [
        _coerce_command(dict(entry), kind="static_analysis")
        for entry in static_analysis_entries
    ]

    planner_entries: Iterable[Dict[str, object]] = raw.get("planner_commands", [])
    planner_commands = [
        _coerce_plan_command(dict(entry))
        for entry in planner_entries
    ]

    rubric_categories = [str(item) for item in raw.get("rubric_categories", [])]
    if len(rubric_categories) != 15:
        raise ValueError(
            "ACE configuration must define exactly 15 rubric categories to align with governance standards"
        )

    return ACEConfig(
        thresholds=thresholds,
        static_analysis=static_analysis,
        planner_commands=planner_commands,
        rubric_categories=rubric_categories,
    )


__all__ = [
    "ACEConfig",
    "CommandConfig",
    "PlanCommandConfig",
    "Thresholds",
    "load_config",
]
