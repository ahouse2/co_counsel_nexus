# 2025-11-22 · Forensics + Privilege Trace Integration Execution Map

## Volume I · Strategy & Outcomes
- Chapter 1 · Objectives
  - Paragraph 1 · User Goals
    - Sentence 1 · Incorporate LlamaIndex node intelligence into forensics artifacts for richer anomaly detection.
    - Sentence 2 · Enable agents to trigger DFIR and financial analyzers through directive-aware tools.
    - Sentence 3 · Tighten privilege classifier propagation through retrieval traces and QA gating.
    - Sentence 4 · Extend regression coverage across forensics modalities and ledger checks.
    - Sentence 5 · Publish remediation workflows in validation playbooks.
  - Paragraph 2 · Success Metrics
    - Sentence 1 · Forensics reports expose node count, embedding stats, and alerts with zero serialization errors.
    - Sentence 2 · Agent connectors emit DFIR/financial findings when directives are asserted, surfacing in memory artifacts.
    - Sentence 3 · QA stage records gating metadata whenever privileged evidence is detected.
    - Sentence 4 · `pytest backend/tests/test_forensics*.py -q` passes with new assertions for node enrichment and ledger summarisation.
    - Sentence 5 · New validation playbook covers workflow plus remediation steps with citations to pipeline components.

## Volume II · System Architecture Adjustments
- Chapter 1 · Forensics Service
  - Paragraph 1 · Context Schema
    - Sentence 1 · Extend `PipelineContext` to track ingested LlamaIndex nodes and upstream metadata.
    - Sentence 2 · Accept node payloads + ingestion metadata in `build_document_artifact` and persist them through the pipeline.
  - Paragraph 2 · Processing Stage
    - Sentence 1 · Introduce `_stage_llama_index` computing node counts, chunk stats, embedding norms, duplicate detection, and IsolationForest outliers.
    - Sentence 2 · Emit structured alerts (`llama.embedding.outlier`, `llama.duplicate.chunk`) and summarise samples for downstream DFIR connectors.
    - Sentence 3 · Merge ingestion metadata into report metadata ensuring deduped keys and canonical serialization.
  - Paragraph 3 · Persistence
    - Sentence 1 · Persist llama-index payload + alerts inside stored report JSON without bloat by truncating previews/embeddings.

- Chapter 2 · Ingestion Service Coupling
  - Paragraph 1 · Node Transfer
    - Sentence 1 · Serialize `PipelineNodeRecord` objects into dict snapshots with node IDs, chunk indices, truncated text, metadata, and embeddings.
    - Sentence 2 · Forward ingestion metadata (source type, checksum, chunk stats) into forensics builder to seed new stage.
  - Paragraph 2 · Payload Enrichment
    - Sentence 1 · Record embedding norms within vector payloads for retrieval trace visibility.
    - Sentence 2 · Ensure Qdrant payload remains JSON-safe while preserving provenance fields (doc ID, origin, source type).

- Chapter 3 · Retrieval & Privilege
  - Paragraph 1 · Trace Augmentation
    - Sentence 1 · Expand vector trace entries with chunk indices, source types, text previews, and embedding norms for DFIR summarisation.
    - Sentence 2 · Surface privilege aggregate label + flagged docs into telemetry to enable QA gating decisions.
  - Paragraph 2 · QA Integration
    - Sentence 1 · Modify QA tool output to include gating metadata and telemetry updates when privileged evidence is present.

## Volume III · Agent Connectors & Directives
- Chapter 1 · Context & Memory
  - Paragraph 1 · Directive Channel
    - Sentence 1 · Seed `CaseThreadMemory` with a `directives` namespace for agent coordination.
    - Sentence 2 · Enhance `StrategyTool` heuristics to populate directives (DFIR/financial) based on question cues.
  - Paragraph 2 · Telemetry Hooks
    - Sentence 1 · Record directive activation inside agent telemetry for auditability.

- Chapter 2 · Connector Execution
  - Paragraph 1 · Forensics Tool Enhancements
    - Sentence 1 · Cache loaded artifact payloads keyed by doc ID to share across connectors.
    - Sentence 2 · When DFIR directive active, aggregate high-entropy nodes, duplicate chunks, and privilege alerts into a DFIR bundle.
    - Sentence 3 · When financial directive active, compile ledger totals/anomalies plus remediation recommendations.
    - Sentence 4 · Persist connector outputs inside memory artifacts and return bundle to orchestrator.

## Volume IV · Quality Engineering
- Chapter 1 · Tests
  - Paragraph 1 · Forensics Unit Coverage
    - Sentence 1 · Add regression verifying llama-index stage populates stats, alerts, and summary lines.
    - Sentence 2 · Extend financial ledger test to assert anomaly summaries + remediation hints.
  - Paragraph 2 · Agent Connector Coverage
    - Sentence 1 · Introduce targeted test mocking document store + directives to ensure DFIR/financial bundles emitted.

- Chapter 2 · Tooling & Docs
  - Paragraph 1 · Validation Playbook
    - Sentence 1 · Author `docs/validation/forensics_workflow_playbook.md` capturing workflows, alerts, and remediation checklists.
  - Paragraph 2 · Stewardship Updates
    - Sentence 1 · Append AGENTS chain entry, update build log, and record ACE state event post-validation.

## Volume V · Execution Ledger
- Chapter 1 · Command & Verification
  - Paragraph 1 · Test Suite
    - Sentence 1 · Run `pytest backend/tests/test_forensics.py backend/tests/test_forensics_chain.py backend/tests/test_forensics_cli.py -q`.
  - Paragraph 2 · Review Loop
    - Sentence 1 · Re-run diff inspection thrice ensuring no placeholder artefacts and JSON serialisation is deterministic.
