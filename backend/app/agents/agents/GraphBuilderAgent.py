from __future__ import annotations

from typing import List, Dict, Any

from backend.app.services.graph import GraphService, get_graph_service
from backend.app.utils.triples import EntitySpan, Triple

class GraphBuilderAgent:
    def __init__(self, graph_service: GraphService = get_graph_service()):
        self.graph_service = graph_service

    def build_graph_from_extracted_data(
        self,
        doc_id: str,
        entities: List[EntitySpan],
        triples: List[Triple],
    ) -> Dict[str, Any]:
        """Builds or updates the knowledge graph with extracted entities and triples.

        Args:
            doc_id: The ID of the document from which data was extracted.
            entities: A list of extracted entities.
            triples: A list of extracted triples (subject, predicate, object).

        Returns:
            A dictionary summarizing the graph mutations.
        """
        nodes_upserted = 0
        relations_merged = 0

        # Upsert entities
        for span in entities:
            self.graph_service.upsert_entity(span.label, span.entity_type, {"label": span.label, "type": span.entity_type})
            self.graph_service.merge_relation(doc_id, "MENTIONS", span.label, {"doc_id": doc_id})
            nodes_upserted += 1
            relations_merged += 1

        # Upsert triples
        for triple in triples:
            self.graph_service.upsert_entity(triple.subject.label, triple.subject.entity_type, {"label": triple.subject.label, "type": triple.subject.entity_type})
            self.graph_service.upsert_entity(triple.obj.label, triple.obj.entity_type, {"label": triple.obj.label, "type": triple.obj.entity_type})
            self.graph_service.merge_relation(
                triple.subject.label,
                triple.predicate,
                triple.obj.label,
                {
                    "doc_id": doc_id,
                    "predicate_text": triple.predicate_text,
                    "evidence": triple.evidence,
                },
            )
            nodes_upserted += 2 # Subject and object
            relations_merged += 1
        
        return {
            "nodes_upserted": nodes_upserted,
            "relations_merged": relations_merged,
        }
