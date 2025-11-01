from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from backend.app.services.graph import GraphEdge, GraphNode
from backend.app.services.timeline import TimelineService
from backend.app.storage.timeline_store import TimelineEvent, TimelineStore


class RecordingCounter:
    def __init__(self) -> None:
        self.calls: List[Tuple[float, Dict[str, object]]] = []

    def add(self, amount: float, attributes: Dict[str, object] | None = None) -> None:
        self.calls.append((amount, dict(attributes or {})))


class StubGraphService:
    def document_entities(self, doc_ids):
        return {
            doc_id: [
                GraphNode(id="entity::acme", type="Entity", properties={"label": "Acme Corporation"}),
                GraphNode(id="entity::policy", type="Entity", properties={"label": "Policy"}),
            ]
            for doc_id in doc_ids
        }

    def neighbors(self, entity_id: str):
        return (
            [],
            [
                GraphEdge(
                    source=entity_id,
                    target="entity::policy",
                    type="MENTIONS",
                    properties={"doc_id": "doc-1", "predicate": "MENTIONS"},
                )
            ],
        )


@pytest.fixture()
def timeline_store(tmp_path: Path) -> TimelineStore:
    store = TimelineStore(tmp_path / "timeline.jsonl")
    store.append(
        [
            TimelineEvent(
                id="doc-1::event::0",
                ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
                title="Policy adopted",
                summary="Acme policy adopted",
                citations=["doc-1"],
            )
        ]
    )
    return store


def test_timeline_service_enriches_metadata(monkeypatch: pytest.MonkeyPatch, timeline_store: TimelineStore) -> None:
    query_counter = RecordingCounter()
    filter_counter = RecordingCounter()
    enrichment_counter = RecordingCounter()

    monkeypatch.setattr("backend.app.services.timeline._timeline_query_counter", query_counter)
    monkeypatch.setattr("backend.app.services.timeline._timeline_filter_counter", filter_counter)
    monkeypatch.setattr("backend.app.services.timeline._timeline_enrichment_counter", enrichment_counter)

    service = TimelineService(store=timeline_store, graph_service=StubGraphService())
    result = service.list_events()

    assert result.events[0].entity_highlights
    assert result.events[0].relation_tags
    assert result.events[0].confidence is not None
    assert result.events[0].risk_score is not None
    assert result.events[0].outcome_probabilities
    assert result.events[0].recommended_actions

    persisted = timeline_store.read_all()
    assert persisted[0].entity_highlights
    assert persisted[0].relation_tags
    assert persisted[0].risk_score is not None
    assert persisted[0].outcome_probabilities

    assert query_counter.calls
    assert enrichment_counter.calls[0][0] >= 1
    assert filter_counter.calls == []
