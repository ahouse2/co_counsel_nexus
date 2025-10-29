"""Persistence layer for cost tracking events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Iterator, List, Optional


def _serialize_datetime(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass(slots=True)
class CostEventRecord:
    """Structured representation for persisted cost events."""

    event_id: str
    timestamp: datetime
    tenant_id: str | None
    category: str
    name: str
    amount: float
    unit: str
    metadata: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        payload = {
            "event_id": self.event_id,
            "timestamp": _serialize_datetime(self.timestamp),
            "tenant_id": self.tenant_id,
            "category": self.category,
            "name": self.name,
            "amount": self.amount,
            "unit": self.unit,
            "metadata": self.metadata,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "CostEventRecord":
        timestamp_raw = payload.get("timestamp")
        if not isinstance(timestamp_raw, str):
            raise ValueError("Cost event missing timestamp")
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        return cls(
            event_id=str(payload.get("event_id")),
            timestamp=_parse_datetime(timestamp_raw),
            tenant_id=str(payload.get("tenant_id")) if payload.get("tenant_id") else None,
            category=str(payload.get("category")),
            name=str(payload.get("name")),
            amount=float(payload.get("amount", 0.0)),
            unit=str(payload.get("unit", "unit")),
            metadata=dict(metadata),
        )


class CostStore:
    """Append-only JSONL store for cost tracking events."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: CostEventRecord) -> None:
        payload = record.to_dict()
        line = json.dumps(payload, separators=(",", ":"))
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def iter_events(self) -> Iterator[CostEventRecord]:
        if not self._path.exists():
            return iter(())
        with self._lock:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        def _generator() -> Iterator[CostEventRecord]:
            for line in lines:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                try:
                    yield CostEventRecord.from_dict(payload)
                except Exception:
                    continue
        return _generator()

    def list_events(
        self,
        *,
        limit: Optional[int] = None,
        tenant_id: str | None = None,
        category: str | None = None,
    ) -> List[CostEventRecord]:
        events: List[CostEventRecord] = []
        for record in self.iter_events():
            if tenant_id and record.tenant_id != tenant_id:
                continue
            if category and record.category != category:
                continue
            events.append(record)
        events.sort(key=lambda record: record.timestamp, reverse=True)
        if limit is not None:
            return events[:limit]
        return events

    def clear(self) -> None:
        with self._lock:
            self._path.write_text("", encoding="utf-8")


__all__ = ["CostEventRecord", "CostStore"]
