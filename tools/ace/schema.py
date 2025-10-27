"""Schema validation helpers for ACE artefacts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

import jsonschema

from . import ACE_PACKAGE_ROOT

SCHEMA_ROOT = Path(ACE_PACKAGE_ROOT).parents[1] / "docs" / "schemas" / "ace"


def _schema_path(name: str) -> Path:
    path = SCHEMA_ROOT / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema '{name}' not found at {path}")
    return path


@lru_cache(maxsize=8)
def _validator(name: str) -> jsonschema.Draft7Validator:
    schema = json.loads(_schema_path(name).read_text())
    resolver = jsonschema.RefResolver.from_schema(schema)
    return jsonschema.Draft7Validator(schema, resolver=resolver)


def _validate(name: str, payload: Dict[str, object]) -> None:
    validator = _validator(name)
    errors = sorted(validator.iter_errors(payload), key=lambda error: error.path)
    if errors:
        message = "; ".join(
            f"{'/'.join(str(p) for p in error.path)}: {error.message}" for error in errors
        )
        raise jsonschema.ValidationError(message)


def validate_retriever_report(payload: Dict[str, object]) -> None:
    _validate("retriever_report", payload)


def validate_planner_plan(payload: Dict[str, object]) -> None:
    _validate("planner_plan", payload)


def validate_critic_verdict(payload: Dict[str, object]) -> None:
    _validate("critic_verdict", payload)


__all__ = [
    "validate_retriever_report",
    "validate_planner_plan",
    "validate_critic_verdict",
]
