from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider as SDKMeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from qdrant_client.http import models as qmodels

from backend.app.config import get_settings, reset_settings_cache
from backend.app.services.forensics import ForensicsService
from backend.app.services.graph import GraphEdge, GraphNode, GraphSubgraph
from backend.app.services.retrieval import QueryResult, RetrievalService
from backend.app.telemetry import reset_telemetry, setup_telemetry


@dataclass
class RetrievalTelemetryRecorder:
    tracer: "RecordingTracer"
    queries: "RecordingCounter"
    duration: "RecordingHistogram"
    results: "RecordingHistogram"


@dataclass
class ForensicsTelemetryRecorder:
    tracer: "RecordingTracer"
    pipeline_counter: "RecordingCounter"
    pipeline_duration: "RecordingHistogram"
    stage_duration: "RecordingHistogram"
    fallback_counter: "RecordingCounter"


@dataclass
class TelemetryHarness:
    retrieval: RetrievalTelemetryRecorder
    forensics: ForensicsTelemetryRecorder


def _bootstrap_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> TelemetryHarness:
    monkeypatch.setenv("TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("TELEMETRY_CONSOLE_FALLBACK", "false")
    monkeypatch.setenv("VECTOR_DIR", str(tmp_path / "vector"))
    monkeypatch.setenv("FORENSICS_DIR", str(tmp_path / "forensics"))
    monkeypatch.setenv("DOCUMENT_STORE_DIR", str(tmp_path / "documents"))
    monkeypatch.setenv("JOB_STORE_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("INGESTION_WORKSPACE_DIR", str(tmp_path / "workspaces"))
    monkeypatch.setenv("TIMELINE_PATH", str(tmp_path / "timeline.jsonl"))
    monkeypatch.setenv("AGENT_THREADS_DIR", str(tmp_path / "threads"))
    reset_settings_cache()
    reset_telemetry()
    harness = TelemetryHarness(
        retrieval=RetrievalTelemetryRecorder(
            tracer=RecordingTracer(),
            queries=RecordingCounter(),
            duration=RecordingHistogram(),
            results=RecordingHistogram(),
        ),
        forensics=ForensicsTelemetryRecorder(
            tracer=RecordingTracer(),
            pipeline_counter=RecordingCounter(),
            pipeline_duration=RecordingHistogram(),
            stage_duration=RecordingHistogram(),
            fallback_counter=RecordingCounter(),
        ),
    )

    monkeypatch.setattr(
        "backend.app.services.retrieval._tracer",
        harness.retrieval.tracer,
    )
    monkeypatch.setattr(
        "backend.app.services.retrieval._retrieval_queries_counter",
        harness.retrieval.queries,
    )
    monkeypatch.setattr(
        "backend.app.services.retrieval._retrieval_query_duration",
        harness.retrieval.duration,
    )
    monkeypatch.setattr(
        "backend.app.services.retrieval._retrieval_results_histogram",
        harness.retrieval.results,
    )

    monkeypatch.setattr(
        "backend.app.services.forensics._tracer",
        harness.forensics.tracer,
    )
    monkeypatch.setattr(
        "backend.app.services.forensics._forensics_pipeline_counter",
        harness.forensics.pipeline_counter,
    )
    monkeypatch.setattr(
        "backend.app.services.forensics._forensics_pipeline_duration",
        harness.forensics.pipeline_duration,
    )
    monkeypatch.setattr(
        "backend.app.services.forensics._forensics_stage_duration",
        harness.forensics.stage_duration,
    )
    monkeypatch.setattr(
        "backend.app.services.forensics._forensics_fallback_counter",
        harness.forensics.fallback_counter,
    )

    monkeypatch.setattr(
        "backend.app.telemetry._create_span_exporter",
        lambda settings: None,
    )
    monkeypatch.setattr(
        "backend.app.telemetry._create_metric_reader",
        lambda settings: None,
    )

    settings = get_settings()
    setup_telemetry(settings)
    return harness


class DummyVectorService:
    def __init__(self, points: List[qmodels.ScoredPoint]) -> None:
        self._points = points

    def search(self, vector: List[float], top_k: int = 8) -> List[qmodels.ScoredPoint]:
        return self._points[:top_k]


class DummyGraphService:
    def neighbors(self, entity_id: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
        node = GraphNode(id=entity_id, type="Entity", properties={"label": entity_id})
        edge = GraphEdge(
            source=entity_id,
            target="doc-1",
            type="MENTIONS",
            properties={"doc_id": "doc-1"},
        )
        return [node], [edge]

    def search_entities(self, query: str, limit: int | None = None) -> List[GraphNode]:
        return []

    def subgraph(self, entity_ids: List[str]) -> GraphSubgraph:
        subgraph = GraphSubgraph()
        for entity_id in entity_ids:
            subgraph.nodes[entity_id] = GraphNode(id=entity_id, type="Entity", properties={"label": entity_id})
        return subgraph

    def communities_for_nodes(self, node_ids: List[str]) -> List[object]:
        return []


class DummyDocumentStore:
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, object]] = {}

    def read_document(self, doc_id: str) -> Dict[str, object]:
        return self._store.get(doc_id, {})

    def list_documents(self) -> List[Dict[str, object]]:
        return list(self._store.values())


class DummyForensicsService:
    def report_exists(self, doc_id: str, artifact: str) -> bool:
        return True

    def load_artifact(self, doc_id: str, artifact: str) -> Dict[str, object]:
        return {
            "schema_version": "telemetry-test",
            "summary": f"Report for {doc_id}",
            "fallback_applied": False,
        }


class RecordingCounter:
    def __init__(self) -> None:
        self.calls: List[Tuple[float, Dict[str, object]]] = []

    def add(self, amount: float, attributes: Dict[str, object] | None = None) -> None:
        self.calls.append((amount, dict(attributes or {})))


class RecordingHistogram:
    def __init__(self) -> None:
        self.records: List[Tuple[float, Dict[str, object]]] = []

    def record(self, value: float, attributes: Dict[str, object] | None = None) -> None:
        self.records.append((value, dict(attributes or {})))


class RecordingSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: Dict[str, object] = {}
        self.events: List[Tuple[str, Dict[str, object]]] = []
        self.exceptions: List[Exception] = []
        self.status: Tuple[str, str] | None = None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, exc: Exception) -> None:
        self.exceptions.append(exc)

    def set_status(self, status: object) -> None:
        code = getattr(status, "status_code", None)
        description = getattr(status, "description", "")
        self.status = (getattr(code, "name", str(code)), str(description))

    def add_event(self, name: str, attributes: Dict[str, object] | None = None) -> None:
        self.events.append((name, dict(attributes or {})))


class RecordingSpanContext:
    def __init__(self, tracer: "RecordingTracer", name: str) -> None:
        self.tracer = tracer
        self.span = RecordingSpan(name)

    def __enter__(self) -> RecordingSpan:
        self.tracer.spans.append(self.span)
        return self.span

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class RecordingTracer:
    def __init__(self) -> None:
        self.spans: List[RecordingSpan] = []

    def start_as_current_span(self, name: str) -> RecordingSpanContext:
        return RecordingSpanContext(self, name)


def test_setup_telemetry_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    call_count = 0

    def exporter_factory(settings) -> InMemorySpanExporter:
        nonlocal call_count
        call_count += 1
        return span_exporter

    monkeypatch.setenv("TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("TELEMETRY_CONSOLE_FALLBACK", "false")
    reset_settings_cache()
    reset_telemetry()
    monkeypatch.setattr("backend.app.telemetry._create_span_exporter", exporter_factory)
    monkeypatch.setattr(
        "backend.app.telemetry._create_metric_reader",
        lambda settings: metric_reader,
    )
    settings = get_settings()
    setup_telemetry(settings)
    setup_telemetry(settings)

    assert call_count == 1
    assert isinstance(trace.get_tracer_provider(), SDKTracerProvider)
    assert isinstance(metrics.get_meter_provider(), SDKMeterProvider)

    reset_telemetry()
    reset_settings_cache()


def test_retrieval_instrumentation_records_spans_and_metrics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    harness = _bootstrap_telemetry(monkeypatch, tmp_path)

    scored_point = qmodels.ScoredPoint(
        id="doc-1",
        score=0.9,
        payload={"doc_id": "doc-1", "type": "document", "text": "Example payload."},
        version=0,
        vector=[0.1, 0.2],
    )
    vector_service = DummyVectorService([scored_point])
    graph_service = DummyGraphService()
    document_store = DummyDocumentStore()
    forensics_service = DummyForensicsService()

    retrieval = RetrievalService(
        vector_service=vector_service,
        graph_service=graph_service,
        document_store=document_store,
        forensics_service=forensics_service,
    )

    result = retrieval.query("what is the payload", page=1, page_size=1)
    assert isinstance(result, QueryResult)
    assert result.has_evidence is True

    span_names = {span.name for span in harness.retrieval.tracer.spans}
    assert "retrieval.query" in span_names
    assert "retrieval.vector_search" in span_names

    query_span = next(span for span in harness.retrieval.tracer.spans if span.name == "retrieval.query")
    assert query_span.attributes["retrieval.page"] == 1
    assert query_span.attributes["retrieval.page_size"] == 1
    assert query_span.attributes["retrieval.has_evidence"] is True
    assert query_span.attributes["retrieval.privilege.label"] == "non_privileged"
    assert query_span.attributes["retrieval.privilege.flagged"] == 0

    vector_span = next(span for span in harness.retrieval.tracer.spans if span.name == "retrieval.vector_search")
    assert vector_span.attributes["retrieval.vector.count"] == 1

    assert len(harness.retrieval.queries.calls) == 1
    amount, attributes = harness.retrieval.queries.calls[0]
    assert amount == 1
    expected_attrs = {
        "rerank": False,
        "filter_source": "any",
        "filter_entity": False,
        "has_evidence": True,
        "privilege_label": "non_privileged",
        "privilege_flagged": False,
    }
    for key, value in expected_attrs.items():
        assert attributes[key] == value
    assert attributes["mode"] == "precision"
    assert attributes["reranker"] == "rrf"
    assert len(harness.retrieval.duration.records) == 1
    assert harness.retrieval.duration.records[0][1]["has_evidence"] is True
    assert len(harness.retrieval.results.records) == 1
    assert harness.retrieval.results.records[0][0] == 1

    reset_telemetry()
    reset_settings_cache()


def test_forensics_pipeline_emits_observability_signals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    harness = _bootstrap_telemetry(monkeypatch, tmp_path)

    source_dir = tmp_path / "workspace"
    source_dir.mkdir(parents=True, exist_ok=True)
    sample_file = source_dir / "doc.txt"
    sample_file.write_text("Telemetry validation document", encoding="utf-8")

    service = ForensicsService()
    report = service.build_document_artifact("doc-telemetry", sample_file)
    assert report.summary

    spans = harness.forensics.tracer.spans
    pipeline_spans = [span for span in spans if span.name == "forensics.pipeline"]
    assert pipeline_spans, "expected pipeline span to be emitted"
    pipeline_span = pipeline_spans[0]
    assert pipeline_span.attributes["forensics.pipeline.fallback_applied"] is False
    assert pipeline_span.attributes["forensics.pipeline.duration_ms"] > 0

    stage_spans = [span for span in spans if span.name.startswith("forensics.stage.")]
    assert len(stage_spans) >= 3
    assert all("forensics.stage.duration_ms" in span.attributes for span in stage_spans)

    assert harness.forensics.pipeline_counter.calls == [
        (
            1,
            {"artifact_type": "document"},
        )
    ]
    assert len(harness.forensics.pipeline_duration.records) == 1
    assert harness.forensics.pipeline_duration.records[0][1]["artifact_type"] == "document"
    assert len(harness.forensics.stage_duration.records) >= 3
    assert harness.forensics.fallback_counter.calls == []

    reset_telemetry()
    reset_settings_cache()
