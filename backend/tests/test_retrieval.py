from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from qdrant_client.http import models as qmodels

from backend.app import config
from backend.app.services import graph as graph_module
from backend.app.services import retrieval as retrieval_module
from backend.app.storage.document_store import DocumentStore
from backend.app.storage.timeline_store import TimelineEvent, TimelineStore


class _DummyForensics:
    def report_exists(self, *_: object, **__: object) -> bool:
        return False

    def load_artifact(self, *_: object, **__: object) -> dict:
        raise FileNotFoundError


class _DummyAggregate:
    def to_dict(self) -> dict:
        return {"label": "allow", "score": 0.0}


class _DummyPrivilege:
    def classify(self, doc_id: str, text: str, metadata: dict) -> retrieval_module.PrivilegeDecision:
        return retrieval_module.PrivilegeDecision(
            doc_id=doc_id,
            label="allow",
            score=0.0,
            explanation=text,
            source="test",
        )

    def format_trace(self, decisions):
        return {"decisions": [], "aggregate": {}}

    def aggregate(self, decisions):
        return _DummyAggregate()


class _DummyVectorService:
    def search(self, *_: object, **__: object) -> list:
        return []


@pytest.fixture()
def retrieval_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage_root = tmp_path / "retrieval"
    storage_root.mkdir()
    monkeypatch.setenv("NEO4J_URI", "memory://")
    monkeypatch.setenv("TIMELINE_PATH", str(storage_root / "timeline.jsonl"))
    monkeypatch.setenv("DOCUMENT_STORE_DIR", str(storage_root / "docs"))
    monkeypatch.setenv("QDRANT_PATH", ":memory:")
    vector_dir = storage_root / "vector"
    vector_dir.mkdir()
    forensics_dir = storage_root / "forensics"
    forensics_dir.mkdir()
    docs_dir = storage_root / "docs"
    docs_dir.mkdir()
    monkeypatch.setenv("VECTOR_DIR", str(vector_dir))
    monkeypatch.setenv("FORENSICS_DIR", str(forensics_dir))
    key_path = storage_root / "manifest.key"
    key_path.write_bytes(b"0" * 32)
    monkeypatch.setenv("MANIFEST_ENCRYPTION_KEY_PATH", str(key_path))
    config.reset_settings_cache()
    graph_module.reset_graph_service()

    service = retrieval_module.RetrievalService.__new__(retrieval_module.RetrievalService)
    service.settings = config.get_settings()
    service.vector_service = _DummyVectorService()
    service.graph_service = graph_module.GraphService()
    service.document_store = DocumentStore(service.settings.document_store_dir)
    service.forensics_service = _DummyForensics()
    service.privilege_classifier = _DummyPrivilege()
    service.timeline_store = TimelineStore(service.settings.timeline_path)
    return service


def test_build_trace_includes_graph_payload(retrieval_service: retrieval_module.RetrievalService) -> None:
    graph_service = retrieval_service.graph_service
    graph_service.upsert_document("doc-trace", "Trace Doc", {})
    graph_service.upsert_entity("entity-graph", "Entity", {"label": "Graph"})
    graph_service.upsert_entity("entity-peer", "Entity", {"label": "Peer"})
    graph_service.merge_relation("doc-trace", "MENTIONS", "entity-graph", {"doc_id": "doc-trace"})
    graph_service.merge_relation("entity-graph", "ASSOCIATED_WITH", "entity-peer", {"doc_id": "doc-trace"})

    timeline_event = TimelineEvent(
        id="event-1",
        ts=datetime.now(timezone.utc),
        title="Event",
        summary="Summary",
        citations=["doc-trace"],
        entity_highlights=[],
        relation_tags=[],
        confidence=0.9,
    )
    retrieval_service.timeline_store.write_all([timeline_event])

    point = qmodels.ScoredPoint(
        id="vec-1",
        score=0.75,
        payload={"doc_id": "doc-trace", "text": "context"},
        version=1,
    )
    trace, relation_statements = retrieval_service._build_trace([point], ["entity-graph"])
    assert relation_statements
    graph_payload = trace.graph
    assert graph_payload["nodes"]
    assert graph_payload["edges"]
    assert graph_payload["events"]
    assert graph_payload["communities"]
