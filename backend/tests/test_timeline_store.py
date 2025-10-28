from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.storage.timeline_store import TimelineEvent, TimelineStore

def test_timeline_store_append_and_read(tmp_path: Path) -> None:
    store = TimelineStore(tmp_path / "timeline.jsonl")
    events = [
        TimelineEvent(
            id="evt-1",
            ts=datetime(2024, 10, 1, tzinfo=timezone.utc),
            title="Event One",
            summary="Summary",
            citations=["doc-1"],
            entity_highlights=[{"id": "entity-1", "label": "Entity", "type": "Entity", "doc": "doc-1"}],
            relation_tags=[{"source": "entity-1", "target": "entity-2", "type": "RELATES", "label": "rel", "doc": "doc-1"}],
            confidence=0.75,
        ),
        TimelineEvent(
            id="evt-0",
            ts=datetime(2024, 9, 1, tzinfo=timezone.utc),
            title="Earlier",
            summary="Earlier summary",
            citations=["doc-2"],
        ),
    ]
    store.append(events)
    results = store.read_all()
    assert [event.id for event in results] == ["evt-0", "evt-1"]
    enriched = next(event for event in results if event.id == "evt-1")
    assert enriched.entity_highlights[0]["id"] == "entity-1"
    assert enriched.relation_tags[0]["type"] == "RELATES"
    assert enriched.confidence == 0.75


def test_timeline_store_handles_empty_and_corrupt_lines(tmp_path: Path) -> None:
    store_path = tmp_path / "timeline.jsonl"
    store = TimelineStore(store_path)
    store.append([])
    store_path.write_text('{"invalid":\n')
    assert store.read_all() == []

    valid = {
        "id": "evt-2",
        "ts": datetime(2024, 11, 1, tzinfo=timezone.utc).isoformat(),
        "title": "Valid",
        "summary": "Works",
        "citations": ["doc-3"],
    }
    store_path.write_text(json.dumps(valid) + "\n")
    read_back = store.read_all()
    assert [event.id for event in read_back] == ["evt-2"]
    assert read_back[0].entity_highlights == []
    assert read_back[0].relation_tags == []
