from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

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
            self._seed_ontology()
        else:
            self._nodes: Dict[str, GraphNode] = {}
            self._edges: Dict[Tuple[str, str, str, str | None], GraphEdge] = {}
            self._seed_ontology()

    # region Schema management
    def _ensure_constraints(self) -> None:
        def run(tx) -> None:
            tx.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            tx.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
        with self.driver.session() as session:
            session.execute_write(run)

    # endregion

    def _seed_ontology(self) -> None:
        classes = (
            ("ontology::root", "OntologyRoot", {"name": "root"}),
            ("ontology::organization", "OntologyClass", {"name": "Organization"}),
            ("ontology::person", "OntologyClass", {"name": "Person"}),
            ("ontology::location", "OntologyClass", {"name": "Location"}),
            ("ontology::event", "OntologyClass", {"name": "Event"}),
        )
        if self.mode == "neo4j":
            query = (
                "MERGE (root:OntologyRoot {id: $root_id}) SET root.name = $root_name "
                "MERGE (child:OntologyClass {id: $child_id}) "
                "SET child.name = $child_name, child.type = $child_type "
                "MERGE (root)-[:ONTOLOGY_CHILD]->(child)"
            )
            with self.driver.session() as session:
                for child_id, child_type, properties in classes[1:]:
                    session.execute_write(
                        lambda tx, cid=child_id, cname=properties["name"], ctype=child_type: tx.run(
                            query,
                            root_id=classes[0][0],
                            root_name=classes[0][2]["name"],
                            child_id=cid,
                            child_name=cname,
                            child_type=ctype,
                        )
                    )
        else:
            root_id, root_type, root_props = classes[0]
            self._nodes.setdefault(root_id, GraphNode(id=root_id, type=root_type, properties=root_props))
            for child_id, child_type, properties in classes[1:]:
                self._nodes.setdefault(
                    child_id,
                    GraphNode(
                        id=child_id,
                        type=child_type,
                        properties=properties,
                    ),
                )
                key = (root_id, "ONTOLOGY_CHILD", child_id, None)
                if key not in self._edges:
                    self._edges[key] = GraphEdge(
                        source=root_id,
                        target=child_id,
                        type="ONTOLOGY_CHILD",
                        properties={},
                    )

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
            key = self._edge_key(source_id, relation_type, target_id, properties)
            if key in self._edges:
                merged = self._merge_properties(self._edges[key].properties, properties)
                self._edges[key] = GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relation_type,
                    properties=merged,
                )
            else:
                self._edges[key] = GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relation_type,
                    properties=properties,
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
        edges = [
            edge
            for edge in self._edges.values()
            if edge.source == node_id or edge.target == node_id
        ]
        for edge in edges:
            neighbor_nodes.setdefault(edge.source, self._nodes.get(edge.source, GraphNode(edge.source, "Unknown", {})))
            neighbor_nodes.setdefault(edge.target, self._nodes.get(edge.target, GraphNode(edge.target, "Unknown", {})))
        return list(neighbor_nodes.values()), edges

    def search_entities(self, query: str, limit: int = 5) -> List[GraphNode]:
        if not query:
            return []
        term = query.lower()
        if self.mode == "neo4j":
            stmt = (
                "MATCH (e:Entity) WHERE toLower(e.label) CONTAINS $term "
                "RETURN e LIMIT $limit"
            )
            with self.driver.session() as session:
                result = session.execute_read(
                    lambda tx: list(tx.run(stmt, term=term, limit=limit))
                )
            nodes: List[GraphNode] = []
            for record in result:
                node = record["e"]
                nodes.append(
                    GraphNode(
                        id=node["id"],
                        type=node.get("type", "Entity"),
                        properties=dict(node),
                    )
                )
            return nodes
        matches: List[GraphNode] = []
        for node in self._nodes.values():
            if node.type not in {"Entity", "Organization", "Person", "Location", "Event"}:
                continue
            label = str(node.properties.get("label", "")).lower()
            if term in label:
                matches.append(node)
        matches.sort(key=lambda node: node.properties.get("label", ""))
        return matches[:limit]

    def document_entities(self, doc_ids: Iterable[str]) -> Dict[str, List[GraphNode]]:
        ids = list(dict.fromkeys(doc_ids))
        if not ids:
            return {}
        mapping: Dict[str, List[GraphNode]] = {doc_id: [] for doc_id in ids}
        if self.mode == "neo4j":
            query = (
                "MATCH (d:Document)-[:MENTIONS]->(e:Entity) "
                "WHERE d.id IN $doc_ids RETURN d.id AS doc_id, e"
            )
            with self.driver.session() as session:
                records = session.execute_read(
                    lambda tx: list(tx.run(query, doc_ids=ids))
                )
            for record in records:
                node = record["e"]
                graph_node = GraphNode(
                    id=node["id"],
                    type=node.get("type", "Entity"),
                    properties=dict(node),
                )
                mapping.setdefault(record["doc_id"], []).append(graph_node)
            return mapping

        for edge in self._edges.values():
            if edge.type != "MENTIONS":
                continue
            if edge.source not in mapping:
                continue
            node = self._nodes.get(edge.target)
            if node is None:
                continue
            mapping[edge.source].append(node)
        return mapping

    def _edge_key(
        self, source_id: str, relation_type: str, target_id: str, properties: Dict[str, object]
    ) -> Tuple[str, str, str, str | None]:
        doc_id = properties.get("doc_id")
        return (source_id, relation_type, target_id, str(doc_id) if doc_id is not None else None)

    @staticmethod
    def _merge_properties(
        existing: Dict[str, object], new_values: Dict[str, object]
    ) -> Dict[str, object]:
        merged = dict(existing)
        for key, value in new_values.items():
            if key == "evidence":
                current = merged.setdefault("evidence", [])
                if isinstance(value, list):
                    for item in value:
                        if item not in current:
                            current.append(item)
                else:
                    if value not in current:
                        current.append(value)
            else:
                merged[key] = value
        return merged

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

