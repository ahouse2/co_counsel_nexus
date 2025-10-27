"""Filesystem helpers for ACE artefact storage."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_LOGS_ROOT = ROOT / "build_logs"


_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def _sanitise_segment(segment: str) -> str:
    cleaned = _SLUG_PATTERN.sub("-", segment.strip())
    return cleaned.strip("-") or "unknown"


def ensure_stage_directory(pr_number: str, stage: str) -> Path:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    safe_pr = _sanitise_segment(pr_number)
    safe_stage = _sanitise_segment(stage)
    target = BUILD_LOGS_ROOT / today / "ace" / safe_pr / safe_stage
    target.mkdir(parents=True, exist_ok=True)
    return target


def ensure_bundle_directory(pr_number: str) -> Path:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    safe_pr = _sanitise_segment(pr_number)
    target = BUILD_LOGS_ROOT / today / "ace" / safe_pr / "context"
    target.mkdir(parents=True, exist_ok=True)
    return target


__all__ = ["ensure_stage_directory", "ensure_bundle_directory"]
