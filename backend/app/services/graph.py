from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Set, Tuple

try:  # pragma: no cover - optional dependency for runtime graph enrichment
    from neo4j import GraphDatabase
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    class _StubGraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):  # noqa: D401 - matches neo4j API
            raise ModuleNotFoundError(
                "neo4j driver is unavailable; install neo4j package to enable graph features"
            )

    GraphDatabase = _StubGraphDatabase  # type: ignore[assignment]

from ..config import get_settings
from .errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowSeverity

try:  # Optional NetworkX support for analytics/community detection
    import networkx as nx  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    nx = None  # type: ignore

try:  # Optional LlamaIndex property-graph integration
    from llama_index.core.graph_stores.simple_labelled import (
        SimplePropertyGraphStore as _LlamaSimplePropertyGraphStore,
    )
    from llama_index.core.graph_stores.types import (  # type: ignore
        ChunkNode as _LlamaChunkNode,
        EntityNode as _LlamaEntityNode,
        LabelledNode as _LlamaLabelledNode,
        PropertyGraphStore as _LlamaPropertyGraphStore,
        Relation as _LlamaRelation,
    )
    from llama_index.core.storage.storage_context import StorageContext  # type: ignore
    from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex  # type: ignore
    try:
        from llama_index.graph_stores.neo4j import (  # type: ignore[attr-defined]
            Neo4jPropertyGraphStore as _LlamaNeo4jPropertyGraphStore,
        )
    except Exception:  # pragma: no cover - optional dependency may not exist
        _LlamaNeo4jPropertyGraphStore = None  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    _LlamaSimplePropertyGraphStore = None
    _LlamaChunkNode = None
    _LlamaEntityNode = None
    _LlamaLabelledNode = None
    _LlamaPropertyGraphStore = None
    _LlamaRelation = None
    StorageContext = None  # type: ignore
    KnowledgeGraphIndex = None  # type: ignore
    _LlamaNeo4jPropertyGraphStore = None  # type: ignore


@dataclass
class _FallbackLabelledNode:
    name: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] | None = None
    text: str | None = None

    @property
    def id(self) -> str:
        return self.name


@dataclass
class _FallbackRelation:
    label: str
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.label


class _FallbackSimplePropertyGraphStore:
    supports_structured_queries = False
    supports_vector_queries = False
    text_to_cypher_template = (
        "Use the provided graph schema to draft a Cypher query.\n"
        "Schema:\n{schema}\nQuestion: {question}\nCypher:"
    )

    def __init__(self) -> None:
        self.graph = {
            "nodes": {},
            "relations": {},
            "triplets": set(),
        }

    # -- basic query helpers -------------------------------------------------
    def get(self, properties: Optional[dict] = None, ids: Optional[List[str]] = None) -> List[_FallbackLabelledNode]:
        nodes: List[_FallbackLabelledNode] = list(self.graph["nodes"].values())
        if properties:
            nodes = [
                node
                for node in nodes
                if any(node.properties.get(key) == value for key, value in properties.items())
            ]
        if ids:
            ids_set = set(ids)
            nodes = [node for node in nodes if node.id in ids_set]
        return nodes

    def get_triplets(
        self,
        entity_names: Optional[List[str]] = None,
        relation_names: Optional[List[str]] = None,
        properties: Optional[dict] = None,
        ids: Optional[List[str]] = None,
    ) -> List[Tuple[_FallbackLabelledNode, _FallbackRelation, _FallbackLabelledNode]]:
        if not self.graph["relations"]:
            return []
        triplets: List[Tuple[_FallbackLabelledNode, _FallbackRelation, _FallbackLabelledNode]] = []
        entity_scope = set(entity_names or [])
        relation_scope = set(relation_names or [])
        id_scope = set(ids or [])
        for key, relation in self.graph["relations"].items():
            if relation_scope and relation.id not in relation_scope:
                continue
            src = self.graph["nodes"].get(relation.source_id)
            tgt = self.graph["nodes"].get(relation.target_id)
            if src is None or tgt is None:
                continue
            if entity_scope and not (src.id in entity_scope or tgt.id in entity_scope):
                continue
            if id_scope and not ({src.id, tgt.id} & id_scope):
                continue
            if properties:
                if not any(
                    src.properties.get(k) == v
                    or tgt.properties.get(k) == v
                    or relation.properties.get(k) == v
                    for k, v in properties.items()
                ):
                    continue
            triplets.append((src, relation, tgt))
        return triplets

    def get_rel_map(
        self,
        graph_nodes: List[_FallbackLabelledNode],
        depth: int = 2,
        limit: int = 30,
        ignore_rels: Optional[List[str]] = None,
    ) -> List[Tuple[_FallbackLabelledNode, _FallbackRelation, _FallbackLabelledNode]]:
        scope = {node.id for node in graph_nodes}
        return [
            triplet
            for triplet in self.get_triplets()
            if triplet[0].id in scope or triplet[2].id in scope
        ][:limit]

    def upsert_nodes(self, nodes: Sequence[_FallbackLabelledNode]) -> None:
        for node in nodes:
            self.graph["nodes"][node.id] = node

    def upsert_relations(self, relations: List[_FallbackRelation]) -> None:
        for relation in relations:
            key = f"{relation.source_id}::{relation.label}::{relation.target_id}"
            self.graph["relations"][key] = relation
            self.graph["nodes"].setdefault(
                relation.source_id,
                _FallbackLabelledNode(name=relation.source_id, label="Entity", properties={}),
            )
            self.graph["nodes"].setdefault(
                relation.target_id,
                _FallbackLabelledNode(name=relation.target_id, label="Entity", properties={}),
            )

    def delete(
        self,
        entity_names: Optional[List[str]] = None,
        relation_names: Optional[List[str]] = None,
        properties: Optional[dict] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        entity_scope = set(entity_names or []) | set(ids or [])
        relation_scope = set(relation_names or [])
        to_remove = []
        for key, relation in self.graph["relations"].items():
            if relation_scope and relation.id not in relation_scope:
                continue
            if entity_scope and not (
                relation.source_id in entity_scope or relation.target_id in entity_scope
            ):
                continue
            if properties and not any(
                relation.properties.get(k) == v for k, v in properties.items()
            ):
                continue
            to_remove.append(key)
        for key in to_remove:
            self.graph["relations"].pop(key, None)

    def structured_query(self, query: str, param_map: Optional[Dict[str, Any]] = None) -> Any:
        raise NotImplementedError("Structured queries are unsupported for fallback property graph store")

    def vector_query(self, query: Any, **_: Any) -> Tuple[List[Any], List[float]]:
        return ([], [])

    def upsert_llama_nodes(self, _: List[Any]) -> None:  # pragma: no cover - compatibility shim
        return


_EntityNodeFactory = (
    _LlamaEntityNode if _LlamaEntityNode is not None else _FallbackLabelledNode
)
_RelationFactory = _LlamaRelation if _LlamaRelation is not None else _FallbackRelation
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


@dataclass
class GraphCommunity:
    id: str
    size: int
    score: float
    nodes: List[Dict[str, object]]
    relations: List[Dict[str, object]]
    documents: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "size": self.size,
            "score": self.score,
            "nodes": self.nodes,
            "relations": self.relations,
            "documents": self.documents,
        }


@dataclass
class GraphCommunitySummary:
    generated_at: str
    algorithm: str
    total_nodes: int
    total_edges: int
    scope: List[str]
    communities: List[GraphCommunity]

    def to_dict(self) -> Dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "algorithm": self.algorithm,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "scope": self.scope,
            "communities": [community.to_dict() for community in self.communities],
        }


@dataclass
class GraphSubgraph:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: Dict[Tuple[str, str, str, str | None], GraphEdge] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, List[Dict[str, object]]]:
        return {
            "nodes": [
                {"id": node.id, "type": node.type, "properties": dict(node.properties)}
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "properties": dict(edge.properties),
                }
                for edge in self.edges.values()
            ],
        }

    def document_ids(self) -> Set[str]:
        documents: Set[str] = set()
        for edge in self.edges.values():
            doc_raw = edge.properties.get("doc_id")
            if doc_raw is None:
                continue
            documents.add(str(doc_raw))
        return documents


@dataclass(slots=True)
class GraphExecutionResult:
    question: str
    cypher: str
    prompt: str
    records: List[Dict[str, object]]
    summary: Dict[str, object]
    documents: List[str]
    evidence_nodes: List[Dict[str, object]]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "question": self.question,
            "cypher": self.cypher,
            "prompt": self.prompt,
            "records": [dict(record) for record in self.records],
            "summary": dict(self.summary),
            "documents": list(self.documents),
            "evidence_nodes": [dict(node) for node in self.evidence_nodes],
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "GraphExecutionResult":
        question = str(payload.get("question", ""))
        cypher = str(payload.get("cypher", ""))
        prompt = str(payload.get("prompt", ""))
        records_raw = payload.get("records", [])
        summary_raw = payload.get("summary", {})
        documents_raw = payload.get("documents", [])
        evidence_raw = payload.get("evidence_nodes", [])
        warnings_raw = payload.get("warnings", [])
        records = [dict(record) for record in records_raw if isinstance(record, dict)]
        summary = dict(summary_raw) if isinstance(summary_raw, dict) else {}
        documents = [str(doc) for doc in documents_raw if doc is not None]
        evidence_nodes = [dict(node) for node in evidence_raw if isinstance(node, dict)]
        warnings = [str(item) for item in warnings_raw if item is not None]
        return cls(
            question=question,
            cypher=cypher,
            prompt=prompt,
            records=records,
            summary=summary,
            documents=documents,
            evidence_nodes=evidence_nodes,
            warnings=warnings,
        )


@dataclass(slots=True)
class GraphTextToCypherResult:
    question: str
    prompt: str
    cypher: str
    used_generator: bool
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "question": self.question,
            "prompt": self.prompt,
            "cypher": self.cypher,
            "used_generator": self.used_generator,
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class GraphArgumentLink:
    node: Dict[str, object]
    relation: str
    stance: Literal["support", "contradiction", "neutral"]
    documents: List[str]
    weight: float | None = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "node": dict(self.node),
            "relation": self.relation,
            "stance": self.stance,
            "documents": list(self.documents),
        }
        if self.weight is not None:
            payload["weight"] = self.weight
        return payload


@dataclass(slots=True)
class GraphArgumentEntry:
    node: Dict[str, object]
    supporting: List[GraphArgumentLink] = field(default_factory=list)
    opposing: List[GraphArgumentLink] = field(default_factory=list)
    neutral: List[GraphArgumentLink] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "node": dict(self.node),
            "supporting": [item.to_dict() for item in self.supporting],
            "opposing": [item.to_dict() for item in self.opposing],
            "neutral": [item.to_dict() for item in self.neutral],
            "documents": list(self.documents),
        }


@dataclass(slots=True)
class GraphContradiction:
    source: Dict[str, object]
    target: Dict[str, object]
    relation: str
    documents: List[str]
    weight: float | None = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "source": dict(self.source),
            "target": dict(self.target),
            "relation": self.relation,
            "documents": list(self.documents),
        }
        if self.weight is not None:
            payload["weight"] = self.weight
        return payload


@dataclass(slots=True)
class GraphLeveragePoint:
    node: Dict[str, object]
    influence: float
    connections: int
    documents: List[str]
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "node": dict(self.node),
            "influence": self.influence,
            "connections": self.connections,
            "documents": list(self.documents),
            "reason": self.reason,
        }


@dataclass(slots=True)
class GraphStrategyBrief:
    generated_at: str
    summary: str
    focus_nodes: List[Dict[str, object]]
    argument_map: List[GraphArgumentEntry]
    contradictions: List[GraphContradiction]
    leverage_points: List[GraphLeveragePoint]

    def to_dict(self) -> Dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "summary": self.summary,
            "focus_nodes": [dict(node) for node in self.focus_nodes],
            "argument_map": [entry.to_dict() for entry in self.argument_map],
            "contradictions": [item.to_dict() for item in self.contradictions],
            "leverage_points": [item.to_dict() for item in self.leverage_points],
        }


class GraphService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.mode = "neo4j" if self.settings.neo4j_uri != "memory://" else "memory"
        self._property_graph = self._create_property_graph_store()
        template_attr = getattr(self._property_graph, "text_to_cypher_template", None)
        self._text_to_cypher_template = (
            template_attr.template  # type: ignore[attr-defined]
            if hasattr(template_attr, "template")
            else str(template_attr or _FallbackSimplePropertyGraphStore.text_to_cypher_template)
        )
        self._knowledge_index: Any | None = None
        self._node_cache: Dict[str, GraphNode] = {}
        self._edge_cache: Dict[Tuple[str, str, str, str | None], GraphEdge] = {}
        self._community_cache: GraphCommunitySummary | None = None
        self._strategy_cache: GraphStrategyBrief | None = None
        self._nx_graph = nx.DiGraph() if nx is not None else None
        if self.mode == "neo4j":
            try:
                self.driver = GraphDatabase.driver(
                    self.settings.neo4j_uri,
                    auth=(self.settings.neo4j_user, self.settings.neo4j_password),
                )
            except ModuleNotFoundError:
                self.mode = "memory"
                self._nodes = {}
                self._edges = {}
            else:
                self._ensure_constraints()
                self._seed_ontology()
        if self.mode == "memory":
            self._nodes: Dict[str, GraphNode] = {}
            self._edges: Dict[Tuple[str, str, str, str | None], GraphEdge] = {}
            self._seed_ontology()
        if KnowledgeGraphIndex is not None and StorageContext is not None:
            try:
                self.ensure_knowledge_index()
            except (RuntimeError, ValueError):  # pragma: no cover - dependencies missing or API key issues
                pass

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
        root_id, root_type, root_props = classes[0]
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
                            root_id=root_id,
                            root_name=root_props["name"],
                            child_id=cid,
                            child_name=cname,
                            child_type=ctype,
                        )
                    )
        else:
            self._nodes.setdefault(root_id, GraphNode(id=root_id, type=root_type, properties=root_props))
        self._register_node(root_id, root_type, root_props)
        for child_id, child_type, properties in classes[1:]:
            if self.mode == "memory":
                self._nodes.setdefault(child_id, GraphNode(id=child_id, type=child_type, properties=properties))
            self._register_node(child_id, child_type, properties)
            relation = GraphEdge(
                source=root_id,
                target=child_id,
                type="ONTOLOGY_CHILD",
                properties={},
            )
            if self.mode == "memory":
                key = (root_id, "ONTOLOGY_CHILD", child_id, None)
                self._edges.setdefault(key, relation)
            self._record_edge(relation)

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
        self._register_node(doc_id, "Document", {"title": title, **metadata})

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
        self._register_node(entity_id, entity_type, properties)

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
        key = self._edge_key(source_id, relation_type, target_id, properties)
        if self.mode == "memory":
            existing = self._edges.get(key)
            if existing:
                merged_props = self._merge_properties(existing.properties, properties)
                edge = GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relation_type,
                    properties=merged_props,
                )
            else:
                edge = GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relation_type,
                    properties=properties,
                )
            self._edges[key] = edge
        else:
            existing = self._edge_cache.get(key)
            if existing:
                merged_props = self._merge_properties(existing.properties, properties)
                edge = GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relation_type,
                    properties=merged_props,
                )
            else:
                edge = GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=relation_type,
                    properties=properties,
                )
        source_node = self._node_cache.get(source_id)
        if source_node is None and self.mode == "memory":
            source_node = self._nodes.get(source_id)
        target_node = self._node_cache.get(target_id)
        if target_node is None and self.mode == "memory":
            target_node = self._nodes.get(target_id)
        self._register_node(
            source_id,
            source_node.type if source_node else "Unknown",
            source_node.properties if source_node else {},
        )
        self._register_node(
            target_id,
            target_node.type if target_node else "Unknown",
            target_node.properties if target_node else {},
        )
        self._record_edge(edge)

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
                    graph_node = GraphNode(
                        id=node["id"],
                        type=next(iter(node.labels)) if node.labels else "Unknown",
                        properties=dict(node),
                    )
                    nodes[graph_node.id] = graph_node
                    self._register_node(graph_node.id, graph_node.type, graph_node.properties)
                rel = record["r"]
                edge = GraphEdge(
                    source=rel.start_node["id"],
                    target=rel.end_node["id"],
                    type=rel.type,
                    properties=dict(rel),
                )
                edges.append(edge)
                self._record_edge(edge)
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
            self._record_edge(edge)
        return list(neighbor_nodes.values()), edges

    def subgraph(self, node_ids: Iterable[str]) -> GraphSubgraph:
        unique_ids = list(dict.fromkeys(node_ids))
        if not unique_ids:
            return GraphSubgraph()
        aggregated_nodes: Dict[str, GraphNode] = {}
        aggregated_edges: Dict[Tuple[str, str, str, str | None], GraphEdge] = {}
        for node_id in unique_ids:
            try:
                node_list, edge_list = self.neighbors(node_id)
            except KeyError:
                continue
            for node in node_list:
                aggregated_nodes[node.id] = node
            for edge in edge_list:
                key = self._edge_key(edge.source, edge.type, edge.target, edge.properties)
                existing = aggregated_edges.get(key)
                if existing is None:
                    aggregated_edges[key] = edge
                else:
                    merged = self._merge_properties(existing.properties, edge.properties)
                    aggregated_edges[key] = GraphEdge(
                        source=edge.source,
                        target=edge.target,
                        type=edge.type,
                        properties=merged,
                    )
        return GraphSubgraph(nodes=aggregated_nodes, edges=aggregated_edges)

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

    def get_property_graph_store(self) -> Any:
        return self._property_graph

    def ensure_knowledge_index(self, nodes: Sequence[Any] | None = None) -> Any:
        if KnowledgeGraphIndex is None or StorageContext is None:
            raise RuntimeError(
                "llama-index core packages are not installed; knowledge index is unavailable"
            )
        if self._knowledge_index is None:
            # Configure LLM for knowledge graph - use OpenAI if API key is available
            llm = None
            try:
                import os
                from llama_index.llms.openai import OpenAI
                openai_key = os.getenv("OPENAI_API_KEY") or self.settings.gemini_api_key
                if openai_key:
                    llm = OpenAI(api_key=openai_key, model="gpt-3.5-turbo")
            except Exception:
                pass  # Fall back to no LLM if configuration fails
            
            storage_context = StorageContext.from_defaults(graph_store=self._property_graph)
            self._knowledge_index = KnowledgeGraphIndex(
                nodes=list(nodes) if nodes else None,
                storage_context=storage_context,
                include_embeddings=True,
                llm=llm,
            )
        elif nodes:
            try:
                self._property_graph.upsert_llama_nodes(list(nodes))
            except AttributeError:  # pragma: no cover - fallback store
                pass
        return self._knowledge_index

    def get_knowledge_index(self) -> Any:
        return self.ensure_knowledge_index()

    def compute_community_summary(
        self, focus_nodes: Iterable[str] | None = None
    ) -> GraphCommunitySummary:
        focus_set = set(focus_nodes or [])
        if self._nx_graph is not None and self._nx_graph.number_of_nodes() > 0:
            graph = self._nx_graph.copy()
            if focus_set:
                relevant = {node for node in focus_set if node in graph}
                if relevant:
                    sub_nodes = set(relevant)
                    for node in relevant:
                        sub_nodes.update(graph.successors(node))
                        sub_nodes.update(graph.predecessors(node))
                    graph = graph.subgraph(sub_nodes).copy()
            scope_nodes = sorted(graph.nodes())
            algorithm = "greedy_modularity"
            communities: List[Set[str]] = []
            if graph.number_of_nodes() == 0:
                communities = []
            else:
                undirected = graph.to_undirected()
                try:
                    raw = nx.algorithms.community.greedy_modularity_communities(undirected)
                    communities = [set(comm) for comm in raw]
                except Exception:  # pragma: no cover - fallback path
                    algorithm = "label_propagation"
                    communities = [
                        set(comm)
                        for comm in nx.algorithms.community.label_propagation_communities(undirected)
                    ]
                if not communities:
                    communities = [set(graph.nodes())]
            summary = self._build_community_summary(graph, communities, algorithm, scope_nodes)
        else:
            nodes = set(self._node_cache.keys()) or {node.id for node in getattr(self, "_nodes", {}).values()}
            if focus_set:
                nodes &= focus_set or nodes
            edges = list(self._edge_cache.values())
            summary = GraphCommunitySummary(
                generated_at=datetime.now(timezone.utc).isoformat(),
                algorithm="fallback",
                total_nodes=len(nodes),
                total_edges=len(edges),
                scope=sorted(nodes),
                communities=[
                    GraphCommunity(
                        id="community::1",
                        size=len(nodes),
                        score=0.0,
                        nodes=[
                            self._graph_node_payload(
                                self._node_cache.get(node) or GraphNode(node, "Unknown", {})
                            )
                            for node in sorted(nodes)
                        ],
                        relations=[
                            {
                                "source": edge.source,
                                "target": edge.target,
                                "type": edge.type,
                                "label": str(
                                    edge.properties.get("predicate")
                                    or edge.properties.get("label")
                                    or edge.type
                                ),
                                "doc": str(edge.properties.get("doc_id"))
                                if edge.properties.get("doc_id") is not None
                                else None,
                            }
                            for edge in edges
                        ],
                        documents=sorted(
                            {
                                str(edge.properties.get("doc_id"))
                                for edge in edges
                                if edge.properties.get("doc_id") is not None
                            }
                        ),
                    )
                ]
                if nodes
                else [],
            )
        self._community_cache = summary
        return summary

    def get_community_summary(self) -> GraphCommunitySummary | None:
        return self._community_cache

    def communities_for_nodes(self, node_ids: Iterable[str]) -> List[GraphCommunity]:
        summary = self._community_cache or self.compute_community_summary()
        focus = set(node_ids)
        return [
            community
            for community in summary.communities
            if focus & {node["id"] for node in community.nodes}
        ]

    def describe_schema(self) -> str:
        node_types = sorted({node.type for node in self._node_cache.values()} or {"Unknown"})
        relation_types = sorted({edge.type for edge in self._edge_cache.values()})
        return (
            "Node types: "
            + ", ".join(node_types)
            + "\nRelation types: "
            + (", ".join(relation_types) if relation_types else "None")
        )

    def synthesize_strategy_brief(
        self, focus_nodes: Iterable[str] | None = None, *, limit: int = 5
    ) -> GraphStrategyBrief:
        now = datetime.now(timezone.utc).isoformat()
        if not self._node_cache:
            return GraphStrategyBrief(
                generated_at=now,
                summary="Strategy map unavailable: graph has no registered nodes.",
                focus_nodes=[],
                argument_map=[],
                contradictions=[],
                leverage_points=[],
            )

        focus_list = self._select_focus_nodes(focus_nodes, limit)
        focus_payload = [
            self._graph_node_payload(self._node_cache[node_id])
            for node_id in focus_list
            if node_id in self._node_cache
        ]

        contradiction_entries: List[GraphContradiction] = []
        for edge in self._edge_cache.values():
            stance = self._classify_relation(edge)
            if stance != "contradiction":
                continue
            source_node = self._node_cache.get(edge.source) or GraphNode(edge.source, "Unknown", {})
            target_node = self._node_cache.get(edge.target) or GraphNode(edge.target, "Unknown", {})
            contradiction_entries.append(
                GraphContradiction(
                    source=self._graph_node_payload(source_node),
                    target=self._graph_node_payload(target_node),
                    relation=str(edge.properties.get("predicate") or edge.type),
                    documents=self._extract_documents_from_edge(edge),
                    weight=self._coerce_float(edge.properties.get("weight")),
                )
            )

        argument_entries: List[GraphArgumentEntry] = []
        for node_id in focus_list:
            node = self._node_cache.get(node_id)
            if node is None:
                continue
            supporting: List[GraphArgumentLink] = []
            opposing: List[GraphArgumentLink] = []
            neutral: List[GraphArgumentLink] = []
            documents: Set[str] = set()
            for edge in self._edge_cache.values():
                if edge.source != node_id and edge.target != node_id:
                    continue
                other_id = edge.target if edge.source == node_id else edge.source
                other = self._node_cache.get(other_id) or GraphNode(other_id, "Unknown", {})
                relation_label = str(edge.properties.get("predicate") or edge.type)
                doc_ids = self._extract_documents_from_edge(edge)
                documents.update(doc_ids)
                stance = self._classify_relation(edge)
                link = GraphArgumentLink(
                    node=self._graph_node_payload(other),
                    relation=relation_label,
                    stance=stance,
                    documents=doc_ids,
                    weight=self._coerce_float(edge.properties.get("weight")),
                )
                if stance == "support":
                    supporting.append(link)
                elif stance == "contradiction":
                    opposing.append(link)
                else:
                    neutral.append(link)
            argument_entries.append(
                GraphArgumentEntry(
                    node=self._graph_node_payload(node),
                    supporting=supporting,
                    opposing=opposing,
                    neutral=neutral,
                    documents=sorted(documents),
                )
            )

        leverage_points: List[GraphLeveragePoint] = []
        degree_map = self._degree_map()
        centrality: Dict[str, float] = {}
        if self._nx_graph is not None and self._nx_graph.number_of_nodes() > 0:
            try:
                centrality = nx.algorithms.centrality.betweenness_centrality(
                    self._nx_graph, normalized=True
                )
            except Exception:  # pragma: no cover - fallback when analytics fails
                centrality = {node_id: 0.0 for node_id in self._nx_graph.nodes()}
        else:
            centrality = {node_id: 0.0 for node_id in degree_map}

        sorted_leverage = sorted(
            centrality.items(), key=lambda item: item[1], reverse=True
        )
        if not sorted_leverage:
            sorted_leverage = sorted(degree_map.items(), key=lambda item: item[1], reverse=True)
        elif all(score <= 0 for _, score in sorted_leverage):
            sorted_leverage = sorted(degree_map.items(), key=lambda item: item[1], reverse=True)

        for node_id, score in sorted_leverage[:limit]:
            node = self._node_cache.get(node_id)
            if node is None:
                continue
            docs = sorted(self._collect_documents_for_node(node_id))
            leverage_points.append(
                GraphLeveragePoint(
                    node=self._graph_node_payload(node),
                    influence=float(score),
                    connections=int(degree_map.get(node_id, 0)),
                    documents=docs,
                    reason=self._build_leverage_reason(
                        node, degree_map.get(node_id, 0), len(docs)
                    ),
                )
            )

        summary_parts = [
            f"{len(argument_entries)} argument focus node(s)",
            f"{len(contradiction_entries)} contradiction link(s)",
            f"{len(leverage_points)} leverage point(s)",
        ]
        if focus_list:
            focus_labels = ", ".join(
                self._node_display_name(self._node_cache.get(node_id))
                for node_id in focus_list
                if self._node_cache.get(node_id) is not None
            )
            summary_parts.append(f"focus: {focus_labels}")
        summary = "Strategy map synthesised with " + ", ".join(summary_parts) + "."

        brief = GraphStrategyBrief(
            generated_at=now,
            summary=summary,
            focus_nodes=focus_payload,
            argument_map=argument_entries,
            contradictions=contradiction_entries,
            leverage_points=leverage_points,
        )
        self._strategy_cache = brief
        return brief

    def build_text_to_cypher_prompt(self, question: str, schema: str | None = None) -> str:
        schema_text = schema or self.describe_schema()
        template = self._text_to_cypher_template or _FallbackSimplePropertyGraphStore.text_to_cypher_template
        if "{schema}" in template and "{question}" in template:
            return template.format(schema=schema_text, question=question)
        return f"Schema:\n{schema_text}\nQuestion: {question}\nCypher:"

    def text_to_cypher(
        self, question: str, *, schema: str | None = None
    ) -> GraphTextToCypherResult:
        question_text = question.strip()
        if not question_text:
            raise ValueError("Question must not be empty for text-to-Cypher generation")
        prompt = self.build_text_to_cypher_prompt(question_text, schema)
        generator = getattr(self._property_graph, "text_to_cypher", None)
        warnings: List[str] = []
        cypher = ""
        used_generator = False
        if callable(generator):
            schema_text = schema or self.describe_schema()
            try:
                try:
                    raw = generator(question_text, schema=schema_text)
                except TypeError:
                    raw = generator(question_text)
            except Exception as exc:  # pragma: no cover - defensive guard
                warnings.append(f"text_to_cypher invocation failed: {exc}")
            else:
                used_generator = True
                if isinstance(raw, str):
                    cypher = raw.strip()
                elif isinstance(raw, dict):
                    cypher = str(raw.get("cypher", "")).strip()
                    prompt_override = raw.get("prompt")
                    if isinstance(prompt_override, str) and prompt_override.strip():
                        prompt = prompt_override.strip()
                else:
                    cypher_attr = getattr(raw, "cypher", None)
                    if cypher_attr is not None:
                        cypher = str(cypher_attr).strip()
                    prompt_attr = getattr(raw, "prompt", None)
                    if isinstance(prompt_attr, str) and prompt_attr.strip():
                        prompt = prompt_attr.strip()
        return GraphTextToCypherResult(
            question=question_text,
            prompt=prompt,
            cypher=cypher,
            used_generator=used_generator,
            warnings=warnings,
        )

    def execute_agent_cypher(
        self,
        question: str,
        cypher: str,
        *,
        parameters: Dict[str, object] | None = None,
        sandbox: bool = True,
        limit: int = 50,
        prompt: str | None = None,
    ) -> GraphExecutionResult:
        question_text = question.strip()
        if not question_text:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_EMPTY_QUESTION",
                    message="Graph question must not be empty",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                ),
                status_code=400,
            )
        raw_query = cypher.strip()
        if not raw_query:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_EMPTY_CYPHER",
                    message="Graph agent produced an empty Cypher statement",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                ),
                status_code=400,
            )
        sanitized = self._sanitize_agent_cypher(raw_query)
        prompt_info = self.text_to_cypher(question_text)
        warnings: List[str] = list(prompt_info.warnings)
        if sandbox:
            enforced, added_limit = self._enforce_limit_clause(sanitized, limit=limit)
            sanitized = enforced
            if added_limit:
                warnings.append(f"LIMIT {limit} appended for sandbox execution")
        try:
            execution = self.run_cypher(sanitized, parameters or {})
        except ValueError as exc:  # pragma: no cover - defensive guard for unsupported queries
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_UNSUPPORTED_QUERY",
                    message=str(exc),
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"cypher": sanitized},
                ),
                status_code=400,
            ) from exc
        records = execution.get("records", [])
        documents, evidence_nodes = self._collect_documents(records)
        summary = {
            "question": question_text,
            "record_count": len(records),
            "document_count": len(documents),
            "mode": execution.get("summary", {}).get("mode", self.mode),
            "insight": self._summarise_execution(question_text, documents, len(records)),
        }
        summary.update(execution.get("summary", {}))
        result = GraphExecutionResult(
            question=question_text,
            cypher=sanitized,
            prompt=prompt or prompt_info.prompt,
            records=[dict(record) for record in records],
            summary=summary,
            documents=documents,
            evidence_nodes=evidence_nodes,
            warnings=warnings,
        )
        return result

    def run_cypher(
        self, query: str, parameters: Dict[str, object] | None = None
    ) -> Dict[str, object]:
        parameters = parameters or {}
        if self.mode == "neo4j":
            with self.driver.session() as session:
                records = session.execute_read(lambda tx: list(tx.run(query, **parameters)))
            normalised = [self._normalise_cypher_record(record) for record in records]
            return {
                "records": normalised,
                "summary": {"mode": "neo4j", "count": len(normalised)},
            }
        return self._run_cypher_memory(query, parameters)

    # region helpers
    def _build_community_summary(
        self,
        graph: Any,
        communities: Sequence[Set[str]],
        algorithm: str,
        scope_nodes: Sequence[str],
    ) -> GraphCommunitySummary:
        payload: List[GraphCommunity] = []
        for index, members in enumerate(communities, start=1):
            member_nodes = [
                self._graph_node_payload(
                    self._node_cache.get(node_id) or GraphNode(node_id, "Unknown", {})
                )
                for node_id in sorted(members)
            ]
            relation_entries: Dict[Tuple[str, str, str, str | None], Dict[str, object]] = {}
            documents: Set[str] = set()
            for edge in self._edge_cache.values():
                if edge.source in members and edge.target in members:
                    doc_raw = edge.properties.get("doc_id")
                    if doc_raw is not None:
                        documents.add(str(doc_raw))
                    key = self._edge_key(edge.source, edge.type, edge.target, edge.properties)
                    relation_entries[key] = {
                        "source": edge.source,
                        "target": edge.target,
                        "type": edge.type,
                        "label": str(
                            edge.properties.get("predicate")
                            or edge.properties.get("label")
                            or edge.type
                        ),
                        "doc": str(doc_raw) if doc_raw is not None else None,
                    }
            relation_list = list(relation_entries.values())
            size = len(members)
            density = 0.0
            if size > 1:
                density = round(len(relation_list) / (size * (size - 1)), 3)
            payload.append(
                GraphCommunity(
                    id=f"community::{index}",
                    size=size,
                    score=density,
                    nodes=member_nodes,
                    relations=relation_list,
                    documents=sorted(documents),
                )
            )
        return GraphCommunitySummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            algorithm=algorithm,
            total_nodes=graph.number_of_nodes() if hasattr(graph, "number_of_nodes") else len(scope_nodes),
            total_edges=graph.number_of_edges() if hasattr(graph, "number_of_edges") else len(self._edge_cache),
            scope=list(scope_nodes),
            communities=payload,
        )

    def _run_cypher_memory(
        self, query: str, parameters: Dict[str, object]
    ) -> Dict[str, object]:
        text = query.strip()
        lowered = re.sub(r"\s+", " ", text.lower())
        lowered = re.sub(r" limit \d+;?", "", lowered).strip()
        lowered = lowered.rstrip(";")
        records: List[Dict[str, object]] = []
        node_match = re.match(
            r"match\s*\(\s*([a-z])(?:\s*:\s*[A-Za-z][A-Za-z0-9_]*)?\s*(?:\{\s*id\s*:\s*'([^']+)'\s*\})?\s*\)\s*return",
            lowered,
        )
        edge_match = re.match(
            r"match\s*\(\s*([a-z])(?:\s*:\s*[A-Za-z][A-Za-z0-9_]*)?\s*\)-\s*\[([a-z])[^]]*\]\s*->\s*\(\s*([a-z])(?:\s*:\s*[A-Za-z][A-Za-z0-9_]*)?\s*\)\s*return",
            lowered,
        )
        if node_match and not edge_match:
            node_id = node_match.group(2)
            if node_id:
                node = self._node_cache.get(node_id) or getattr(self, "_nodes", {}).get(node_id)
                if node:
                    records.append({"n": self._graph_node_payload(node)})
            else:
                for node in self._node_cache.values():
                    records.append({"n": self._graph_node_payload(node)})
        elif edge_match:
            for edge in self._edge_cache.values():
                source = self._node_cache.get(edge.source) or GraphNode(edge.source, "Unknown", {})
                target = self._node_cache.get(edge.target) or GraphNode(edge.target, "Unknown", {})
                records.append(
                    {
                        "source": self._graph_node_payload(source),
                        "relation": {
                            "type": edge.type,
                            "properties": dict(edge.properties),
                        },
                        "target": self._graph_node_payload(target),
                    }
                )
        else:
            raise ValueError("Unsupported Cypher query for in-memory graph backend")
        return {"records": records, "summary": {"mode": "memory", "count": len(records), "query": query}}

    def _graph_node_payload(self, node: GraphNode) -> Dict[str, object]:
        return {"id": node.id, "type": node.type, "properties": dict(node.properties)}

    def _select_focus_nodes(
        self, focus_nodes: Iterable[str] | None, limit: int
    ) -> List[str]:
        ordered: List[str] = []
        if focus_nodes:
            for candidate in focus_nodes:
                if candidate in self._node_cache and candidate not in ordered:
                    ordered.append(candidate)
                elif candidate in getattr(self, "_nodes", {}) and candidate not in ordered:
                    ordered.append(candidate)
        if not ordered:
            ordered = [node_id for node_id, _ in self._default_focus_nodes(limit)]
        return ordered[:limit]

    def _default_focus_nodes(self, limit: int) -> List[Tuple[str, int]]:
        if self._nx_graph is not None and self._nx_graph.number_of_nodes() > 0:
            degree_sequence = list(self._nx_graph.degree())
            sorted_nodes = sorted(degree_sequence, key=lambda item: item[1], reverse=True)
            return sorted_nodes[:limit]
        degree_map = self._degree_map()
        return sorted(degree_map.items(), key=lambda item: item[1], reverse=True)[:limit]

    def _degree_map(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for edge in self._edge_cache.values():
            counts[edge.source] = counts.get(edge.source, 0) + 1
            counts[edge.target] = counts.get(edge.target, 0) + 1
        if not counts and hasattr(self, "_nodes"):
            for node_id in getattr(self, "_nodes").keys():
                counts.setdefault(node_id, 0)
        return counts

    def _collect_documents_for_node(self, node_id: str) -> Set[str]:
        documents: Set[str] = set()
        for edge in self._edge_cache.values():
            if edge.source == node_id or edge.target == node_id:
                documents.update(self._extract_documents_from_edge(edge))
        return documents

    def _build_leverage_reason(
        self, node: GraphNode, connections: int, document_count: int
    ) -> str:
        label = self._node_display_name(node)
        fragments: List[str] = []
        if connections:
            fragments.append(f"connected to {connections} node(s)")
        if document_count:
            fragments.append(f"linked to {document_count} document(s)")
        if not fragments:
            fragments.append("currently lightly connected")
        return f"{label} is {', '.join(fragments)}."

    def _node_display_name(self, node: GraphNode | None) -> str:
        if node is None:
            return "unknown node"
        for key in ("label", "title", "name"):
            raw = node.properties.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return node.id

    def _extract_documents_from_edge(self, edge: GraphEdge) -> List[str]:
        documents: Set[str] = set()
        doc_value = edge.properties.get("doc_id")
        if isinstance(doc_value, (list, tuple, set)):
            documents.update(str(item) for item in doc_value if item is not None)
        elif doc_value is not None:
            documents.add(str(doc_value))
        evidence = edge.properties.get("evidence")
        if isinstance(evidence, (list, tuple, set)):
            documents.update(str(item) for item in evidence if item is not None)
        elif isinstance(evidence, dict):
            doc_id = evidence.get("doc_id")
            if doc_id is not None:
                documents.add(str(doc_id))
        elif isinstance(evidence, str):
            documents.add(evidence)
        return sorted(documents)

    def _classify_relation(self, edge: GraphEdge) -> Literal["support", "contradiction", "neutral"]:
        stance_raw = edge.properties.get("stance")
        if isinstance(stance_raw, str):
            lowered = stance_raw.lower()
            if lowered in {"support", "supports", "pro", "favorable", "corroborates"}:
                return "support"
            if lowered in {"against", "oppose", "opposes", "refute", "contradict", "challenge", "con"}:
                return "contradiction"
        predicate = str(edge.properties.get("predicate") or edge.type).lower()
        if any(keyword in predicate for keyword in ["contradict", "refute", "disput", "oppose", "challenge", "deny"]):
            return "contradiction"
        if any(keyword in predicate for keyword in ["support", "corrobor", "confirm", "sustain", "align"]):
            return "support"
        sentiment = edge.properties.get("sentiment")
        if isinstance(sentiment, str):
            lowered = sentiment.lower()
            if lowered in {"positive", "favorable"}:
                return "support"
            if lowered in {"negative", "unfavorable"}:
                return "contradiction"
        weight = self._coerce_float(edge.properties.get("weight"))
        if weight is not None and weight < 0:
            return "contradiction"
        return "neutral"

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _register_node(self, node_id: str, node_type: str, properties: Dict[str, object]) -> None:
        existing = self._node_cache.get(node_id)
        merged_props = {**(existing.properties if existing else {}), **properties}
        resolved_type = node_type if node_type != "Unknown" else (existing.type if existing else node_type)
        node = GraphNode(id=node_id, type=resolved_type, properties=merged_props)
        self._node_cache[node_id] = node
        self._strategy_cache = None
        if self._property_graph is not None:
            try:
                property_node = self._create_property_node(node)
                self._property_graph.upsert_nodes([property_node])
                self._sync_knowledge_index([property_node])
            except Exception:  # pragma: no cover - defensive fallback
                pass
        if self._nx_graph is not None:
            self._nx_graph.add_node(node_id, type=node.type, properties=dict(node.properties))

    def _record_edge(self, edge: GraphEdge) -> None:
        key = self._edge_key(edge.source, edge.type, edge.target, edge.properties)
        self._edge_cache[key] = edge
        self._strategy_cache = None
        if self._property_graph is not None:
            try:
                source_node = self._node_cache.get(edge.source)
                target_node = self._node_cache.get(edge.target)
                nodes_to_upsert = []
                if source_node:
                    nodes_to_upsert.append(self._create_property_node(source_node))
                if target_node:
                    nodes_to_upsert.append(self._create_property_node(target_node))
                if nodes_to_upsert:
                    self._property_graph.upsert_nodes(nodes_to_upsert)
                    self._sync_knowledge_index(nodes_to_upsert)
                self._property_graph.upsert_relations([self._create_property_relation(edge)])
            except Exception:  # pragma: no cover - defensive fallback
                pass
        if self._nx_graph is not None:
            self._nx_graph.add_edge(
                edge.source,
                edge.target,
                **{"type": edge.type, "properties": dict(edge.properties)},
            )

    def _create_property_graph_store(self) -> Any:
        if self.mode == "neo4j" and _LlamaNeo4jPropertyGraphStore is not None:
            try:
                return _LlamaNeo4jPropertyGraphStore(
                    url=self.settings.neo4j_uri,
                    username=self.settings.neo4j_user,
                    password=self.settings.neo4j_password,
                )
            except Exception:  # pragma: no cover - fallback to in-memory store
                pass
        if _LlamaSimplePropertyGraphStore is not None:
            try:
                return _LlamaSimplePropertyGraphStore()
            except Exception:  # pragma: no cover - fallback to stub
                pass
        return _FallbackSimplePropertyGraphStore()

    def _create_property_node(self, node: GraphNode) -> Any:
        label = node.properties.get("type") or node.type or "Entity"
        if _LlamaEntityNode is not None and _LlamaLabelledNode is not None:
            return _LlamaEntityNode(name=node.id, label=label, properties=dict(node.properties))
        return _FallbackLabelledNode(name=node.id, label=label, properties=dict(node.properties))

    def _create_property_relation(self, edge: GraphEdge) -> Any:
        return _RelationFactory(
            label=edge.type,
            source_id=edge.source,
            target_id=edge.target,
            properties=dict(edge.properties),
        )

    def _graph_edge_payload(self, edge: GraphEdge) -> Dict[str, object]:
        return {
            "source": edge.source,
            "target": edge.target,
            "type": edge.type,
            "properties": dict(edge.properties),
        }

    def _sync_knowledge_index(self, nodes: Sequence[Any]) -> None:
        if not nodes:
            return
        if KnowledgeGraphIndex is None or StorageContext is None:
            return
        try:
            if self._knowledge_index is None:
                self.ensure_knowledge_index(nodes)
            else:
                try:
                    self._property_graph.upsert_llama_nodes(list(nodes))
                except AttributeError:  # pragma: no cover - fallback store
                    pass
        except RuntimeError:  # pragma: no cover - optional dependency missing
            return

    def _normalise_cypher_record(self, record: Any) -> Dict[str, object]:
        payload: Dict[str, object] = {}
        for key in record.keys():
            payload[key] = self._normalise_cypher_value(record[key])
        return payload

    def _normalise_cypher_value(self, value: Any) -> Any:
        if hasattr(value, "labels") and hasattr(value, "items"):
            data = dict(value)
            data.setdefault("id", value.get("id"))  # type: ignore[attr-defined]
            data.setdefault("labels", list(value.labels))  # type: ignore[attr-defined]
            return data
        if hasattr(value, "type") and hasattr(value, "items"):
            data = dict(value)
            data.setdefault("type", value.type)
            data.setdefault("start", value.start_node["id"])  # type: ignore[attr-defined]
            data.setdefault("end", value.end_node["id"])  # type: ignore[attr-defined]
            return data
        if isinstance(value, list):
            return [self._normalise_cypher_value(item) for item in value]
        return value

    # endregion

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

    def _sanitize_agent_cypher(self, query: str) -> str:
        cleaned = query.strip()
        cleaned = re.sub(r"```(?:cypher)?", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        forbidden = [
            "call ",
            "create ",
            "delete ",
            "remove ",
            "merge ",
            "drop ",
            "load ",
            "apoc",
            "set ",
        ]
        lowered = cleaned.lower()
        if not lowered.startswith("match"):
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_UNSAFE_QUERY",
                    message="Agent-generated Cypher must begin with MATCH",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"cypher": query},
                ),
                status_code=400,
            )
        for keyword in forbidden:
            if keyword in lowered:
                raise WorkflowAbort(
                    WorkflowError(
                        component=WorkflowComponent.GRAPH,
                        code="GRAPH_FORBIDDEN_KEYWORD",
                        message=f"Cypher contains forbidden keyword: {keyword.strip()}",
                        severity=WorkflowSeverity.ERROR,
                        retryable=False,
                        context={"cypher": query},
                    ),
                    status_code=400,
                )
        if "return" not in lowered:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_RETURN_REQUIRED",
                    message="Cypher must include a RETURN clause",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"cypher": query},
                ),
                status_code=400,
            )
        return cleaned.rstrip(";")

    @staticmethod
    def _enforce_limit_clause(query: str, *, limit: int) -> Tuple[str, bool]:
        if re.search(r"limit\s+\d+", query, flags=re.IGNORECASE):
            return query, False
        trimmed = query.rstrip(";")
        return f"{trimmed} LIMIT {limit}", True

    def _collect_documents(
        self, records: Iterable[Dict[str, object]]
    ) -> Tuple[List[str], List[Dict[str, object]]]:
        documents: Dict[str, str] = {}
        evidence_nodes: Dict[str, Dict[str, object]] = {}

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                if {"id", "type", "properties"}.issubset(value.keys()):
                    node_id = str(value.get("id"))
                    node_type = str(value.get("type", ""))
                    properties = value.get("properties", {})
                    if isinstance(properties, dict):
                        doc_id = properties.get("doc_id")
                        if doc_id is not None:
                            documents[str(doc_id)] = str(doc_id)
                        label = properties.get("label") or node_type or node_id
                    else:
                        label = node_type or node_id
                    if node_type.lower() == "document":
                        documents[node_id] = node_id
                    payload = {
                        "id": node_id,
                        "type": node_type,
                        "label": str(label),
                        "properties": dict(properties) if isinstance(properties, dict) else {},
                    }
                    evidence_nodes[node_id] = payload
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        for record in records:
            visit(record)

        return sorted(documents.keys()), list(evidence_nodes.values())

    @staticmethod
    def _summarise_execution(question: str, documents: List[str], record_count: int) -> str:
        doc_text = "no linked documents" if not documents else f"{len(documents)} linked document(s)"
        return (
            f"Graph query answering '{question}' returned {record_count} record(s) with {doc_text}."
        )

    def get_document_neighborhood(self, case_id: str, doc_id: str, hops: int = 1) -> Dict[str, Any]:
        """
        Retrieves the immediate graph neighborhood of a document.
        Returns nodes and edges.
        """
        if self.mode != "neo4j":
            return {"nodes": [], "edges": []}

        query = f"""
        MATCH (d:Document {{id: $doc_id}})
        CALL apoc.path.subgraphAll(d, {{
            maxLevel: $hops,
            relationshipFilter: "CITES|MENTIONS|SIMILAR_TO|HAS_ENTITY",
            labelFilter: "+Document|Entity"
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        
        try:
            with self._driver.session() as session:
                result = session.run(query, doc_id=doc_id, hops=hops)
                record = result.single()
                if not record:
                    return {"nodes": [], "edges": []}
                
                nodes = []
                for node in record["nodes"]:
                    nodes.append({
                        "id": node["id"],
                        "label": list(node.labels)[0] if node.labels else "Unknown",
                        "properties": dict(node)
                    })
                
                edges = []
                for rel in record["relationships"]:
                    edges.append({
                        "source": rel.start_node["id"],
                        "target": rel.end_node["id"],
                        "type": rel.type,
                        "properties": dict(rel)
                    })
                
                return {"nodes": nodes, "edges": edges}
        except Exception as e:
            # logger.error(f"Failed to get document neighborhood: {e}")
            return {"nodes": [], "edges": []}

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

