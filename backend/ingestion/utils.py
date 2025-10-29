"""Shared helper utilities for the ingestion package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union


def compute_sha256(payload: Union[Path, bytes, str]) -> str:
    """Compute a stable SHA-256 checksum for files or raw data."""

    hasher = hashlib.sha256()
    if isinstance(payload, Path):
        with payload.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    if isinstance(payload, bytes):
        hasher.update(payload)
        return hasher.hexdigest()
    if isinstance(payload, str):
        hasher.update(payload.encode("utf-8"))
        return hasher.hexdigest()
    raise TypeError(f"Unsupported payload type for checksum: {type(payload)!r}")


__all__ = ["compute_sha256"]
