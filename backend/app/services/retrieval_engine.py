from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from qdrant_client.http import models as qmodels

from ..storage.document_store import DocumentStore
from ..utils.triples import extract_entities, normalise_entity_id
from .graph import GraphEdge, GraphNode, GraphService
from .vector import VectorService

try:  # pragma: no cover - optional dependency
    from llama_index.core.schema import NodeWithScore, TextNode
except ModuleNotFoundError:  # pragma: no cover - fallback shims

    @dataclass
    class TextNode:  # type: ignore
        id_: str
        text: str
        metadata: Dict[str, object] = field(default_factory=dict)

    @dataclass
    class NodeWithScore:  # type: ignore
        node: TextNode
        score: float


@dataclass
class HybridRetrievalBundle:
    fused_points: List[qmodels.ScoredPoint]
    vector_points: List[qmodels.ScoredPoint]
    graph_points: List[qmodels.ScoredPoint]
    keyword_points: List[qmodels.ScoredPoint]
    relation_statements: List[Tuple[str, str | None]]
    reranker: str
    fusion_scores: Dict[str, float]
    external_points: List[qmodels.ScoredPoint] = field(default_factory=list)


class VectorRetrieverAdapter:
    """Adapter that exposes VectorService results as LlamaIndex-style nodes."""

    def __init__(self, vector_service: VectorService, embedding_model) -> None:
        self.vector_service = vector_service
        self.embedding_model = embedding_model

    def retrieve(self, query: str, *, top_k: int) -> List[qmodels.ScoredPoint]:
        query_vector = self._embed_query(query)
        return self.vector_service.search(query_vector, top_k=top_k)

    def _embed_query(self, query: str) -> List[float]:
        if hasattr(self.embedding_model, "get_query_embedding"):
            return list(self.embedding_model.get_query_embedding(query))
        return list(self.embedding_model.get_text_embedding(query))


class GraphRetrieverAdapter:
    """Emit graph relation statements as scored points."""

    def __init__(self, graph_service: GraphService) -> None:
        self.graph_service = graph_service

    def retrieve(self, query: str, *, top_k: int) -> Tuple[List[qmodels.ScoredPoint], List[Tuple[str, str | None]]]:
        entities = self.graph_service.search_entities(query, limit=top_k)
        if not entities:
            entities = self._entities_from_question(query, limit=top_k)
        relation_statements: List[Tuple[str, str | None]] = []
        points: List[qmodels.ScoredPoint] = []
        for entity in entities[:top_k]:
            subgraph = self.graph_service.subgraph([entity.id])
            node_map: Dict[str, GraphNode] = dict(subgraph.nodes)
            for edge in subgraph.edges.values():
                statement = _format_relation_statement(edge, node_map)
                if not statement:
                    continue
                doc_id_raw = edge.properties.get("doc_id")
                doc_id = str(doc_id_raw) if doc_id_raw is not None else None
                relation_statements.append((statement, doc_id))
                point_id = f"graph::{edge.source}::{edge.type}::{edge.target}::{doc_id or 'unknown'}"
                payload = {
                    "doc_id": doc_id,
                    "text": statement,
                    "relation_type": edge.type,
                    "source_type": edge.properties.get("source_type", "graph"),
                    "entity_ids": [edge.source, edge.target],
                    "entity_labels": _entity_labels(edge, node_map),
                    "retriever": "graph",
                }
                points.append(
                    qmodels.ScoredPoint(
                        id=point_id,
                        score=0.6,
                        payload=payload,
                        version=1,
                    )
                )
        return points[:top_k], relation_statements[: top_k * 2]

    def _entities_from_question(self, query: str, limit: int) -> List[GraphNode]:
        seen: set[str] = set()
        nodes: List[GraphNode] = []
        for span in extract_entities(query):
            entity_id = normalise_entity_id(span.label)
            if not entity_id or entity_id in seen:
                continue
            seen.add(entity_id)
            existing = getattr(self.graph_service, "_nodes", {}).get(entity_id)
            if existing is not None:
                nodes.append(existing)
            else:
                nodes.append(GraphNode(id=entity_id, type="Entity", properties={"label": span.label}))
            if len(nodes) >= limit:
                break
        return nodes


class KeywordRetrieverAdapter:
    """Keyword/BM25-style scoring using document metadata stored locally."""

    _TOKEN_RE = re.compile(r"[A-Za-z0-9']+")

    def __init__(self, document_store: DocumentStore) -> None:
        self.document_store = document_store

    def retrieve(self, query: str, *, top_k: int) -> List[qmodels.ScoredPoint]:
        tokens = {token.lower() for token in self._TOKEN_RE.findall(query)}
        if not tokens:
            return []
        scored: List[Tuple[float, Dict[str, object]]] = []
        for document in self.document_store.list_documents():
            doc_tokens = self._document_tokens(document)
            overlap = tokens & doc_tokens
            if not overlap:
                continue
            title = str(document.get("title", document.get("name", "")))
            snippet = document.get("summary") or title
            payload = {
                "doc_id": document.get("id"),
                "text": str(snippet),
                "title": title,
                "source_type": document.get("source_type"),
                "retriever": "keyword",
                "entity_labels": document.get("entity_labels", []),
                "entity_ids": document.get("entity_ids", []),
            }
            score = self._score(tokens, doc_tokens, len(snippet or ""))
            scored.append((score, payload))
        scored.sort(key=lambda item: item[0], reverse=True)
        points: List[qmodels.ScoredPoint] = []
        for index, (score, payload) in enumerate(scored[:top_k]):
            point_id = f"keyword::{payload.get('doc_id', 'unknown')}::{index}"
            points.append(
                qmodels.ScoredPoint(
                    id=point_id,
                    score=float(score),
                    payload=payload,
                    version=1,
                )
            )
        return points

    def _document_tokens(self, document: Dict[str, object]) -> set[str]:
        corpus_parts: List[str] = []
        for key in ("title", "summary", "description"):
            value = document.get(key)
            if isinstance(value, str):
                corpus_parts.append(value)
        for label in document.get("entity_labels", []) or []:
            corpus_parts.append(str(label))
        content = " ".join(corpus_parts)
        return {token.lower() for token in self._TOKEN_RE.findall(content)}

    def _score(self, query_tokens: set[str], doc_tokens: set[str], snippet_length: int) -> float:
        overlap = len(query_tokens & doc_tokens)
        if overlap == 0:
            return 0.0
        length_penalty = 1.0 if snippet_length <= 0 else min(1.0, 80.0 / float(snippet_length))
        return overlap * (0.8 + length_penalty * 0.2)


class HybridQueryEngine:
    """Fuse vector, graph, and keyword retrievers using Reciprocal Rank Fusion."""

    def __init__(
        self,
        vector: VectorRetrieverAdapter,
        graph: GraphRetrieverAdapter,
        keyword: KeywordRetrieverAdapter,
        *,
        rrf_constant: float = 60.0,
        cross_encoder_model: str | None = None,
    ) -> None:
        self.vector = vector
        self.graph = graph
        self.keyword = keyword
        self.rrf_constant = rrf_constant
        self._cross_encoder_model = cross_encoder_model
        self._cross_encoder = None
        self._cross_encoder_error: Exception | None = None

    def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        vector_window: int,
        graph_window: int,
        keyword_window: int,
        use_cross_encoder: bool,
    ) -> HybridRetrievalBundle:
        vector_points = self.vector.retrieve(query, top_k=vector_window)
        graph_points, relation_statements = self.graph.retrieve(query, top_k=graph_window)
        keyword_points = self.keyword.retrieve(query, top_k=keyword_window)
        candidates = {
            "vector": vector_points,
            "graph": graph_points,
            "keyword": keyword_points,
        }
        fused, contributions = self._fuse(candidates, top_k)
        reranker_label = "rrf"
        if use_cross_encoder:
            reranker = self._ensure_cross_encoder()
            if reranker is not None:
                fused = self._rerank_with_cross_encoder(reranker, query, fused)
                reranker_label = "cross_encoder"
        return HybridRetrievalBundle(
            fused_points=fused,
            vector_points=vector_points,
            graph_points=graph_points,
            keyword_points=keyword_points,
            relation_statements=relation_statements,
            reranker=reranker_label,
            fusion_scores=contributions,
            external_points=[],
        )

    def _fuse(
        self,
        candidates: Dict[str, List[qmodels.ScoredPoint]],
        top_k: int,
    ) -> Tuple[List[qmodels.ScoredPoint], Dict[str, float]]:
        scores: Dict[str, float] = {}
        exemplars: Dict[str, qmodels.ScoredPoint] = {}
        contributors: Dict[str, set[str]] = {}
        for retriever, points in candidates.items():
            for rank, point in enumerate(points, start=1):
                key = _point_key(point)
                exemplars.setdefault(key, point)
                contributors.setdefault(key, set()).add(retriever)
                scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrf_constant + rank)
        ordered_keys = sorted(scores.keys(), key=lambda item: scores[item], reverse=True)
        fused: List[qmodels.ScoredPoint] = []
        fused_scores: Dict[str, float] = {}
        for key in ordered_keys[:top_k]:
            point = exemplars[key]
            payload = dict(point.payload or {})
            payload.setdefault("retrievers", sorted(contributors.get(key, set())))
            payload["fusion_score"] = scores[key]
            fused.append(
                qmodels.ScoredPoint(
                    id=point.id,
                    score=float(scores[key]),
                    payload=payload,
                    version=point.version,
                )
            )
            fused_scores[key] = scores[key]
        return fused, fused_scores

    def _ensure_cross_encoder(self):  # pragma: no cover - exercised when dependency available
        if self._cross_encoder_model is None:
            return None
        if self._cross_encoder is not None:
            return self._cross_encoder
        if self._cross_encoder_error is not None:
            return None
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            self._cross_encoder_error = exc
            return None
        try:
            self._cross_encoder = CrossEncoder(self._cross_encoder_model)
        except Exception as exc:  # pragma: no cover - dependency initialisation failure
            self._cross_encoder_error = exc
            return None
        return self._cross_encoder

    def _rerank_with_cross_encoder(
        self,
        reranker,
        query: str,
        points: List[qmodels.ScoredPoint],
    ) -> List[qmodels.ScoredPoint]:  # pragma: no cover - requires optional dependency
        if not points:
            return points
        pairs = [[query, str(point.payload.get("text", ""))] for point in points]
        try:
            scores = reranker.predict(pairs)
        except Exception:  # pragma: no cover - prediction failure fallback
            return points
        rescored = list(zip(scores, points))
        rescored.sort(key=lambda item: float(item[0]), reverse=True)
        reordered: List[qmodels.ScoredPoint] = []
        for score, point in rescored:
            payload = dict(point.payload or {})
            payload["cross_encoder_score"] = float(score)
            reordered.append(
                qmodels.ScoredPoint(
                    id=point.id,
                    score=float(score),
                    payload=payload,
                    version=point.version,
                )
            )
        return reordered


def _point_key(point: qmodels.ScoredPoint) -> str:
    payload = point.payload or {}
    doc_id = payload.get("doc_id") or payload.get("id")
    chunk_index = payload.get("chunk_index")
    return f"{doc_id or point.id}::{chunk_index if chunk_index is not None else 'na'}::{point.id}"


def _entity_labels(edge: GraphEdge, node_map: Dict[str, GraphNode]) -> List[str]:
    labels: List[str] = []
    for node_id in (edge.source, edge.target):
        node = node_map.get(node_id)
        if node is None:
            continue
        label = node.properties.get("label") or node.properties.get("title")
        if label:
            labels.append(str(label))
    return labels


def _format_relation_statement(edge: GraphEdge, nodes: Dict[str, GraphNode]) -> str:
    source_node = nodes.get(edge.source)
    target_node = nodes.get(edge.target)
    source_label = _node_label(source_node, edge.source)
    target_label = _node_label(target_node, edge.target)
    predicate = edge.properties.get("predicate") or edge.properties.get("relation")
    if not predicate:
        predicate = edge.type.replace("_", " ").lower()
    return f"{source_label} {predicate} {target_label}".strip()


def _node_label(node: Optional[GraphNode], fallback: str) -> str:
    if node is None:
        return fallback
    label = node.properties.get("label")
    if isinstance(label, str) and label:
        return label
    title = node.properties.get("title")
    if isinstance(title, str) and title:
        return title
    return fallback


__all__ = [
    "HybridQueryEngine",
    "HybridRetrievalBundle",
    "VectorRetrieverAdapter",
    "GraphRetrieverAdapter",
    "KeywordRetrieverAdapter",
]
