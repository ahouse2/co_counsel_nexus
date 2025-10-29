# Graph Knowledge Graph Integration & Timeline Enrichment Execution Plan

## Volume I · Foundation Survey
- ### Chapter 1 · Context Assimilation
  - #### Section 1.1 · Existing Graph Service Topology
    - ##### Paragraph 1.1.1 · Inventory current Node/Edge APIs
      - Extracted neighbor/search/document entity flows relying on ad-hoc in-memory/Neo4j logic.
    - ##### Paragraph 1.1.2 · Assess ingestion + retrieval touchpoints
      - Identified `_commit_entity`, `_commit_triples`, and retrieval trace builders as primary integration surfaces.
  - #### Section 1.2 · LlamaIndex Capability Map
    - ##### Paragraph 1.2.1 · Property Graph Store inventory
      - Neo4j + NetworkX stores required with optional import fallbacks.
    - ##### Paragraph 1.2.2 · KnowledgeGraphIndex affordances
      - Provide triple ingestion, summarisation, and text→Cypher hooks for agents toolkit.

## Volume II · Integration Architecture
- ### Chapter 2 · Service Refactor Blueprint
  - #### Section 2.1 · Backend abstraction layering
    - ##### Paragraph 2.1.1 · Define `GraphBackend` interface (document/entity/relation ops, neighborhood fetch).
    - ##### Paragraph 2.1.2 · Implement `Neo4jBackend` + `NetworkXBackend` bridging to LlamaIndex stores when available.
  - #### Section 2.2 · Knowledge graph index orchestration
    - ##### Paragraph 2.2.1 · Lazy-load `KnowledgeGraphIndex` per backend, caching graph store handles.
    - ##### Paragraph 2.2.2 · Provide export utilities for retrieval traces + agent tooling.

## Volume III · Analytics & Enrichment Pipelines
- ### Chapter 3 · Community Detection Engine
  - #### Section 3.1 · Graph snapshot construction
    - ##### Paragraph 3.1.1 · Materialise ingestion-run subgraph from GraphMutation record.
  - #### Section 3.2 · Algorithm Selection & Execution
    - ##### Paragraph 3.2.1 · Prefer NetworkX greedy modularity as default; fallback to label propagation for minimal graphs.
    - ##### Paragraph 3.2.2 · Summarise clusters into narrative bulletins stored alongside ingestion job metadata and DocumentStore.
- ### Chapter 4 · Timeline Enrichment Workflow
  - #### Section 4.1 · Enrichment triggers post-ingestion success
    - ##### Paragraph 4.1.1 · Derive highlight sets from graph neighborhoods + community assignments.
  - #### Section 4.2 · Persistence & idempotence
    - ##### Paragraph 4.2.1 · Update TimelineStore entries in-place with highlight/relation tags + coverage metrics.

## Volume IV · Retrieval Trace & Agent Tooling
- ### Chapter 5 · Trace Payload Extensions
  - #### Section 5.1 · Subgraph packaging
    - ##### Paragraph 5.1.1 · Include nodes, edges, supporting events, and community metadata in trace output.
  - #### Section 5.2 · Test reinforcement
    - ##### Paragraph 5.2.1 · Extend retrieval + graph service tests to assert new payloads.
- ### Chapter 6 · Cypher Exploration Toolkit
  - #### Section 6.1 · Cypher execution wrappers
    - ##### Paragraph 6.1.1 · Provide secure `run_cypher` with sandbox guardrails.
  - #### Section 6.2 · Text-to-Cypher prompt helper
    - ##### Paragraph 6.2.1 · Implement template-driven LLM prompt for natural language exploration within agents toolkit.

## Volume V · Documentation & Stewardship
- ### Chapter 7 · Schema & Ontology Runbooks
  - #### Section 7.1 · Roadmap updates
    - ##### Paragraph 7.1.1 · Capture property graph schema, community metrics, and enrichment procedures in docs/roadmaps.
  - #### Section 7.2 · PRP alignment
    - ##### Paragraph 7.2.1 · Update relevant PRP entries to reflect new knowledge graph operations + tooling.
- ### Chapter 8 · Validation & Handoff
  - #### Section 8.1 · Test suite execution
    - ##### Paragraph 8.1.1 · Target pytest backend/tests subset focusing on graph + retrieval + timeline.
  - #### Section 8.2 · Stewardship log entry
    - ##### Paragraph 8.2.1 · Append AGENTS.md log with summary + validation metrics.
