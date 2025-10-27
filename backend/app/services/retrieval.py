from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from qdrant_client.http import models as qmodels

from ..config import get_settings
from ..storage.document_store import DocumentStore
from ..utils.text import hashed_embedding
from ..utils.triples import extract_entities, normalise_entity_id
from .graph import GraphEdge, GraphNode, GraphService, get_graph_service
from .vector import VectorService, get_vector_service


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

    def to_dict(self) -> Dict[str, object]:
        return {"vector": self.vector, "graph": self.graph}


class RetrievalService:
    def __init__(
        self,
        vector_service: VectorService | None = None,
        graph_service: GraphService | None = None,
        document_store: DocumentStore | None = None,
    ) -> None:
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.graph_service = graph_service or get_graph_service()
        self.document_store = document_store or DocumentStore(self.settings.document_store_dir)

    def query(self, question: str, top_k: int = 5) -> Dict[str, object]:
        query_vector = hashed_embedding(question, self.settings.qdrant_vector_size)
        results = self.vector_service.search(query_vector, top_k=top_k)
        citations = self._build_citations(results)
        vector_entities = self._collect_entities(results)
        entity_ids = self._augment_entity_ids(question, vector_entities)
        trace, relation_statements = self._build_trace(results, entity_ids)
        summary = self._compose_answer(question, results, relation_statements)
        return {
            "answer": summary,
            "citations": [citation.to_dict() for citation in citations],
            "traces": trace.to_dict(),
        }

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
        return Trace(vector=vector_trace, graph=graph_trace), relation_statements

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

