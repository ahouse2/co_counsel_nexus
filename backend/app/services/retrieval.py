from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Dict, List, Set, Tuple

from qdrant_client.http import models as qmodels

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..config import get_settings
from ..storage.document_store import DocumentStore
from ..utils.text import hashed_embedding
from ..utils.triples import extract_entities, normalise_entity_id
from .forensics import ForensicsService, get_forensics_service
from .graph import GraphEdge, GraphNode, GraphService, get_graph_service
from .vector import VectorService, get_vector_service


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)
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


@dataclass
class Citation:
    doc_id: str
    span: str
    uri: str | None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {"docId": self.doc_id, "span": self.span}
        if self.uri:
            payload["uri"] = self.uri
        return payload


@dataclass
class Trace:
    vector: List[Dict[str, object]]
    graph: Dict[str, List[Dict[str, object]]]
    forensics: List[Dict[str, object]]

    def to_dict(self) -> Dict[str, object]:
        return {"vector": self.vector, "graph": self.graph, "forensics": self.forensics}


@dataclass
class QueryMeta:
    page: int
    page_size: int
    total_items: int
    has_next: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "has_next": self.has_next,
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
    ) -> None:
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.graph_service = graph_service or get_graph_service()
        self.document_store = document_store or DocumentStore(self.settings.document_store_dir)
        self.forensics_service = forensics_service or get_forensics_service()

    def query(
        self,
        question: str,
        *,
        page: int = 1,
        page_size: int = 10,
        filters: Dict[str, str] | None = None,
        rerank: bool = False,
    ) -> QueryResult:
        if page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if page_size < 1 or page_size > 50:
            raise ValueError("page_size must be between 1 and 50")
        start_time = perf_counter()
        filters = filters or {}
        allowed_sources = {"local", "s3", "sharepoint"}

        with _tracer.start_as_current_span("retrieval.query") as span:
            span.set_attribute("retrieval.page", page)
            span.set_attribute("retrieval.page_size", page_size)
            span.set_attribute("retrieval.rerank", rerank)

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
            search_window = min(max_window, max(page * page_size * 2, page_size))
            span.set_attribute("retrieval.search_window", search_window)

            query_vector = hashed_embedding(question, self.settings.qdrant_vector_size)
            with _tracer.start_as_current_span("retrieval.vector_search") as vector_span:
                vector_span.set_attribute("retrieval.vector.top_k", search_window)
                results = self.vector_service.search(query_vector, top_k=search_window)
                vector_span.set_attribute("retrieval.vector.count", len(results))

            if rerank:
                with _tracer.start_as_current_span("retrieval.rerank") as rerank_span:
                    rerank_span.set_attribute("retrieval.rerank.candidates", len(results))
                    results = self._rerank_results(results, entity_filter)
                    rerank_span.set_attribute("retrieval.rerank.reordered", len(results))

            filtered_results = self._apply_filters(results, source_filter, entity_filter)
            span.set_attribute("retrieval.filtered_results", len(filtered_results))

            total_items = len(filtered_results)
            metric_attrs: Dict[str, object] = {
                "rerank": rerank,
                "filter_source": source_filter or "any",
                "filter_entity": bool(entity_filter),
            }

            if total_items == 0:
                has_evidence = False
                metric_attrs["has_evidence"] = has_evidence
                duration_ms = (perf_counter() - start_time) * 1000.0
                span.set_attribute("retrieval.total_items", total_items)
                span.set_attribute("retrieval.has_evidence", has_evidence)
                span.set_attribute("retrieval.duration_ms", duration_ms)
                _retrieval_queries_counter.add(1, attributes=metric_attrs)
                _retrieval_query_duration.record(duration_ms, attributes=metric_attrs)
                _retrieval_results_histogram.record(total_items, attributes=metric_attrs)
                empty_trace = Trace(vector=[], graph={"nodes": [], "edges": []}, forensics=[])
                meta = QueryMeta(page=page, page_size=page_size, total_items=0, has_next=False)
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

            primary_span = filtered_results[: page_size]
            graph_window = min(self.settings.retrieval_graph_hop_window, max(len(primary_span), 1))
            graph_seed = filtered_results[:graph_window]
            vector_entities = self._collect_entities(graph_seed)
            entity_ids = self._augment_entity_ids(question, vector_entities)
            with _tracer.start_as_current_span("retrieval.trace_build") as trace_span:
                trace_span.set_attribute("retrieval.trace.entity_ids", len(entity_ids))
                trace_full, relation_statements = self._build_trace(filtered_results, entity_ids)
                trace_span.set_attribute("retrieval.trace.nodes", len(trace_full.graph.get("nodes", [])))
                trace_span.set_attribute("retrieval.trace.edges", len(trace_full.graph.get("edges", [])))
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

            trace_page = Trace(
                vector=vector_trace_page,
                graph={"nodes": graph_nodes_page, "edges": graph_edges_page},
                forensics=forensics_trace_page,
            )

            answer = self._compose_answer(question, filtered_results, relation_statements)
            if start >= total_items:
                answer = (
                    f"{answer} No additional supporting evidence available for page {page}; "
                    "adjust pagination or filters to view existing evidence."
                )

            meta = QueryMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                has_next=has_next,
            )

            has_evidence = True
            metric_attrs["has_evidence"] = has_evidence
            duration_ms = (perf_counter() - start_time) * 1000.0
            span.set_attribute("retrieval.total_items", total_items)
            span.set_attribute("retrieval.has_evidence", has_evidence)
            span.set_attribute("retrieval.duration_ms", duration_ms)
            _retrieval_queries_counter.add(1, attributes=metric_attrs)
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
        for point in results:
            payload = point.payload or {}
            raw_doc_id = payload.get("doc_id")
            if raw_doc_id is None:
                continue
            doc_id = str(raw_doc_id)
            uri = payload.get("uri")
            if uri is None:
                try:
                    doc_record = self.document_store.read_document(doc_id)
                    uri = doc_record.get("uri") if isinstance(doc_record, dict) else None
                except FileNotFoundError:
                    uri = None
            text = payload.get("text", "")
            span = text[:180] + ("..." if len(text) > 180 else "")
            citations.append(Citation(doc_id=doc_id, span=span, uri=uri))
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

    def _build_trace(
        self, results: List[qmodels.ScoredPoint], entity_ids: List[str]
    ) -> Tuple[Trace, List[str]]:
        vector_trace = [
            {
                "id": str(point.id),
                "score": point.score,
                "docId": point.payload.get("doc_id") if point.payload else None,
            }
            for point in results
        ]
        forensics_trace = self._build_forensics_trace(results)
        node_map: Dict[str, GraphNode] = {}
        edge_bucket: Dict[Tuple[str, str, str, object], GraphEdge] = {}
        relation_statements: List[str] = []
        statement_seen: Set[str] = set()
        for entity_id in entity_ids:
            try:
                node_list, edge_list = self.graph_service.neighbors(entity_id)
            except KeyError:
                continue
            for node in node_list:
                node_map[node.id] = node
            for edge in edge_list:
                key = (edge.source, edge.type, edge.target, edge.properties.get("doc_id"))
                if key not in edge_bucket:
                    edge_bucket[key] = edge
                if edge.type != "MENTIONS":
                    statement = self._format_relation_statement(edge, node_map)
                    if statement and statement not in statement_seen:
                        statement_seen.add(statement)
                        relation_statements.append(statement)
        graph_trace = {
            "nodes": [
                {"id": node.id, "type": node.type, "properties": node.properties}
                for node in node_map.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "properties": edge.properties,
                }
                for edge in edge_bucket.values()
            ],
        }
        return Trace(vector=vector_trace, graph=graph_trace, forensics=forensics_trace), relation_statements

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


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()

