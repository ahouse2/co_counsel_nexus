from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pytest
import httpx
from qdrant_client.http import models as qmodels

from backend.app import config
from backend.app.services import graph as graph_module
from backend.app.services import retrieval as retrieval_module
from backend.app.services.retrieval_engine import HybridRetrievalBundle
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


@pytest.fixture()
def cassette_loader() -> Callable[[str], dict]:
    base = Path(__file__).parent / "fixtures" / "cassettes"

    def _load(name: str) -> dict:
        path = base / f"{name}.json"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    return _load


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
    trace, relation_statements, doc_scope, privilege_decisions = retrieval_service._build_trace(
        [point], ["entity-graph"]
    )
    assert relation_statements
    graph_payload = trace.graph
    assert graph_payload["nodes"]
    assert graph_payload["edges"]
    assert graph_payload["events"]
    assert graph_payload["communities"]
    assert doc_scope
    assert privilege_decisions == {}


def test_build_citations_includes_page_context(
    retrieval_service: retrieval_module.RetrievalService,
) -> None:
    retrieval_service.document_store.write_document(
        "doc-1",
        {
            "id": "doc-1",
            "uri": "file://doc",
            "title": "Doc Title",
            "source_type": "local",
            "entity_labels": ["Acme Corporation"],
            "entity_ids": ["entity::acme"],
        },
    )
    point = qmodels.ScoredPoint(
        id="vec-1",
        score=0.8,
        payload={
            "doc_id": "doc-1",
            "text": "Example snippet",
            "chunk_index": 2,
            "retrievers": ["vector", "keyword"],
            "fusion_score": 0.42,
            "entity_labels": ["Acme Corporation"],
            "entity_ids": ["entity::acme"],
        },
        version=1,
    )
    citations = retrieval_service._build_citations([point])
    assert citations
    citation = citations[0]
    assert citation.page_label == "Page 3"
    assert citation.chunk_index == 2
    assert citation.page_number == 3
    assert citation.title == "Doc Title"
    assert citation.source_type == "local"
    assert citation.retrievers == ["keyword", "vector"]
    assert citation.fusion_score == pytest.approx(0.42)
    assert citation.confidence == pytest.approx(0.8)
    assert citation.entities and citation.entities[0]["label"] == "Acme Corporation"
    payload = citation.to_dict()
    assert payload["pageNumber"] == 3
    assert payload["retrievers"] == ["keyword", "vector"]


def test_merge_relation_statements_deduplicates(
    retrieval_service: retrieval_module.RetrievalService,
) -> None:
    primary = [("A relates B", "doc-1")]
    secondary = [("A relates B", "doc-1"), ("C relates D", None)]
    merged = retrieval_service._merge_relation_statements(primary, secondary)
    assert merged == [("A relates B", "doc-1"), ("C relates D", None)]


def test_courtlistener_adapter_uses_cassette(cassette_loader) -> None:
    payload = cassette_loader("courtlistener_search")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "courtlistener" in request.url.host
        return httpx.Response(200, json=payload)

    adapter = retrieval_module.CourtListenerCaseLawAdapter(
        endpoint="https://www.courtlistener.com/api/rest/v3/opinions/",
        token=None,
        client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    points = adapter.search("Miranda", limit=3)
    assert points
    first = points[0]
    assert first.payload["source_type"] == "courtlistener"
    assert "Miranda" in first.payload["case_name"]


def test_caselaw_adapter_uses_cassette(cassette_loader) -> None:
    payload = cassette_loader("caselaw_search")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "case.law" in request.url.host
        return httpx.Response(200, json=payload)

    adapter = retrieval_module.CaseLawApiAdapter(
        endpoint="https://api.case.law/v1/cases/",
        api_key=None,
        max_results=5,
        client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    points = adapter.search("Miranda", limit=2)
    assert points
    first = points[0]
    assert first.payload["source_type"] == "caselaw"
    assert "Miranda" in first.payload["case_name"]


def test_join_external_results_links_internal_case(
    retrieval_service: retrieval_module.RetrievalService,
) -> None:
    retrieval_service.document_store.write_document(
        "doc-internal",
        {
            "id": "doc-internal",
            "title": "Miranda v. Arizona",
            "source_type": "local",
            "citations": [{"cite": "384 U.S. 436"}],
        },
    )
    internal_point = qmodels.ScoredPoint(
        id="vec-internal",
        score=0.9,
        payload={"doc_id": "doc-internal", "text": "internal context", "source_type": "local"},
        version=1,
    )
    bundle = HybridRetrievalBundle(
        fused_points=[internal_point],
        vector_points=[internal_point],
        graph_points=[],
        keyword_points=[],
        relation_statements=[],
        reranker="rrf",
        fusion_scores={},
    )
    external_raw = qmodels.ScoredPoint(
        id="caselaw::67890",
        score=1.0,
        payload={
            "doc_id": "caselaw::67890",
            "text": "The conviction is reversed and the case is remanded for further proceedings.",
            "source_type": "caselaw",
            "case_name": "Miranda v. Arizona",
            "citations": [{"cite": "384 U.S. 436"}],
            "retrievers": ["external:caselaw"],
        },
        version=1,
    )
    inventory = retrieval_service.document_store.list_documents()
    reconciled = retrieval_service._reconcile_external_evidence([external_raw], inventory)
    retrieval_service._join_external_results(bundle, reconciled, limit=5)
    assert bundle.external_points
    external_payload = bundle.external_points[0].payload
    assert external_payload["linked_doc_id"] == "doc-internal"
    assert "external:caselaw" in external_payload["retrievers"]


def test_contradiction_detection_logs_warning(
    retrieval_service: retrieval_module.RetrievalService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    external_point = qmodels.ScoredPoint(
        id="courtlistener::1",
        score=1.0,
        payload={
            "doc_id": "courtlistener::1",
            "source_type": "courtlistener",
            "holding": "The motion was denied.",
            "text": "The motion was denied.",
        },
        version=1,
    )
    holdings = retrieval_service._authoritative_holdings([external_point])
    contradictions = retrieval_service._detect_contradictions("The motion was granted.", holdings)
    assert contradictions
    with caplog.at_level("WARNING"):
        retrieval_service._log_contradictions("Was the motion granted?", "The motion was granted.", contradictions)
    assert any("Contradiction detected" in record.message for record in caplog.records)

def test_stream_result_generates_events(
    retrieval_service: retrieval_module.RetrievalService,
) -> None:
    graph_service = retrieval_service.graph_service
    graph_service.upsert_document("doc-trace", "Trace Doc", {})
    graph_service.upsert_entity("entity-graph", "Entity", {"label": "Graph"})
    graph_service.merge_relation("doc-trace", "ASSOCIATED_WITH", "entity-graph", {"doc_id": "doc-trace"})

    timeline_event = TimelineEvent(
        id="event-graph",
        ts=datetime.now(timezone.utc),
        title="Graph Event",
        summary="Graph summary",
        citations=["doc-trace"],
        entity_highlights=[],
        relation_tags=[],
        confidence=0.9,
    )
    retrieval_service.timeline_store.write_all([timeline_event])

    point = qmodels.ScoredPoint(
        id="vec-graph",
        score=0.92,
        payload={"doc_id": "doc-trace", "text": "Context"},
        version=1,
    )
    trace, _, doc_scope, privilege_decisions = retrieval_service._build_trace([point], ["entity-graph"])
    trace.graph["events"] = retrieval_service._timeline_events_for_docs(doc_scope, privilege_decisions, None)
    meta = retrieval_module.QueryMeta(
        page=1,
        page_size=1,
        total_items=1,
        has_next=False,
        mode=retrieval_module.RetrievalMode.PRECISION,
        reranker="rrf",
    )
    result = retrieval_module.QueryResult(
        answer="Segmented answer",
        citations=[],
        trace=trace,
        meta=meta,
        has_evidence=True,
    )
    events = list(
        retrieval_service.stream_result(
            result,
            attributes={"mode": "precision", "reranker": "rrf", "stream": True},
            chunk_size=7,
        )
    )
    assert events[0].startswith("{\"type\": \"meta\"")
    assert any("\"type\": \"answer\"" in event for event in events)
    assert events[-1].startswith("{\"type\": \"final\"")
    final_payload = json.loads(events[-1])
    graph_payload = final_payload["traces"]["graph"]
    node_ids = {node["id"] for node in graph_payload["nodes"]}
    assert {"doc-trace", "entity-graph"}.issubset(node_ids)
    relation_types = {edge["type"] for edge in graph_payload["edges"]}
    assert "ASSOCIATED_WITH" in relation_types
    event_doc_ids = {citation for event in graph_payload["events"] for citation in event.get("citations", [])}
    assert "doc-trace" in event_doc_ids
