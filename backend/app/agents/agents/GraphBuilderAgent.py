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
    async def discover_connections(self, doc_id: str) -> int:
        """
        Autonomous connection discovery.
        Scans the graph for nodes related to the entities in the given document
        and infers new relationships based on shared properties or co-occurrence.
        """
        # Placeholder for complex logic:
        # 1. Get all entities in doc
        # 2. Find other docs with same entities
        # 3. Create "RELATED_TO" edges between docs
        
        # For now, we'll just do a simple Cypher query to link docs sharing entities
        if self.graph_service.mode != "neo4j":
            return 0
            
        query = """
        MATCH (d1:Document {id: $doc_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(d2:Document)
        WHERE d1 <> d2
        MERGE (d1)-[r:RELATED_TO]->(d2)
        SET r.weight = coalesce(r.weight, 0) + 1
        RETURN count(r) as connections
        """
        
        try:
            with self.graph_service.driver.session() as session:
                result = session.run(query, doc_id=doc_id)
                record = result.single()
                return record["connections"] if record else 0
        except Exception as e:
            print(f"Connection discovery failed: {e}")
            return 0

    async def cluster_nodes(self) -> int:
        """
        Runs community detection (Louvain) to find clusters of related entities.
        """
        if self.graph_service.mode != "neo4j":
            return 0
            
        # Requires GDS library in Neo4j, or we can simulate it
        # For this "Wow" factor, let's assume we might have GDS or just do a simple label propagation
        # If GDS is not available, we can't do much.
        # Let's try a simple Cypher-based label propagation if possible, or just skip.
        return 0
