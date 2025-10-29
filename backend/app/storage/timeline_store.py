from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(order=True)
class TimelineEvent:
    ts: datetime
    id: str = field(compare=False)
    title: str = field(compare=False)
    summary: str = field(compare=False)
    citations: List[str] = field(default_factory=list, compare=False)
    entity_highlights: List[Dict[str, str]] = field(default_factory=list, compare=False)
    relation_tags: List[Dict[str, str]] = field(default_factory=list, compare=False)
    confidence: float | None = field(default=None, compare=False)

    def to_record(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "ts": self.ts.isoformat(),
            "title": self.title,
            "summary": self.summary,
            "citations": list(self.citations),
            "entity_highlights": list(self.entity_highlights),
            "relation_tags": list(self.relation_tags),
            "confidence": self.confidence,
        }

    @classmethod
    def from_record(cls, record: Dict[str, object]) -> "TimelineEvent":
        return cls(
            id=str(record["id"]),
            ts=datetime.fromisoformat(str(record["ts"])),
            title=str(record["title"]),
            summary=str(record["summary"]),
            citations=list(record.get("citations", [])),
            entity_highlights=list(record.get("entity_highlights", [])),
            relation_tags=list(record.get("relation_tags", [])),
            confidence=float(record["confidence"]) if record.get("confidence") is not None else None,
        )


class TimelineStore:
    """JSONL-backed storage for timeline events."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, events: Iterable[TimelineEvent]) -> None:
        if not events:
            return
        with self.path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event.to_record(), sort_keys=True) + "\n")

    def write_all(self, events: Iterable[TimelineEvent]) -> None:
        ordered = sorted(events)
        with self.path.open("w", encoding="utf-8") as handle:
            for event in ordered:
                handle.write(json.dumps(event.to_record(), sort_keys=True) + "\n")

    def read_all(self) -> List[TimelineEvent]:
        if not self.path.exists():
            return []
        records: List[TimelineEvent] = []
        for line in self.path.read_text().splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                records.append(TimelineEvent.from_record(record))
            except (KeyError, ValueError):
                continue
        return sorted(records)

