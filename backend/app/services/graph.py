from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from neo4j import GraphDatabase

from ..config import get_settings


@dataclass
class GraphNode:
    id: str
    type: str
    properties: Dict[str, object]


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    properties: Dict[str, object]


class GraphService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.mode = "neo4j" if self.settings.neo4j_uri != "memory://" else "memory"
        if self.mode == "neo4j":
            self.driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            )
            self._ensure_constraints()
        else:
            self._nodes: Dict[str, GraphNode] = {}
            self._edges: List[GraphEdge] = []

    # region Schema management
    def _ensure_constraints(self) -> None:
        def run(tx) -> None:
            tx.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            tx.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
        with self.driver.session() as session:
            session.execute_write(run)

    # endregion

    # region Upserts
    def upsert_document(self, doc_id: str, title: str, metadata: Dict[str, object]) -> None:
        if self.mode == "neo4j":
            query = (
                "MERGE (d:Document {id: $id}) "
                "SET d.title = $title, d += $metadata"
            )
            with self.driver.session() as session:
                session.execute_write(lambda tx: tx.run(query, id=doc_id, title=title, metadata=metadata))
        else:
            self._nodes[doc_id] = GraphNode(id=doc_id, type="Document", properties={"title": title, **metadata})

    def upsert_entity(self, entity_id: str, entity_type: str, properties: Dict[str, object]) -> None:
        if self.mode == "neo4j":
            query = (
                "MERGE (e:Entity {id: $id}) "
                "SET e.type = $type, e += $properties"
            )
            with self.driver.session() as session:
                session.execute_write(
                    lambda tx: tx.run(query, id=entity_id, type=entity_type, properties=properties)
                )
        else:
            self._nodes[entity_id] = GraphNode(id=entity_id, type=entity_type, properties=properties)

    def merge_relation(
        self,
        source_id: str,
        relation_type: str,
        target_id: str,
        properties: Dict[str, object],
    ) -> None:
        if self.mode == "neo4j":
            query = (
                "MATCH (s {id: $source_id}), (t {id: $target_id}) "
                f"MERGE (s)-[r:{relation_type}]->(t) "
                "SET r += $properties"
            )
            with self.driver.session() as session:
                session.execute_write(
                    lambda tx: tx.run(
                        query,
                        source_id=source_id,
                        target_id=target_id,
                        properties=properties,
                    )
                )
        else:
            self._edges.append(
                GraphEdge(source=source_id, target=target_id, type=relation_type, properties=properties)
            )

    # endregion

    # region Queries
    def neighbors(self, node_id: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
        if self.mode == "neo4j":
            query = (
                "MATCH (n {id: $node_id})- [r] - (m) "
                "RETURN DISTINCT n, r, m"
            )
            with self.driver.session() as session:
                result = session.execute_read(lambda tx: list(tx.run(query, node_id=node_id)))
            nodes: Dict[str, GraphNode] = {}
            edges: List[GraphEdge] = []
            for record in result:
                for key in ("n", "m"):
                    node = record[key]
                    nodes[node["id"]] = GraphNode(
                        id=node["id"],
                        type=next(iter(node.labels)) if node.labels else "Unknown",
                        properties=dict(node),
                    )
                rel = record["r"]
                edges.append(
                    GraphEdge(
                        source=rel.start_node["id"],
                        target=rel.end_node["id"],
                        type=rel.type,
                        properties=dict(rel),
                    )
                )
            return list(nodes.values()), edges
        if node_id not in self._nodes:
            raise KeyError(node_id)
        neighbor_nodes = {node_id: self._nodes[node_id]}
        edges = [edge for edge in self._edges if edge.source == node_id or edge.target == node_id]
        for edge in edges:
            neighbor_nodes.setdefault(edge.source, self._nodes.get(edge.source, GraphNode(edge.source, "Unknown", {})))
            neighbor_nodes.setdefault(edge.target, self._nodes.get(edge.target, GraphNode(edge.target, "Unknown", {})))
        return list(neighbor_nodes.values()), edges

    # endregion


_graph_service: GraphService | None = None


def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service


def reset_graph_service() -> None:
    global _graph_service
    _graph_service = None

