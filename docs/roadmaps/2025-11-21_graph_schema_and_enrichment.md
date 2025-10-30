# 2025-11-21 · Graph Schema & Enrichment Procedures

## Ontology Overview
- **Core classes**
  - `Document` (properties: `title`, `origin`, `source_type`, `checksum_sha256`, `chunk_count`, etc.)
  - `Entity` (properties: `label`, `type`, `aliases`, optional embeddings)
  - `OntologyClass` (seeded taxonomy: Organization, Person, Location, Event)
- **Relations**
  - `MENTIONS` — Document → Entity with evidence metadata (`doc_id`, `label`, `type`, `evidence`)
  - `ONTOLOGY_CHILD` — OntologyRoot → OntologyClass
  - Case-specific predicates extracted from triples (e.g., `ASSOCIATED_WITH`, `EMPLOYED_BY`)

## Property Graph Backends
- Neo4j: accessed via transactional Cypher, mirrored into LlamaIndex `PropertyGraphStore` for KG tooling.
- In-memory: NetworkX-driven DiGraph with LlamaIndex SimplePropertyGraph fallback to remain operable offline.
- `GraphService.get_knowledge_index()` lazily initialises a LlamaIndex `KnowledgeGraphIndex` bound to the active store; node/edge
  registrations call `_sync_knowledge_index` so tooling such as text-to-Cypher and KG agents stay fresh without manual rebuilds.
- Graph service exposes `run_cypher`, `describe_schema`, and text-to-Cypher prompt scaffolding for agent workflows.
- `GraphService.text_to_cypher` wraps backend graph stores that implement automated NL → Cypher translation while preserving a
  safe fallback prompt (agents toolkit exposes this via `graph_explorer.text_to_cypher`).
- Unified subgraph export via `GraphService.subgraph` standardises node/edge payloads for retrieval traces and UI panes.

## Community Detection Pipeline
1. **Trigger**: invoked after each ingestion run (`IngestionService._refresh_timeline_enrichments`).
2. **Graph snapshot**: induced subgraph from mutated nodes (NetworkX greedy modularity; fallback to label propagation / singleton summary when NetworkX unavailable).
3. **Summary payload**: stored under `status_details.graph.communities` (id, members, relations, supporting documents, density score).
4. **Reuse**: surfaced in retrieval traces and agents toolkit (`community_overview`).

## Timeline Enrichment Update Flow
1. Persist raw events (`TimelineStore.append`).
2. Execute `TimelineService.refresh_enrichments()` to recompute highlights + relation tags using latest graph neighborhoods.
3. Capture enrichment stats in job manifest (`status_details.timeline`).
4. Retrieval traces filter timeline events by returned document ids, exposing highlights + relation tags to UI.

## Update Procedures
- **Schema evolution**
  - Extend ontology seeds in `GraphService._seed_ontology` with new classes.
  - Add node/edge registration logic to `_register_node` / `_record_edge` for downstream analytics.
- **Analytics tuning**
  - Adjust `compute_community_summary` thresholds (density calculation, algorithm fallback) as graph scale grows.
  - Extend timeline enrichment scoring via `TimelineService._compute_confidence`.
- **Documentation cadence**
  - When adding new relation types or ontology classes, update this roadmap and PRP schema appendix (see PRP update below).
