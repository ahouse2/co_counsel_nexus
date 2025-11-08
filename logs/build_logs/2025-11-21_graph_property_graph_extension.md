# 2025-11-21 — Graph Property Graph Extension

## Summary
- Wired `GraphService` to instantiate LlamaIndex-compatible property graph stores (Neo4j-aware) and lazily initialise `KnowledgeGraphIndex`.
- Synced node/edge registrations into the property graph + knowledge index, exposing a `get_knowledge_index()` helper.
- Extended retrieval traces/tests to assert subgraph payload fidelity (nodes, relations, timeline events, communities).
- Documented knowledge index integration within roadmap + PRP artefacts.

## Validation
- pytest backend/tests/test_graph_service.py
- pytest backend/tests/test_retrieval.py

## Notes
- LlamaIndex optional dependency remains absent in CI; runtime gracefully raises `RuntimeError` when unavailable, covered by tests.
- Neo4j property graph store import guarded for deployments without the addon package.
