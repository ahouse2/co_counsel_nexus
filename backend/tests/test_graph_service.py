from __future__ import annotations

import pytest

from backend.app import config
from backend.app.services import graph as graph_module


@pytest.fixture()
def memory_graph(monkeypatch: pytest.MonkeyPatch) -> graph_module.GraphService:
    monkeypatch.setenv("NEO4J_URI", "memory://")
    config.reset_settings_cache()
    graph_module.reset_graph_service()
    service = graph_module.GraphService()
    return service


def test_merge_relation_merges_evidence(memory_graph: graph_module.GraphService) -> None:
    service = memory_graph
    service.upsert_document("doc-1", "Agreement", {"case": "alpha"})
    service.upsert_entity("entity-1", "Entity", {"label": "Acme"})
    service.merge_relation("doc-1", "MENTIONS", "entity-1", {"doc_id": "doc-1", "evidence": ["page-1"]})
    service.merge_relation(
        "doc-1",
        "MENTIONS",
        "entity-1",
        {"doc_id": "doc-1", "weight": 0.75, "evidence": "page-2"},
    )

    nodes, edges = service.neighbors("doc-1")
    node_ids = {node.id for node in nodes}
    assert node_ids == {"doc-1", "entity-1"}
    assert len(edges) == 1
    edge = edges[0]
    assert edge.source == "doc-1"
    assert edge.properties["doc_id"] == "doc-1"
    assert set(edge.properties["evidence"]) == {"page-1", "page-2"}
    assert edge.properties["weight"] == 0.75

    mapping = service.document_entities(["doc-1", "missing"])
    assert {node.id for node in mapping["doc-1"]} == {"entity-1"}
    assert mapping["missing"] == []


def test_neighbors_missing_node_raises(memory_graph: graph_module.GraphService) -> None:
    with pytest.raises(KeyError):
        memory_graph.neighbors("unknown::id")


def test_search_entities_filters_types(memory_graph: graph_module.GraphService) -> None:
    service = memory_graph
    service.upsert_entity("entity-2", "Entity", {"label": "Beta Corp"})
    service.upsert_entity("other", "Evidence", {"label": "Ignore"})
    matches = service.search_entities("beta", limit=5)
    assert [node.id for node in matches] == ["entity-2"]
    assert service.search_entities("") == []


def test_edge_key_includes_doc_id(memory_graph: graph_module.GraphService) -> None:
    key = memory_graph._edge_key("doc-1", "REL", "entity-1", {"doc_id": "case-9"})
    assert key == ("doc-1", "REL", "entity-1", "case-9")


def test_merge_properties_handles_evidence_lists() -> None:
    existing = {"score": 0.5, "evidence": ["a"]}
    new_values = {"score": 0.9, "evidence": ["a", "b"]}
    merged = graph_module.GraphService._merge_properties(existing, new_values)
    assert merged["score"] == 0.9
    assert merged["evidence"] == ["a", "b"]

    appended = graph_module.GraphService._merge_properties(merged, {"evidence": "c"})
    assert appended["evidence"] == ["a", "b", "c"]


class _DummyNode(dict):
    def __init__(self, node_id: str, labels: list[str], props: dict[str, object]):
        super().__init__(props)
        self["id"] = node_id
        self.labels = labels


class _DummyRelationship(dict):
    def __init__(self, start: str, end: str, rel_type: str, props: dict[str, object]):
        super().__init__(props)
        self.start_node = {"id": start}
        self.end_node = {"id": end}
        self.type = rel_type


class _DummyRecord(dict):
    """Container mirroring neo4j Record interface for testing."""


class _DummyTx:
    def __init__(self, driver: "_DummyDriver", write: bool) -> None:
        self.driver = driver
        self.write = write

    def run(self, query: str, **params):
        if self.write:
            self.driver.write_calls.append((query, params))
            return []
        self.driver.read_calls.append((query, params))
        return self.driver.read_results.pop(0)


class _DummySession:
    def __init__(self, driver: "_DummyDriver") -> None:
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute_write(self, func):
        return func(_DummyTx(self.driver, write=True))

    def execute_read(self, func):
        return func(_DummyTx(self.driver, write=False))


class _DummyDriver:
    def __init__(self) -> None:
        self.write_calls: list[tuple[str, dict[str, object]]] = []
        self.read_calls: list[tuple[str, dict[str, object]]] = []
        self.read_results: list[list[dict[str, object]]] = []

    def session(self):
        return _DummySession(self)


class _DummyGraphDatabase:
    def __init__(self, driver: _DummyDriver) -> None:
        self._driver = driver

    def driver(self, uri: str, auth: tuple[str, str]):
        return self._driver


def test_graph_service_neo4j_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO4J_URI", "bolt://neo4j")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "pass")
    config.reset_settings_cache()
    dummy_driver = _DummyDriver()
    dummy_driver.read_results = [
        [_DummyRecord(
            n=_DummyNode("doc-9", ["Document"], {"title": "Doc"}),
            m=_DummyNode("entity-9", ["Entity"], {"label": "Acme"}),
            r=_DummyRelationship("doc-9", "entity-9", "MENTIONS", {"weight": 0.7}),
        )],
        [_DummyRecord(e=_DummyNode("entity-9", ["Entity"], {"label": "Acme"}))],
        [_DummyRecord(doc_id="doc-9", e=_DummyNode("entity-9", ["Entity"], {"label": "Acme"}))],
    ]
    monkeypatch.setattr(graph_module, "GraphDatabase", _DummyGraphDatabase(dummy_driver))
    graph_module.reset_graph_service()
    service = graph_module.GraphService()
    assert service.mode == "neo4j"

    service.upsert_document("doc-9", "Doc", {"status": "active"})
    service.upsert_entity("entity-9", "Entity", {"label": "Acme"})
    service.merge_relation("doc-9", "MENTIONS", "entity-9", {"doc_id": "doc-9", "evidence": ["page-3"]})

    nodes, edges = service.neighbors("doc-9")
    assert {node.id for node in nodes} == {"doc-9", "entity-9"}
    assert edges[0].properties["weight"] == 0.7

    matches = service.search_entities("acme", limit=5)
    assert matches[0].properties["label"] == "Acme"

    mapping = service.document_entities(["doc-9"])
    assert mapping["doc-9"][0].id == "entity-9"

    assert any("MERGE (d:Document" in call[0] for call in dummy_driver.write_calls)
    assert any("MATCH (d:Document)-[:MENTIONS]->(e:Entity)" in call[0] for call in dummy_driver.read_calls)
