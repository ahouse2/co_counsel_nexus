# Data Model Enrichment Plan — 2025-10-28

## Phase 1 — Discovery & Context Alignment
- ### Inventory Existing Guidance
  - #### Read `docs/roadmaps/2024-11-01_co_counsel_workflow_plan.md` Data Model section.
  - #### Identify referenced storage systems (Neo4j, Qdrant, filesystem) for alignment.
- ### Extract Implicit Model Contracts
  - #### Trace mentions of Document/Chunk/Entity/Relation/ForensicsArtifact across docs.
  - #### Determine expected interactions (graph, vectors, forensics outputs).

## Phase 2 — Schema Design Detailing
- ### Document & Chunk Models
  - #### Enumerate core metadata fields (identity, provenance, media properties).
  - #### Specify nullable constraints and Pydantic-compatible typing.
- ### Entity & Relation Models
  - #### Define canonical naming, type vocabularies, and relationship semantics.
  - #### Capture property bags for flexibility with strict typing on identifiers.
- ### ForensicsArtifact Model
  - #### Map artifact catalog (hash, metadata, structure, authenticity, financial).
  - #### Align fields with filesystem outputs and retrieval APIs.

## Phase 3 — Persistence Mapping Blueprint
- ### Neo4j Graph
  - #### Assign labels and relationship types per model.
  - #### Draft uniqueness constraints and supporting indexes.
- ### Qdrant Vector Store
  - #### Determine collection layout, vector sizes, payload schemas for chunks.
  - #### Map document-level metadata replication needs.
- ### Filesystem Layout
  - #### Document directory hierarchy for raw inputs and forensic derivatives.
  - #### Ensure compatibility with ingestion + retrieval services.

## Phase 4 — Migration & Initialization Assets
- ### Neo4j Migration Script
  - #### Create Cypher defining constraints/indexes with `IF NOT EXISTS` guards.
- ### Qdrant Bootstrap Script
  - #### Provide Python client snippet establishing collections and payload schema hints.
- ### Filesystem Bootstrap Checklist
  - #### Enumerate required directories with permissions guidance.

## Phase 5 — Documentation Update Execution
- ### Expand Data Model Section
  - #### Introduce per-model tables summarizing fields/type/nullability/notes.
  - #### Add persistence mapping narrative + cross-store linkage.
- ### Embed Migration Guidance
  - #### Reference new scripts from roadmap and provide inline commands.
- ### Quality Assurance
  - #### Re-read section twice for accuracy/completeness.
  - #### Validate markdown formatting (tables, code blocks, lists) renders cleanly.

## Phase 6 — Repository Stewardship
- ### Chain-of-Stewardship Entry
  - #### Summarize tasks, files touched, validation status.
- ### Commit & PR Preparation
  - #### Stage changes, run lint-equivalent checks (markdown lint via visual inspection).
  - #### Craft detailed summary + tests section for PR body and final response.
