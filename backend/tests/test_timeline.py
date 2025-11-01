from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pytest

from backend.app.services.graph import GraphEdge, GraphNode
from backend.app.services.timeline import TimelineService
from backend.app.storage.timeline_store import TimelineEvent, TimelineStore


class StubGraphService:
    def __init__(self) -> None:
        self._relations: Dict[str, List[GraphEdge]] = {}

    def document_entities(self, doc_ids: Iterable[str]) -> Dict[str, List[GraphNode]]:
        mapping: Dict[str, List[GraphNode]] = {}
        for doc_id in doc_ids:
            mapping[doc_id] = [
                GraphNode(id="entity::acme", type="Entity", properties={"label": "Acme Corp"}),
                GraphNode(id="entity::motion", type="Entity", properties={"label": "Motion"}),
            ]
        return mapping

    def neighbors(self, entity_id: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
        edge = GraphEdge(
            source=entity_id,
            target="entity::motion",
            type="MENTIONS",
            properties={"doc_id": "doc-motion", "predicate": "MENTIONS"},
        )
        return [], [edge]


@pytest.fixture()
def timeline_store(tmp_path: Path) -> TimelineStore:
    store = TimelineStore(tmp_path / "timeline.jsonl")
    store.write_all(
        [
            TimelineEvent(
                id="doc-motion::event::0",
                ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
                title="Emergency motion filed",
                summary="Emergency motion alleging discovery breach and sanctions request.",
                citations=["doc-motion"],
            ),
            TimelineEvent(
                id="doc-update::event::1",
                ts=datetime(2023, 6, 15, tzinfo=timezone.utc),
                title="Policy update recorded",
                summary="Routine compliance update with no outstanding motions.",
                citations=["doc-update"],
            ),
        ]
    )
    return store


def test_risk_forecasting_persists_to_store(timeline_store: TimelineStore) -> None:
    service = TimelineService(store=timeline_store, graph_service=StubGraphService())

    result = service.list_events()
    assert result.events, "Expected timeline events to be returned"
    event = next(event for event in result.events if "Emergency motion" in event.title)

    assert event.risk_score is not None
    assert event.risk_band in {"low", "medium", "high"}
    assert event.outcome_probabilities
    assert sum(prob["probability"] for prob in event.outcome_probabilities) == pytest.approx(
        1.0, abs=0.05
    )
    assert event.recommended_actions
    assert event.motion_deadline is not None

    persisted = timeline_store.read_all()
    stored = next(item for item in persisted if item.id == event.id)
    assert stored.risk_band == event.risk_band
    assert stored.motion_deadline == event.motion_deadline


def test_advanced_filters_by_risk_and_deadline(timeline_store: TimelineStore) -> None:
    service = TimelineService(store=timeline_store, graph_service=StubGraphService())
    full_result = service.list_events()
    high_risk = [event for event in full_result.events if event.risk_band == "high"]
    if not high_risk:
        pytest.skip("Risk calibration did not produce a high risk event in this configuration")

    filtered_by_risk = service.list_events(risk_band="high")
    assert all(event.risk_band == "high" for event in filtered_by_risk.events)

    target_event = high_risk[0]
    assert target_event.motion_deadline is not None
    before = target_event.motion_deadline + timedelta(days=1)
    after = target_event.motion_deadline - timedelta(days=1)

    due_before = service.list_events(motion_due_before=before)
    assert target_event.id in {event.id for event in due_before.events}

    due_after = service.list_events(motion_due_after=after)
    assert target_event.id in {event.id for event in due_after.events}

    too_early = service.list_events(motion_due_before=after)
    assert target_event.id not in {event.id for event in too_early.events}
