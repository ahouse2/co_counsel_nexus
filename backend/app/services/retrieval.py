from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from qdrant_client.http import models as qmodels

from ..config import get_settings
from ..storage.document_store import DocumentStore
from ..utils.text import extract_capitalized_entities, hashed_embedding
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
        summary = self._compose_answer(question, results)
        trace = self._build_trace(results)
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

    def _compose_answer(self, question: str, results: List[qmodels.ScoredPoint]) -> str:
        if not results:
            return "No supporting evidence found for the supplied query."
        top = results[0]
        payload = top.payload or {}
        text = payload.get("text", "")
        if not text:
            return "Unable to locate textual evidence despite stored vector payloads."
        return f"Based on retrieved context, the most relevant information is: {text[:400]}"

    def _build_trace(self, results: List[qmodels.ScoredPoint]) -> Trace:
        vector_trace = [
            {
                "id": str(point.id),
                "score": point.score,
                "docId": point.payload.get("doc_id") if point.payload else None,
            }
            for point in results
        ]
        entity_ids = self._collect_entities(results)
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        for entity_id in entity_ids:
            try:
                node_list, edge_list = self.graph_service.neighbors(entity_id)
            except KeyError:
                continue
            nodes.extend(node_list)
            edges.extend(edge_list)
        graph_trace = {
            "nodes": [
                {"id": node.id, "type": node.type, "properties": node.properties}
                for node in {node.id: node for node in nodes}.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "properties": edge.properties,
                }
                for edge in edges
            ],
        }
        return Trace(vector=vector_trace, graph=graph_trace)

    def _collect_entities(self, results: List[qmodels.ScoredPoint]) -> List[str]:
        entity_ids: List[str] = []
        seen = set()
        for point in results:
            payload = point.payload or {}
            text = payload.get("text", "")
            for label in extract_capitalized_entities(text):
                doc_id = payload.get("doc_id")
                entity_id = f"entity::{label}" if doc_id is None else f"entity::{label}"
                if entity_id not in seen:
                    seen.add(entity_id)
                    entity_ids.append(entity_id)
        return entity_ids


def get_retrieval_service() -> RetrievalService:
    return RetrievalService()

