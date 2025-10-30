from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from itertools import zip_longest
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, Iterator, List, Set, Tuple
from urllib.parse import urljoin

try:  # pragma: no cover - optional dependency for vector retrieval
    from qdrant_client.http import models as qmodels
except ModuleNotFoundError:  # pragma: no cover - fallback for test environments
    class _StubScoredPoint(dict):
        """Minimal stand-in for qdrant_client.http.models.ScoredPoint."""

        id: str  # type: ignore[assignment]
        payload: dict
        score: float

    class _StubModels:  # pragma: no cover - type stub only
        ScoredPoint = _StubScoredPoint

    qmodels = _StubModels()  # type: ignore[assignment]

import httpx
from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..config import get_settings
from backend.ingestion.llama_index_factory import create_embedding_model, configure_global_settings
from backend.ingestion.settings import build_runtime_config
from ..storage.document_store import DocumentStore
from ..storage.timeline_store import TimelineStore
from ..utils.triples import extract_entities, normalise_entity_id
from .forensics import ForensicsService, get_forensics_service
from .graph import GraphEdge, GraphNode, GraphService, GraphSubgraph, get_graph_service
from .privilege import (
    PrivilegeClassifierService,
    PrivilegeDecision,
    get_privilege_classifier_service,
)
from .retrieval_engine import (
    GraphRetrieverAdapter,
    HybridQueryEngine,
    HybridRetrievalBundle,
    KeywordRetrieverAdapter,
    VectorRetrieverAdapter,
)
from .vector import VectorService, get_vector_service


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)
_logger = logging.getLogger(__name__)
_retrieval_queries_counter = _meter.create_counter(
    "retrieval_queries_total",
    unit="1",
    description="Total retrieval queries processed",
)
_retrieval_query_duration = _meter.create_histogram(
    "retrieval_query_duration_ms",
    unit="ms",
    description="Latency of retrieval queries",
)
_retrieval_results_histogram = _meter.create_histogram(
    "retrieval_results_returned",
    unit="1",
    description="Number of vector results evaluated per query",
)
_mode_queries_counter = _meter.create_counter(
    "retrieval_mode_queries_total",
    unit="1",
    description="Retrieval queries labelled by precision/recall mode",
)
_retrieval_stream_chunks_counter = _meter.create_counter(
    "retrieval_stream_chunks_total",
    unit="1",
    description="Total streamed answer chunks emitted",
)
_retrieval_partial_latency = _meter.create_histogram(
    "retrieval_partial_latency_ms",
    unit="ms",
    description="Latency from query execution to first streamed chunk",
)

_CONTRADICTION_TERMS: Tuple[Tuple[str, str], ...] = (
    ("granted", "denied"),
    ("denied", "granted"),
    ("affirmed", "reversed"),
    ("reversed", "affirmed"),
    ("affirmed", "vacated"),
    ("liable", "not liable"),
    ("allowed", "barred"),
)


class RetrievalMode(str, Enum):
    PRECISION = "precision"
    RECALL = "recall"


class CourtListenerCaseLawAdapter:
    """Lightweight CourtListener client that emits scored opinion payloads."""

    _MAX_PAGE_SIZE = 100
    _MAX_PAGES = 3

    def __init__(
        self,
        endpoint: str,
        token: str | None,
        *,
        timeout: float = 10.0,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/") + "/"
        self.token = token
        self.timeout = timeout
        self._client_factory = client_factory or (lambda: httpx.Client(timeout=self.timeout))

    def search(self, query: str, *, limit: int) -> List[qmodels.ScoredPoint]:
        if not query.strip() or limit <= 0:
            return []
        params = {"q": query, "page_size": min(max(limit, 1), self._MAX_PAGE_SIZE)}
        headers = self._headers()
        points: List[qmodels.ScoredPoint] = []
        next_url = self.endpoint
        page = 0
        try:
            with self._client_factory() as client:
                while next_url and len(points) < limit and page < self._MAX_PAGES:
                    response = client.get(
                        next_url,
                        params=params if page == 0 else None,
                        headers=headers,
                    )
                    if response.status_code >= 400:
                        _logger.warning(
                            "CourtListener request failed", extra={"url": next_url, "status": response.status_code}
                        )
                        break
                    payload = response.json()
                    results = payload.get("results") or []
                    for item in results:
                        point = self._point_from_result(item, query, len(points))
                        if point is None:
                            continue
                        points.append(point)
                        if len(points) >= limit:
                            break
                    next_url = payload.get("next")
                    page += 1
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            _logger.warning("CourtListener adapter error", exc_info=exc, extra={"query": query})
        return points

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "CoCounsel-Retrieval/1.0", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        return headers

    def _point_from_result(
        self, item: Dict[str, object], query: str, rank: int
    ) -> qmodels.ScoredPoint | None:
        identifier = item.get("id") or item.get("cluster") or item.get("absolute_url")
        if identifier is None:
            return None
        text = self._extract_text(item)
        if not text:
            return None
        case_name = str(item.get("case_name") or item.get("caption") or "").strip()
        docket = item.get("docket_number")
        doc_id = f"courtlistener::{identifier}"
        uri = item.get("absolute_url")
        payload = {
            "doc_id": doc_id,
            "text": text,
            "source_type": "courtlistener",
            "retriever": "external:courtlistener",
            "retrievers": ["external:courtlistener"],
            "case_name": case_name,
            "query": query,
            "docket_number": docket,
            "decision_date": item.get("date_filed"),
            "citations": item.get("citations"),
            "uri": urljoin("https://www.courtlistener.com", str(uri or "")) if uri else None,
            "title": case_name or str(uri or doc_id),
            "entity_labels": [case_name] if case_name else [],
            "entity_ids": [f"case::{identifier}"],
            "holding": self._holding_from_text(text),
        }
        score = 1.0 / float(rank + 1)
        return qmodels.ScoredPoint(id=doc_id, score=score, payload=payload, version=1)

    def _extract_text(self, item: Dict[str, object]) -> str:
        primary = item.get("plain_text") or item.get("html_with_citations")
        if isinstance(primary, str) and primary.strip():
            text = primary.strip()
        else:
            text = ""
        return text[:2000]

    @staticmethod
    def _holding_from_text(text: str) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        sentence_end = cleaned.find(".")
        return cleaned if sentence_end == -1 else cleaned[: sentence_end + 1]


class CaseLawApiAdapter:
    """Adapter for the Harvard CaseLaw API (api.case.law)."""

    _MAX_PAGE_SIZE = 100

    def __init__(
        self,
        endpoint: str,
        api_key: str | None,
        *,
        timeout: float = 10.0,
        client_factory: Callable[[], httpx.Client] | None = None,
        max_results: int = 10,
    ) -> None:
        self.endpoint = endpoint.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout = timeout
        self.max_results = max_results
        self._client_factory = client_factory or (lambda: httpx.Client(timeout=self.timeout))

    def search(self, query: str, *, limit: int) -> List[qmodels.ScoredPoint]:
        if not query.strip() or limit <= 0 or self.max_results == 0:
            return []
        limit = min(limit, self.max_results)
        params = {"search": query, "page_size": min(limit, self._MAX_PAGE_SIZE)}
        headers = {"User-Agent": "CoCounsel-Retrieval/1.0", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
        points: List[qmodels.ScoredPoint] = []
        next_url = self.endpoint
        try:
            with self._client_factory() as client:
                while next_url and len(points) < limit:
                    response = client.get(
                        next_url,
                        params=params if next_url == self.endpoint else None,
                        headers=headers,
                    )
                    if response.status_code >= 400:
                        _logger.warning(
                            "CaseLaw API request failed",
                            extra={"url": next_url, "status": response.status_code},
                        )
                        break
                    payload = response.json()
                    results = payload.get("results") or []
                    for item in results:
                        point = self._point_from_result(item, query, len(points))
                        if point is None:
                            continue
                        points.append(point)
                        if len(points) >= limit:
                            break
                    next_url = payload.get("next")
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            _logger.warning("CaseLaw adapter error", exc_info=exc, extra={"query": query})
        return points

    def _point_from_result(
        self, item: Dict[str, object], query: str, rank: int
    ) -> qmodels.ScoredPoint | None:
        identifier = item.get("id") or item.get("url")
        if identifier is None:
            return None
        text = self._extract_text(item)
        if not text:
            return None
        name = str(item.get("name") or item.get("case_name") or "").strip()
        docket = item.get("docket_number") or item.get("docket")
        doc_id = f"caselaw::{identifier}"
        payload = {
            "doc_id": doc_id,
            "text": text,
            "source_type": "caselaw",
            "retriever": "external:caselaw",
            "retrievers": ["external:caselaw"],
            "case_name": name,
            "query": query,
            "docket_number": docket,
            "decision_date": item.get("decision_date"),
            "citations": item.get("citations"),
            "uri": item.get("url") or item.get("frontend_url"),
            "title": name or str(identifier),
            "entity_labels": [name] if name else [],
            "entity_ids": [f"case::{identifier}"],
            "holding": self._holding_from_text(text),
        }
        score = 1.0 / float(rank + 1)
        return qmodels.ScoredPoint(id=doc_id, score=score, payload=payload, version=1)

    def _extract_text(self, item: Dict[str, object]) -> str:
        casebody = item.get("casebody") or {}
        data = casebody.get("data") if isinstance(casebody, dict) else {}
        opinions = data.get("opinions") if isinstance(data, dict) else []
        if isinstance(opinions, list) and opinions:
            first = opinions[0] or {}
            text = first.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()[:2000]
        body = casebody.get("casebody") if isinstance(casebody, dict) else None
        if isinstance(body, str) and body.strip():
            return body.strip()[:2000]
        return ""

    @staticmethod
    def _holding_from_text(text: str) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        sentence_end = cleaned.find(".")
        return cleaned if sentence_end == -1 else cleaned[: sentence_end + 1]


@dataclass
class Citation:
    doc_id: str
    span: str
    uri: str | None
    page_label: str | None
    chunk_index: int | None
    page_number: int | None = None
    title: str | None = None
    source_type: str | None = None
    retrievers: List[str] = field(default_factory=list)
    fusion_score: float | None = None
    confidence: float | None = None
    entities: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {"docId": self.doc_id, "span": self.span}
        if self.uri:
            payload["uri"] = self.uri
        if self.page_label:
            payload["pageLabel"] = self.page_label
        if self.chunk_index is not None:
            payload["chunkIndex"] = self.chunk_index
        if self.page_number is not None:
            payload["pageNumber"] = self.page_number
        if self.title:
            payload["title"] = self.title
        if self.source_type:
            payload["sourceType"] = self.source_type
        if self.retrievers:
            payload["retrievers"] = self.retrievers
        if self.fusion_score is not None:
            payload["fusionScore"] = self.fusion_score
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.entities:
            payload["entities"] = self.entities
        return payload


@dataclass
class Trace:
    vector: List[Dict[str, object]]
    graph: Dict[str, List[Dict[str, object]]]
    forensics: List[Dict[str, object]]
    privilege: Dict[str, object] | None = None

    def to_dict(self) -> Dict[str, object]:
        payload = {
            "vector": self.vector,
            "graph": self.graph,
            "forensics": self.forensics,
        }
        if self.privilege is not None:
            payload["privilege"] = self.privilege
        return payload


@dataclass
class QueryMeta:
    page: int
    page_size: int
    total_items: int
    has_next: bool
    mode: RetrievalMode
    reranker: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "has_next": self.has_next,
            "mode": self.mode.value,
            "reranker": self.reranker,
        }


@dataclass
class QueryResult:
    answer: str
    citations: List[Citation]
    trace: Trace
    meta: QueryMeta
    has_evidence: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "traces": self.trace.to_dict(),
            "meta": self.meta.to_dict(),
        }


class RetrievalService:
    def __init__(
        self,
        vector_service: VectorService | None = None,
        graph_service: GraphService | None = None,
        document_store: DocumentStore | None = None,
        forensics_service: ForensicsService | None = None,
        privilege_classifier: PrivilegeClassifierService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.graph_service = graph_service or get_graph_service()
        self.document_store = document_store or DocumentStore(self.settings.document_store_dir)
        self.forensics_service = forensics_service or get_forensics_service()
        self.privilege_classifier = privilege_classifier or get_privilege_classifier_service()
        self.runtime_config = build_runtime_config(self.settings)
        configure_global_settings(self.runtime_config)
        self.embedding_model = create_embedding_model(self.runtime_config.embedding)
        self.timeline_store = TimelineStore(self.settings.timeline_path)
        cross_encoder_model = getattr(self.settings, "retrieval_cross_encoder_model", None)
        self.query_engine = HybridQueryEngine(
            VectorRetrieverAdapter(self.vector_service, self.embedding_model),
            GraphRetrieverAdapter(self.graph_service),
            KeywordRetrieverAdapter(self.document_store),
            cross_encoder_model=cross_encoder_model,
        )
        self.courtlistener_adapter = CourtListenerCaseLawAdapter(
            self.settings.courtlistener_endpoint,
            self.settings.courtlistener_token,
        )
        self.caselaw_adapter = CaseLawApiAdapter(
            self.settings.caselaw_endpoint,
            self.settings.caselaw_api_key,
            max_results=self.settings.caselaw_max_results,
        )

    def query(
        self,
        question: str,
        *,
        page: int = 1,
        page_size: int = 10,
        filters: Dict[str, str] | None = None,
        rerank: bool = False,
        mode: RetrievalMode = RetrievalMode.PRECISION,
    ) -> QueryResult:
        if not isinstance(mode, RetrievalMode):
            mode = RetrievalMode(mode)
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if page_size < 1 or page_size > 50:
            raise ValueError("page_size must be between 1 and 50")
        start_time = perf_counter()
        filters = filters or {}
        allowed_sources = {
            "local",
            "s3",
            "sharepoint",
            "onedrive",
            "courtlistener",
            "caselaw",
            "websearch",
        }

        with _tracer.start_as_current_span("retrieval.query") as span:
            span.set_attribute("retrieval.page", page)
            span.set_attribute("retrieval.page_size", page_size)
            span.set_attribute("retrieval.rerank", rerank)
            span.set_attribute("retrieval.mode", mode.value)

            source_filter = filters.get("source")
            entity_filter = filters.get("entity")
            if source_filter:
                source_filter = source_filter.strip().lower()
                if source_filter not in allowed_sources:
                    message = f"Unsupported source filter '{source_filter}'"
                    span.record_exception(ValueError(message))
                    span.set_status(Status(StatusCode.ERROR, message))
                    raise ValueError(message)
            else:
                source_filter = None
            if entity_filter:
                entity_filter = entity_filter.strip()
            else:
                entity_filter = None

            span.set_attribute("retrieval.filters.source", source_filter or "")
            span.set_attribute("retrieval.filters.entity", entity_filter or "")
            span.set_attribute("retrieval.filters.applied", bool(source_filter or entity_filter))

            max_window = self.settings.retrieval_max_search_window
            span.set_attribute("retrieval.search_window.max", max_window)
            if page_size > max_window:
                message = "page_size exceeds configured retrieval window"
                span.record_exception(ValueError(message))
                span.set_status(Status(StatusCode.ERROR, message))
                raise ValueError(message)

            base_window = max(page * page_size * 2, page_size * 4)
            if mode is RetrievalMode.RECALL:
                base_window = max(page * page_size * 3, page_size * 6)
            search_window = min(max_window, base_window)
            span.set_attribute("retrieval.search_window", search_window)

            vector_window = min(search_window, max(page_size * 3, page_size))
            graph_window = min(self.settings.retrieval_graph_hop_window, 6)
            keyword_window = 5
            if mode is RetrievalMode.RECALL:
                vector_window = min(search_window, max(page_size * 4, page_size * 2))
                graph_window = min(self.settings.retrieval_graph_hop_window * 2, 12)
                keyword_window = 10

            external_points: List[qmodels.ScoredPoint] = []
            with _tracer.start_as_current_span("retrieval.hybrid") as hybrid_span:
                bundle: HybridRetrievalBundle = self.query_engine.retrieve(
                    question,
                    top_k=search_window,
                    vector_window=vector_window,
                    graph_window=graph_window,
                    keyword_window=keyword_window,
                    use_cross_encoder=bool(rerank and mode is RetrievalMode.PRECISION),
                )
                hybrid_span.set_attribute("retrieval.vector_candidates", len(bundle.vector_points))
                hybrid_span.set_attribute("retrieval.graph_candidates", len(bundle.graph_points))
                hybrid_span.set_attribute("retrieval.keyword_candidates", len(bundle.keyword_points))
                hybrid_span.set_attribute("retrieval.fused_candidates", len(bundle.fused_points))
                hybrid_span.set_attribute("retrieval.reranker", bundle.reranker)

            with _tracer.start_as_current_span("retrieval.external_case_law") as external_span:
                external_points = self._retrieve_external_case_law(
                    question,
                    top_k=search_window,
                    source_filter=source_filter,
                )
                external_span.set_attribute("retrieval.external.count", len(external_points))
                if external_points:
                    bundle = self._join_external_results(bundle, external_points, search_window)
                    external_points = bundle.external_points
            external_points = getattr(bundle, "external_points", external_points)

            with _tracer.start_as_current_span("retrieval.vector_search") as vector_span:
                vector_span.set_attribute("retrieval.vector.count", len(bundle.vector_points))
                vector_span.set_attribute("retrieval.vector.window", vector_window)

            filtered_results = self._apply_filters(bundle.fused_points, source_filter, entity_filter)
            span.set_attribute("retrieval.filtered_results", len(filtered_results))

            metric_attrs: Dict[str, object] = {
                "rerank": rerank,
                "filter_source": source_filter or "any",
                "filter_entity": bool(entity_filter),
                "mode": mode.value,
                "reranker": bundle.reranker,
            }
            metric_attrs["external_results"] = len(external_points)

            total_items = len(filtered_results)
            if total_items == 0:
                has_evidence = False
                metric_attrs["has_evidence"] = has_evidence
                duration_ms = (perf_counter() - start_time) * 1000.0
                span.set_attribute("retrieval.total_items", total_items)
                span.set_attribute("retrieval.has_evidence", has_evidence)
                span.set_attribute("retrieval.duration_ms", duration_ms)
                _retrieval_queries_counter.add(1, attributes=metric_attrs)
                _mode_queries_counter.add(1, attributes=metric_attrs)
                _retrieval_query_duration.record(duration_ms, attributes=metric_attrs)
                _retrieval_results_histogram.record(total_items, attributes=metric_attrs)
                empty_trace = Trace(vector=[], graph={"nodes": [], "edges": []}, forensics=[])
                meta = QueryMeta(
                    page=page,
                    page_size=page_size,
                    total_items=0,
                    has_next=False,
                    mode=mode,
                    reranker=bundle.reranker,
                )
                answer = "No supporting evidence found for the supplied query."
                return QueryResult(
                    answer=answer,
                    citations=[],
                    trace=empty_trace,
                    meta=meta,
                    has_evidence=False,
                )

            start = (page - 1) * page_size
            end = min(start + page_size, total_items)
            has_next = end < total_items

            vector_seed = self._apply_filters(bundle.vector_points, source_filter, entity_filter)
            vector_entities = self._collect_entities(vector_seed[:graph_window])
            entity_ids = self._augment_entity_ids(question, vector_entities)
            with _tracer.start_as_current_span("retrieval.trace_build") as trace_span:
                trace_span.set_attribute("retrieval.trace.entity_ids", len(entity_ids))
                trace_full, trace_relations = self._build_trace(filtered_results, entity_ids)
                trace_span.set_attribute("retrieval.trace.nodes", len(trace_full.graph.get("nodes", [])))
                trace_span.set_attribute("retrieval.trace.edges", len(trace_full.graph.get("edges", [])))
            relation_statements = self._merge_relation_statements(trace_relations, bundle.relation_statements)
            citations_full = self._build_citations(filtered_results)

            page_results = filtered_results[start:end]
            citations_page = citations_full[start:end] if end > start else []
            doc_ids_page: Set[str] = set()
            for point in page_results:
                payload = point.payload or {}
                doc_id = payload.get("doc_id")
                if doc_id is not None:
                    doc_ids_page.add(str(doc_id))

            vector_trace_page = trace_full.vector[start:end] if end > start else []
            forensics_trace_page = [
                entry for entry in trace_full.forensics if entry.get("document_id") in doc_ids_page
            ]
            if doc_ids_page:
                graph_edges_page = [
                    edge
                    for edge in trace_full.graph.get("edges", [])
                    if (
                        edge.get("properties", {}).get("doc_id") in doc_ids_page
                        or edge.get("source") in doc_ids_page
                        or edge.get("target") in doc_ids_page
                    )
                ]
                graph_node_ids = {
                    edge.get("source") for edge in graph_edges_page
                } | {
                    edge.get("target") for edge in graph_edges_page
                }
                graph_nodes_page = [
                    node
                    for node in trace_full.graph.get("nodes", [])
                    if node.get("id") in graph_node_ids
                ]
            else:
                graph_edges_page = []
                graph_nodes_page = []

            relation_statements_page = [
                statement
                for statement, doc_id in relation_statements
                if doc_id is None or doc_id in doc_ids_page
            ]

            privilege_full = trace_full.privilege or {
                "decisions": [],
                "aggregate": {"label": "unknown", "score": 0.0, "flagged": []},
            }
            privilege_page = self._page_privilege_trace(privilege_full, doc_ids_page)

            trace_page = Trace(
                vector=vector_trace_page,
                graph={"nodes": graph_nodes_page, "edges": graph_edges_page},
                forensics=forensics_trace_page,
                privilege=privilege_page,
            )
            privilege_label = privilege_page.get("aggregate", {}).get("label", "unknown")
            privilege_flagged = privilege_page.get("aggregate", {}).get("flagged", [])
            span.set_attribute("retrieval.privilege.label", privilege_label)
            span.set_attribute("retrieval.privilege.flagged", len(privilege_flagged))
            metric_attrs["privilege_label"] = privilege_label
            metric_attrs["privilege_flagged"] = bool(privilege_flagged)

            answer = self._compose_answer(question, page_results, relation_statements_page)
            if start >= total_items:
                answer = (
                    f"{answer} No additional supporting evidence available for page {page}; "
                    "adjust pagination or filters to view existing evidence."
                )

            authoritative_holdings = self._authoritative_holdings(external_points)
            contradictions = self._detect_contradictions(answer, authoritative_holdings)
            if contradictions:
                span.add_event(
                    "retrieval.contradiction",
                    {
                        "count": len(contradictions),
                        "first_holding": contradictions[0],
                    },
                )
                metric_attrs["contradictions"] = len(contradictions)
                self._log_contradictions(question, answer, contradictions)

            meta = QueryMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                has_next=has_next,
                mode=mode,
                reranker=bundle.reranker,
            )

            has_evidence = True
            metric_attrs["has_evidence"] = has_evidence
            duration_ms = (perf_counter() - start_time) * 1000.0
            span.set_attribute("retrieval.total_items", total_items)
            span.set_attribute("retrieval.has_evidence", has_evidence)
            span.set_attribute("retrieval.duration_ms", duration_ms)
            _retrieval_queries_counter.add(1, attributes=metric_attrs)
            _mode_queries_counter.add(1, attributes=metric_attrs)
            _retrieval_query_duration.record(duration_ms, attributes=metric_attrs)
            _retrieval_results_histogram.record(total_items, attributes=metric_attrs)

            return QueryResult(
                answer=answer,
                citations=citations_page,
                trace=trace_page,
                meta=meta,
                has_evidence=True,
            )

    def _build_citations(self, results: List[qmodels.ScoredPoint]) -> List[Citation]:
        citations: List[Citation] = []
        doc_cache: Dict[str, Dict[str, object]] = {}
        for point in results:
            payload = point.payload or {}
            raw_doc_id = payload.get("doc_id")
            if raw_doc_id is None:
                continue
            doc_id = str(raw_doc_id)
            doc_record = self._document_record(doc_id, doc_cache)
            uri = self._citation_uri(payload, doc_record)
            text = str(payload.get("text", ""))
            span = self._citation_snippet(text)
            chunk_index = self._safe_int(payload.get("chunk_index"))
            page_label = self._page_label(payload, chunk_index)
            page_number = self._page_number(payload, page_label, chunk_index)
            title = self._citation_title(payload, doc_record)
            source_type = self._citation_source(payload, doc_record)
            retrievers = self._citation_retrievers(payload)
            fusion_score = self._safe_float(payload.get("fusion_score"))
            confidence = self._safe_float(point.score)
            entities = self._citation_entities(payload, doc_record)
            citations.append(
                Citation(
                    doc_id=doc_id,
                    span=span,
                    uri=uri,
                    page_label=page_label,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    title=title,
                    source_type=source_type,
                    retrievers=retrievers,
                    fusion_score=fusion_score,
                    confidence=confidence,
                    entities=entities,
                )
            )
        return citations

    def _compose_answer(
        self, question: str, results: List[qmodels.ScoredPoint], relation_statements: List[str]
    ) -> str:
        if not results:
            if relation_statements:
                return self._format_graph_answer(relation_statements)
            return "No supporting evidence found for the supplied query."
        top = results[0]
        payload = top.payload or {}
        text = payload.get("text", "")
        if not text and relation_statements:
            return self._format_graph_answer(relation_statements)
        if not text:
            return "Unable to locate textual evidence despite stored vector payloads."
        snippet = text[:400]
        if relation_statements:
            graph_summary = "; ".join(relation_statements[:3])
            return (
                f"Based on retrieved context, the most relevant information is: {snippet}. "
                f"Graph analysis highlights: {graph_summary}."
            )
        return f"Based on retrieved context, the most relevant information is: {snippet}"

    def _format_graph_answer(self, relation_statements: List[str]) -> str:
        summary = "; ".join(relation_statements[:3])
        return f"Graph evidence indicates: {summary}."

    def _retrieve_external_case_law(
        self,
        question: str,
        *,
        top_k: int,
        source_filter: str | None,
    ) -> List[qmodels.ScoredPoint]:
        adapters: List[tuple[str, object]] = []
        if source_filter in (None, "courtlistener"):
            adapters.append(("courtlistener", self.courtlistener_adapter))
        if source_filter in (None, "caselaw"):
            adapters.append(("caselaw", self.caselaw_adapter))
        if not adapters:
            return []
        inventory = self.document_store.list_documents()
        aggregated: List[qmodels.ScoredPoint] = []
        for label, adapter in adapters:
            try:
                points = adapter.search(question, limit=top_k)
            except Exception as exc:  # pragma: no cover - defensive path
                _logger.warning(
                    "External case law adapter failed",
                    exc_info=exc,
                    extra={"adapter": label, "question": question},
                )
                continue
            reconciled = self._reconcile_external_evidence(points, inventory)
            aggregated.extend(reconciled)
        aggregated.sort(key=lambda point: float(point.score or 0.0), reverse=True)
        return aggregated[:top_k]

    def _reconcile_external_evidence(
        self,
        points: Iterable[qmodels.ScoredPoint],
        inventory: List[Dict[str, object]],
    ) -> List[qmodels.ScoredPoint]:
        reconciled: List[qmodels.ScoredPoint] = []
        for point in points:
            payload = dict(point.payload or {})
            payload.setdefault("fusion_score", float(point.score))
            payload.setdefault("confidence", float(point.score))
            payload["external_case_law"] = True
            linked = self._link_internal_case_law(payload, inventory)
            if linked:
                payload["linked_doc_id"] = linked.get("id")
                payload["linked_doc_title"] = linked.get("title") or linked.get("name")
                payload["linked_doc_source_type"] = linked.get("source_type")
                payload["linked_doc_summary"] = linked.get("summary")
                payload["linked_doc_citations"] = linked.get("citations")
            payload["retrievers"] = self._citation_retrievers(payload)
            reconciled.append(
                qmodels.ScoredPoint(
                    id=point.id,
                    score=float(point.score),
                    payload=payload,
                    version=point.version,
                )
            )
        return reconciled

    def _link_internal_case_law(
        self,
        payload: Dict[str, object],
        inventory: List[Dict[str, object]],
    ) -> Dict[str, object] | None:
        case_name = str(payload.get("case_name") or payload.get("title") or "").strip().lower()
        docket = str(payload.get("docket_number") or "").strip().lower()
        citations = self._normalise_citation_list(payload.get("citations"))
        for record in inventory:
            record_name = str(record.get("title") or record.get("name") or "").strip().lower()
            record_docket = str(record.get("docket_number") or record.get("docket") or "").strip().lower()
            record_citations = self._normalise_citation_list(record.get("citations"))
            if case_name and record_name and case_name == record_name:
                return record
            if docket and record_docket and docket == record_docket:
                return record
            if citations and record_citations and citations & record_citations:
                return record
        return None

    def _normalise_citation_list(self, value: object) -> Set[str]:
        citations: Set[str] = set()
        if value is None:
            return citations
        if isinstance(value, (list, tuple, set)):
            iterable = value
        else:
            iterable = [value]
        for item in iterable:
            normalised = self._normalise_citation(item)
            if normalised:
                citations.add(normalised)
        return citations

    def _normalise_citation(self, citation: object) -> str:
        if isinstance(citation, dict):
            candidate = citation.get("cite") or citation.get("citation") or citation.get("value") or ""
        else:
            candidate = citation or ""
        text = str(candidate)
        cleaned = re.sub(r"\s+", " ", text).strip().lower()
        return cleaned

    def _join_external_results(
        self,
        bundle: HybridRetrievalBundle,
        external_points: List[qmodels.ScoredPoint],
        limit: int,
    ) -> HybridRetrievalBundle:
        keyed: Dict[str, qmodels.ScoredPoint] = {
            self._point_key(point): point for point in bundle.fused_points
        }
        normalised_external = [self._standardise_external_point(point) for point in external_points]
        for point in normalised_external:
            key = self._point_key(point)
            existing = keyed.get(key)
            if existing is None:
                keyed[key] = point
            else:
                keyed[key] = self._merge_points(existing, point)
        fused = list(keyed.values())
        fused.sort(key=lambda item: float(item.score or 0.0), reverse=True)
        bundle.fused_points = fused[:limit]
        bundle.external_points = normalised_external
        for point in bundle.fused_points:
            key = self._point_key(point)
            bundle.fusion_scores.setdefault(key, float(point.score))
        return bundle

    def _standardise_external_point(self, point: qmodels.ScoredPoint) -> qmodels.ScoredPoint:
        payload = dict(point.payload or {})
        payload.setdefault("fusion_score", float(point.score))
        payload.setdefault("confidence", float(point.score))
        payload.setdefault("retrievers", self._citation_retrievers(payload))
        payload.setdefault("external_case_law", True)
        return qmodels.ScoredPoint(
            id=point.id,
            score=float(payload.get("fusion_score", point.score)),
            payload=payload,
            version=point.version,
        )

    def _merge_points(
        self,
        primary: qmodels.ScoredPoint,
        external: qmodels.ScoredPoint,
    ) -> qmodels.ScoredPoint:
        payload = dict(primary.payload or {})
        other = external.payload or {}
        existing_retrievers = set(self._citation_retrievers(payload))
        external_retrievers = set(self._citation_retrievers(other))
        payload["retrievers"] = sorted(existing_retrievers | external_retrievers)
        payload.setdefault("fusion_score", float(primary.score))
        payload["fusion_score"] = max(float(payload.get("fusion_score", primary.score)), float(other.get("fusion_score", external.score)))
        payload["confidence"] = max(float(payload.get("confidence", primary.score)), float(other.get("confidence", external.score)))
        for key in (
            "uri",
            "title",
            "source_type",
            "case_name",
            "docket_number",
            "decision_date",
            "holding",
            "linked_doc_id",
            "linked_doc_title",
            "linked_doc_source_type",
            "linked_doc_summary",
            "linked_doc_citations",
            "citations",
        ):
            value = other.get(key)
            if value and not payload.get(key):
                payload[key] = value
        text_existing = str(payload.get("text", ""))
        text_external = str(other.get("text", ""))
        if len(text_external) > len(text_existing):
            payload["text"] = text_external
        payload["external_case_law"] = payload.get("external_case_law", False) or other.get("external_case_law", False)
        return qmodels.ScoredPoint(
            id=primary.id,
            score=float(payload.get("fusion_score", primary.score)),
            payload=payload,
            version=primary.version,
        )

    @staticmethod
    def _point_key(point: qmodels.ScoredPoint) -> str:
        payload = point.payload or {}
        doc_id = payload.get("doc_id") or payload.get("id")
        chunk_index = payload.get("chunk_index")
        return f"{doc_id or point.id}::{chunk_index if chunk_index is not None else 'na'}::{point.id}"

    def _augment_privilege_metadata(
        self, payload: Dict[str, object], doc_id: str
    ) -> Dict[str, object]:
        metadata = {key: value for key, value in payload.items() if key != "text"}
        source_type = str(metadata.get("source_type") or "").lower()
        if source_type in {"courtlistener", "caselaw"}:
            linked_id = metadata.get("linked_doc_id")
            linked_record: Dict[str, object] | None = None
            if linked_id:
                try:
                    linked_record = self.document_store.read_document(str(linked_id))
                except FileNotFoundError:
                    linked_record = None
            if linked_record:
                metadata.setdefault("linked_doc_title", linked_record.get("title") or linked_record.get("name"))
                metadata.setdefault("linked_doc_source_type", linked_record.get("source_type"))
                metadata.setdefault("linked_doc_summary", linked_record.get("summary"))
            metadata.setdefault("external_case_law", True)
            metadata.setdefault("linked_doc_hint", linked_id)
        metadata.setdefault("doc_id", doc_id)
        return metadata

    def _authoritative_holdings(
        self, points: Iterable[qmodels.ScoredPoint]
    ) -> List[str]:
        holdings: List[str] = []
        for point in points:
            payload = point.payload or {}
            holding = payload.get("holding") or payload.get("text")
            if not isinstance(holding, str):
                continue
            excerpt = " ".join(holding.split())
            if excerpt:
                holdings.append(excerpt[:400])
        return holdings

    def _detect_contradictions(self, answer: str, holdings: List[str]) -> List[str]:
        contradictions: List[str] = []
        if not answer or not holdings:
            return contradictions
        answer_lower = answer.lower()
        for holding in holdings:
            holding_lower = holding.lower()
            for positive, negative in _CONTRADICTION_TERMS:
                if positive in answer_lower and negative in holding_lower:
                    contradictions.append(holding)
                    break
                if negative in answer_lower and positive in holding_lower:
                    contradictions.append(holding)
                    break
        return contradictions

    def _log_contradictions(
        self,
        question: str,
        answer: str,
        contradictions: List[str],
    ) -> None:
        if not contradictions:
            return
        _logger.warning(
            "Contradiction detected between generated answer and authoritative holdings",
            extra={
                "question": question,
                "answer_excerpt": answer[:200],
                "contradictions": contradictions,
            },
        )

    def _citation_snippet(self, text: str) -> str:
        clean = " ".join(text.split())
        if len(clean) <= 220:
            return clean
        snippet = clean[:220]
        last_space = snippet.rfind(" ")
        if last_space > 120:
            snippet = snippet[:last_space]
        return snippet.rstrip() + "…"

    def _page_label(self, payload: Dict[str, object], chunk_index: int | None) -> str | None:
        explicit = payload.get("page_label") or payload.get("page_number") or payload.get("page")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
        if isinstance(explicit, (int, float)):
            return f"Page {int(explicit)}"
        if chunk_index is not None and chunk_index >= 0:
            return f"Page {chunk_index + 1}"
        return None

    def _safe_int(self, value: object) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_float(self, value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _document_record(
        self, doc_id: str, cache: Dict[str, Dict[str, object]]
    ) -> Dict[str, object]:
        if doc_id not in cache:
            try:
                cache[doc_id] = self.document_store.read_document(doc_id)
            except FileNotFoundError:
                cache[doc_id] = {}
        return cache[doc_id]

    def _citation_uri(
        self, payload: Dict[str, object], doc_record: Dict[str, object] | None
    ) -> str | None:
        uri = payload.get("uri")
        if isinstance(uri, str) and uri.strip():
            return uri.strip()
        if not doc_record:
            return None
        record_uri = doc_record.get("uri")
        if isinstance(record_uri, str) and record_uri.strip():
            return record_uri.strip()
        return None

    def _citation_title(
        self, payload: Dict[str, object], doc_record: Dict[str, object] | None
    ) -> str | None:
        candidates = [
            payload.get("title"),
            payload.get("document_title"),
            doc_record.get("title") if doc_record else None,
            doc_record.get("name") if doc_record else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None

    def _citation_source(
        self, payload: Dict[str, object], doc_record: Dict[str, object] | None
    ) -> str | None:
        candidates = [
            payload.get("source_type"),
            doc_record.get("source_type") if doc_record else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip().lower()
        return None

    def _citation_retrievers(self, payload: Dict[str, object]) -> List[str]:
        retrievers_raw = payload.get("retrievers")
        retrievers: List[str] = []
        if isinstance(retrievers_raw, (list, tuple, set)):
            retrievers.extend(str(item).strip() for item in retrievers_raw if str(item).strip())
        single = payload.get("retriever")
        if single:
            retrievers.append(str(single).strip())
        ordered = sorted({item for item in retrievers if item})
        return ordered

    def _citation_entities(
        self,
        payload: Dict[str, object],
        doc_record: Dict[str, object] | None,
    ) -> List[Dict[str, str]]:
        labels = self._normalise_str_list(payload.get("entity_labels"))
        ids = self._normalise_str_list(payload.get("entity_ids"))
        types = self._normalise_str_list(payload.get("entity_types"))
        if doc_record:
            labels.extend(self._normalise_str_list(doc_record.get("entity_labels")))
            ids.extend(self._normalise_str_list(doc_record.get("entity_ids")))
            types.extend(self._normalise_str_list(doc_record.get("entity_types")))
        highlights: List[Dict[str, str]] = []
        seen: Set[Tuple[str, str, str]] = set()
        for label, entity_id, entity_type in zip_longest(labels, ids, types, fillvalue=None):
            label_value = (label or "").strip()
            entity_id_value = (entity_id or "").strip()
            entity_type_value = (entity_type or "").strip()
            if not label_value and not entity_id_value:
                continue
            if not entity_id_value:
                entity_id_value = label_value or "entity::unknown"
            if not entity_type_value:
                entity_type_value = "entity"
            key = (
                entity_id_value.lower(),
                label_value.lower() or entity_id_value.lower(),
                entity_type_value.lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            highlights.append(
                {
                    "id": entity_id_value,
                    "label": label_value or entity_id_value,
                    "type": entity_type_value,
                }
            )
        return highlights

    def _normalise_str_list(self, value: object) -> List[str]:
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, (list, tuple, set)):
            normalised: List[str] = []
            for item in value:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    normalised.append(text)
            return normalised
        return []

    def _page_number(
        self,
        payload: Dict[str, object],
        page_label: str | None,
        chunk_index: int | None,
    ) -> int | None:
        explicit = payload.get("page_number") or payload.get("page")
        number = self._extract_page_number(explicit)
        if number is not None:
            return number
        number = self._extract_page_number(page_label)
        if number is not None:
            return number
        if chunk_index is not None and chunk_index >= 0:
            return chunk_index + 1
        return None

    def _extract_page_number(self, value: object) -> int | None:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match:
                try:
                    return int(match.group(0))
                except ValueError:
                    return None
        return None

    def _build_trace(
        self, results: List[qmodels.ScoredPoint], entity_ids: List[str]
    ) -> Tuple[Trace, List[Tuple[str, str | None]]]:
        vector_trace = [self._vector_trace_entry(point) for point in results]
        forensics_trace = self._build_forensics_trace(results)
        subgraph: GraphSubgraph = self.graph_service.subgraph(entity_ids)
        node_map: Dict[str, GraphNode] = dict(subgraph.nodes)
        edge_bucket: Dict[Tuple[str, str, str, str | None], GraphEdge] = dict(subgraph.edges)
        relation_statements: List[Tuple[str, str | None]] = []
        statement_seen: Set[Tuple[str, str | None]] = set()
        for edge in edge_bucket.values():
            if edge.type == "MENTIONS":
                continue
            statement = self._format_relation_statement(edge, node_map)
            if not statement:
                continue
            doc_id_raw = edge.properties.get("doc_id")
            doc_id = str(doc_id_raw) if doc_id_raw is not None else None
            statement_key = (statement, doc_id)
            if statement_key in statement_seen:
                continue
            statement_seen.add(statement_key)
            relation_statements.append(statement_key)
        graph_trace = subgraph.to_payload()
        doc_ids_from_results: Set[str] = {
            str(point.payload.get("doc_id"))
            for point in results
            if point.payload and point.payload.get("doc_id") is not None
        }
        doc_scope = doc_ids_from_results | subgraph.document_ids()
        graph_trace["communities"] = [
            community.to_dict()
            for community in self.graph_service.communities_for_nodes(node_map.keys())
        ]
        graph_trace["events"] = self._timeline_events_for_docs(doc_scope)
        privilege_trace = self._build_privilege_trace(results)
        trace = Trace(
            vector=vector_trace,
            graph=graph_trace,
            forensics=forensics_trace,
            privilege=privilege_trace,
        )
        return trace, relation_statements

    def _vector_trace_entry(self, point: qmodels.ScoredPoint) -> Dict[str, object]:
        payload = point.payload or {}
        raw_doc = payload.get("doc_id")
        doc_id = str(raw_doc) if raw_doc is not None else None
        text = str(payload.get("text", ""))
        preview = text[:180] + ("..." if len(text) > 180 else "")
        entry = {
            "id": str(point.id),
            "score": float(point.score),
            "docId": doc_id,
            "chunkIndex": payload.get("chunk_index"),
            "sourceType": payload.get("source_type"),
            "embeddingNorm": payload.get("embedding_norm"),
            "textPreview": preview,
            "metadata": self._compact_vector_metadata(payload),
        }
        return entry

    @staticmethod
    def _compact_vector_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
        keys = {
            "origin",
            "doc_type",
            "source_type",
            "entity_ids",
            "entity_labels",
            "checksum_sha256",
        }
        compact = {key: payload.get(key) for key in keys if payload.get(key) is not None}
        return ForensicsService.to_jsonable(compact) if compact else {}
    def _merge_relation_statements(
        self,
        primary: List[Tuple[str, str | None]],
        secondary: List[Tuple[str, str | None]],
    ) -> List[Tuple[str, str | None]]:
        merged: List[Tuple[str, str | None]] = []
        seen: Set[Tuple[str, str | None]] = set()
        for statement in primary + secondary:
            key = (statement[0], statement[1])
            if key in seen:
                continue
            seen.add(key)
            merged.append(key)
        return merged

    def _build_privilege_trace(self, results: List[qmodels.ScoredPoint]) -> Dict[str, object]:
        decisions: List[PrivilegeDecision] = []
        for point in results:
            payload = point.payload or {}
            doc_id = payload.get("doc_id")
            if doc_id is None:
                continue
            text = payload.get("text")
            metadata = self._augment_privilege_metadata(payload, str(doc_id))
            decision = self.privilege_classifier.classify(str(doc_id), str(text or ""), metadata)
            decisions.append(decision)
        return self.privilege_classifier.format_trace(decisions)

    def _page_privilege_trace(
        self, privilege_trace: Dict[str, object], doc_ids: Set[str]
    ) -> Dict[str, object]:
        if not doc_ids:
            return {"decisions": [], "aggregate": privilege_trace.get("aggregate", {})}
        decisions_payload = privilege_trace.get("decisions", [])
        filtered_payload = [
            decision
            for decision in decisions_payload
            if str(decision.get("doc_id")) in doc_ids
        ]
        decisions = [
            PrivilegeDecision(
                doc_id=str(item.get("doc_id", "")),
                label=str(item.get("label", "unknown")),
                score=float(item.get("score", 0.0)),
                explanation=str(item.get("explanation", "")),
                source=str(item.get("source", "classifier")),
            )
            for item in filtered_payload
        ]
        summary = self.privilege_classifier.aggregate(decisions)
        return {
            "decisions": filtered_payload,
            "aggregate": summary.to_dict(),
        }

    def _build_forensics_trace(
        self, results: List[qmodels.ScoredPoint]
    ) -> List[Dict[str, object]]:
        entries: List[Dict[str, object]] = []
        seen: Set[str] = set()
        for point in results:
            payload = point.payload or {}
            raw_doc = payload.get("doc_id")
            if raw_doc is None:
                continue
            doc_id = str(raw_doc)
            if doc_id in seen:
                continue
            seen.add(doc_id)
            doc_type = payload.get("type")
            if doc_type is None:
                try:
                    record = self.document_store.read_document(doc_id)
                except FileNotFoundError:
                    record = {}
                doc_type = record.get("type")
            artifact = self._artifact_name_for_type(doc_type)
            if artifact is None:
                continue
            if not self.forensics_service.report_exists(doc_id, artifact):
                continue
            try:
                report_payload = self.forensics_service.load_artifact(doc_id, artifact)
            except FileNotFoundError:
                continue
            entries.append(
                {
                    "document_id": doc_id,
                    "artifact": artifact,
                    "schema_version": report_payload.get("schema_version", "unknown"),
                    "summary": report_payload.get("summary", ""),
                    "fallback_applied": report_payload.get("fallback_applied", False),
                }
            )
        return entries

    def _timeline_events_for_docs(self, doc_ids: Set[str]) -> List[Dict[str, object]]:
        if not doc_ids:
            return []
        events = self.timeline_store.read_all()
        payload: List[Dict[str, object]] = []
        for event in events:
            if not any(citation in doc_ids for citation in event.citations):
                continue
            payload.append(
                {
                    "id": event.id,
                    "ts": event.ts.isoformat(),
                    "title": event.title,
                    "summary": event.summary,
                    "citations": list(event.citations),
                    "entity_highlights": list(event.entity_highlights),
                    "relation_tags": list(event.relation_tags),
                    "confidence": event.confidence,
                }
            )
        return payload

    def _apply_filters(
        self,
        results: List[qmodels.ScoredPoint],
        source_filter: str | None,
        entity_filter: str | None,
    ) -> List[qmodels.ScoredPoint]:
        if source_filter is None and entity_filter is None:
            return results
        filtered: List[qmodels.ScoredPoint] = []
        doc_cache: Dict[str, Dict[str, object]] = {}
        entity_cache: Dict[str, List[GraphNode]] = {}
        for point in results:
            payload = point.payload or {}
            raw_doc = payload.get("doc_id")
            doc_id = str(raw_doc) if raw_doc is not None else None
            if source_filter and not self._matches_source(payload, source_filter, doc_id, doc_cache):
                continue
            if entity_filter and not self._matches_entity(payload, entity_filter, doc_id, entity_cache, doc_cache):
                continue
            filtered.append(point)
        return filtered

    def _matches_source(
        self,
        payload: Dict[str, object],
        source_filter: str,
        doc_id: str | None,
        doc_cache: Dict[str, Dict[str, object]],
    ) -> bool:
        payload_source = str(payload.get("source_type", "")).lower()
        if payload_source == source_filter:
            return True
        if doc_id is None:
            return False
        if doc_id not in doc_cache:
            try:
                doc_cache[doc_id] = self.document_store.read_document(doc_id)
            except FileNotFoundError:
                doc_cache[doc_id] = {}
        record_source = str(doc_cache[doc_id].get("source_type", "")).lower()
        return record_source == source_filter

    def _matches_entity(
        self,
        payload: Dict[str, object],
        entity_filter: str,
        doc_id: str | None,
        entity_cache: Dict[str, List[GraphNode]],
        doc_cache: Dict[str, Dict[str, object]],
    ) -> bool:
        token = entity_filter.lower()
        labels = [str(label) for label in payload.get("entity_labels", [])]
        ids = [str(identifier) for identifier in payload.get("entity_ids", [])]
        if any(token in label.lower() for label in labels):
            return True
        if any(token == identifier.lower() for identifier in ids):
            return True
        if doc_id is None:
            return False
        if doc_id not in doc_cache:
            try:
                doc_cache[doc_id] = self.document_store.read_document(doc_id)
            except FileNotFoundError:
                doc_cache[doc_id] = {}
        record = doc_cache[doc_id]
        record_labels = [str(label) for label in record.get("entity_labels", [])]
        record_ids = [str(identifier) for identifier in record.get("entity_ids", [])]
        if any(token in label.lower() for label in record_labels):
            return True
        if any(token == identifier.lower() for identifier in record_ids):
            return True
        if doc_id not in entity_cache:
            mapping = self.graph_service.document_entities([doc_id])
            entity_cache[doc_id] = mapping.get(doc_id, [])
        for node in entity_cache.get(doc_id, []):
            label = str(node.properties.get("label", "")).lower()
            if token in label:
                return True
            if token == node.id.lower():
                return True
        return False

    def _rerank_results(
        self,
        results: List[qmodels.ScoredPoint],
        entity_filter: str | None,
    ) -> List[qmodels.ScoredPoint]:
        if not results:
            return results
        entity_token = entity_filter.lower() if entity_filter else None
        forensics_cache: Dict[str, bool] = {}
        ranked: List[Tuple[float, qmodels.ScoredPoint]] = []
        for point in results:
            payload = point.payload or {}
            base_score = float(point.score or 0.0)
            boost = 0.0
            labels = [str(label) for label in payload.get("entity_labels", [])]
            ids = [str(identifier) for identifier in payload.get("entity_ids", [])]
            if entity_token:
                if any(entity_token in label.lower() for label in labels) or any(
                    entity_token == identifier.lower() for identifier in ids
                ):
                    boost += 0.25
            boost += min(0.15, 0.02 * len(labels))
            raw_doc = payload.get("doc_id")
            doc_id = str(raw_doc) if raw_doc is not None else None
            if doc_id:
                artifact = self._artifact_name_for_type(payload.get("doc_type") or payload.get("type"))
                if artifact:
                    if doc_id not in forensics_cache:
                        forensics_cache[doc_id] = self.forensics_service.report_exists(doc_id, artifact)
                    if forensics_cache[doc_id]:
                        boost += 0.05
            ranked.append((base_score + boost, point))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in ranked]

    @staticmethod
    def _artifact_name_for_type(doc_type: str | None) -> str | None:
        if doc_type in {"text", "document", "note"}:
            return "document"
        if doc_type == "image":
            return "image"
        if doc_type == "financial":
            return "financial"
        return None

    def _collect_entities(self, results: List[qmodels.ScoredPoint]) -> List[str]:
        entity_ids: List[str] = []
        seen: Set[str] = set()
        for point in results:
            payload = point.payload or {}
            text = payload.get("text", "")
            for span in extract_entities(text):
                entity_id = normalise_entity_id(span.label)
                if entity_id not in seen:
                    seen.add(entity_id)
                    entity_ids.append(entity_id)
        return entity_ids

    def _augment_entity_ids(self, question: str, vector_entities: List[str]) -> List[str]:
        combined: List[str] = list(vector_entities)
        seen: Set[str] = set(vector_entities)
        for span in extract_entities(question):
            entity_id = normalise_entity_id(span.label)
            if entity_id and entity_id not in seen:
                combined.append(entity_id)
                seen.add(entity_id)
        for node in self.graph_service.search_entities(question):
            if node.id not in seen:
                combined.append(node.id)
                seen.add(node.id)
        return combined

    def _format_relation_statement(self, edge: GraphEdge, nodes: Dict[str, GraphNode]) -> str:
        source_node = nodes.get(edge.source)
        target_node = nodes.get(edge.target)
        source_label = self._node_label(source_node, edge.source)
        target_label = self._node_label(target_node, edge.target)
        predicate = edge.properties.get("predicate") or edge.properties.get("relation")
        if not predicate:
            predicate = edge.type.replace("_", " ").lower()
        return f"{source_label} {predicate} {target_label}"

    @staticmethod
    def _node_label(node: GraphNode | None, fallback: str) -> str:
        if node is None:
            return fallback
        label = node.properties.get("label")
        if isinstance(label, str) and label:
            return label
        title = node.properties.get("title")
        if isinstance(title, str) and title:
            return title
        return fallback

    def stream_result(
        self,
        result: QueryResult,
        *,
        attributes: Dict[str, object],
        chunk_size: int = 160,
    ) -> Iterator[str]:
        def _iterator() -> Iterator[str]:
            start = perf_counter()
            meta_event = {
                "type": "meta",
                "meta": result.meta.to_dict(),
                "hasEvidence": result.has_evidence,
            }
            meta_payload = json.dumps(meta_event)
            first_latency = (perf_counter() - start) * 1000.0
            _retrieval_partial_latency.record(first_latency, attributes=attributes)
            yield meta_payload
            emitted = 0
            answer = result.answer or ""
            for idx in range(0, len(answer), chunk_size):
                chunk = answer[idx : idx + chunk_size]
                if not chunk:
                    continue
                yield json.dumps({"type": "answer", "delta": chunk})
                emitted += 1
            final_event = {
                "type": "final",
                "answer": result.answer,
                "citations": [citation.to_dict() for citation in result.citations],
                "traces": result.trace.to_dict(),
                "meta": result.meta.to_dict(),
            }
            yield json.dumps(final_event)
            _retrieval_stream_chunks_counter.add(emitted, attributes=attributes)

        return _iterator()


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()

