# Graph Subgraph Orchestration Refinement Blueprint

## Volume I · Situational Awareness
- ### Chapter 1 · Inventory
  - #### Section 1.1 · Retrieval Trace Construction
    - ##### Paragraph 1.1.1 · Observe manual neighbor aggregation in `_build_trace`.
    - ##### Paragraph 1.1.2 · Note duplication of edge deduplication logic across services.
  - #### Section 1.2 · Graph Service Facilities
    - ##### Paragraph 1.2.1 · `neighbors` returns per-node results but lacks multi-node synthesis.
    - ##### Paragraph 1.2.2 · UI consumers require consistent payload formatting.

## Volume II · Refactor Objective
- ### Chapter 2 · Graph Subgraph Abstraction
  - #### Section 2.1 · Dataclass Definition
    - ##### Paragraph 2.1.1 · Implement `GraphSubgraph` capturing node/edge maps and serialization helper.
  - #### Section 2.2 · Aggregation Method
    - ##### Paragraph 2.2.1 · Add `GraphService.subgraph` to merge neighbor snapshots with deduplication.
    - ##### Paragraph 2.2.2 · Ensure caches/property graph/NetworkX stores stay updated via existing hooks.

## Volume III · Retrieval Trace Alignment
- ### Chapter 3 · Trace Construction Update
  - #### Section 3.1 · Replace manual loops with `GraphSubgraph` usage.
    - ##### Paragraph 3.1.1 · Preserve relation statement extraction and document scope logic.
  - #### Section 3.2 · Community & Timeline Integration
    - ##### Paragraph 3.2.1 · Reuse `GraphSubgraph` payload for nodes/edges while keeping community/event enrichment.

## Volume IV · Verification Suite
- ### Chapter 4 · Unit Tests
  - #### Section 4.1 · Graph Service Coverage
    - ##### Paragraph 4.1.1 · Extend `test_graph_service` to assert `subgraph` correctness for memory backend.
  - #### Section 4.2 · Retrieval Trace Regression
    - ##### Paragraph 4.2.1 · Confirm trace payload still exposes nodes, edges, events, communities.

## Volume V · Documentation & Stewardship
- ### Chapter 5 · Roadmap Update
  - #### Section 5.1 · Document new abstraction in schema/enrichment roadmap.
  - #### Section 5.2 · Append AGENTS log entry post-validation with pytest subset command.
