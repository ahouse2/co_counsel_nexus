# Phase 1 Implementation Review & ACE Workflow Blueprint

- ## Review Context
  - ### Scope
    - #### Artefacts Evaluated
      - backend/app/storage/**/*.py
      - backend/app/services/vector.py, ingestion.py
      - backend/app/models/api.py
      - docs/roadmaps/2025-11-01_prp_execution_phase1.md
  - ### Methodology
    - #### Rubric
      - Applied 15-category rubric (Tech Accuracy → Enterprise Value) with 1–10 scale.
    - #### Evidence Handling
      - Source inspection, traceability cross-checks, risk analysis, and reproducibility validation design review.

- ## Rubric Scorecard
  - ### Summary Table

    | Category | Score | Evidence Highlights | Observations |
    | --- | --- | --- | --- |
    | Technical Accuracy | 9 | Deterministic storage semantics, vector fallback aligns with settings. | Consider file locking for future concurrency. |
    | Modularity | 9 | Stores encapsulated per concern; services accept injectables. | Potential to extract entity indexing policy. |
    | Performance | 8 | In-memory cosine search O(n) acceptable for Phase 1 scale. | Document store lacks bulk operations. |
    | Security | 8 | Filesystem sanitisation (`replace("/", "_")`). | No validation for traversal beyond root; add path normalisation guards. |
    | Scalability | 8 | Qdrant client bootstrap + in-memory fallback. | Need pagination/streaming for job/timeline listing. |
    | Robustness | 9 | Error handling for missing records and JSON decode resilience. | Logging missing for silent skips. |
    | Maintainability | 9 | Readable composition, dataclass usage, settings-driven wiring. | Document default MIME inference may require tests. |
    | Innovation | 9 | Hybrid vector strategy, deterministic embeddings to avoid test flake. | Explore hashed embedding seeding controls. |
    | UX/UI | 8 | API responses preserve citations/traces schema. | Extend ingestion feedback for skipped files. |
    | Explainability | 10 | Timeline events derived from parse pipeline; metadata stored verbosely. | None. |
    | Coordination | 10 | Stores + services align with roadmap tasks; ACE notes present. | Maintain synchronised ACE updates post-future cycles. |
    | DevOps | 8 | Collection bootstrap ensures deterministic state. | Add health probes for storage directories. |
    | Documentation | 9 | Roadmap + inline docstrings convey intent. | Expand README quickstart for ingestion prerequisites. |
    | Compliance | 9 | Structured metadata ready for audit trails. | Introduce retention policy controls. |
    | Enterprise Value | 9 | Delivers retrieval foundation unlocking downstream features. | Next: integrate analytics instrumentation. |

- ## Key Findings
  - ### Strengths
    - #### Deterministic persistence improves reproducibility and contract testing confidence.
    - #### VectorService abstraction minimises external dependency friction while keeping parity with production topology.
    - #### Timeline and job stores already expose sorted outputs for predictable UX flows.
  - ### Risks & Gaps
    - #### Missing file-level validation for directory traversal (DocumentStore & JobStore `_path`).
    - #### No concurrency control for timeline append operations — acceptable today but flagged for future parallel ingestion.
    - #### Lack of observability hooks (metrics/logs) may hinder debugging under load.

- ## Recommended Follow-ups
  - ### Immediate (Phase 1.1)
    - #### Implement path normalisation + allowlist to guard against `..` segments.
    - #### Add instrumentation events around ingestion/skipped files.
  - ### Near Term (Phase 2)
    - #### Introduce lightweight record batching for document/job listings.
    - #### Provide CLI utility to purge/reset stores safely.
  - ### Long Term
    - #### Evaluate migration path from JSON stores to embedded SQLite once concurrency requirements increase.

- ## ACE 3-Agent Validation Workflow
  - ### Trigger: Pull Request push to `main`-targeting branches.
  - ### Agent Roles
    - #### Retriever Agent
      - ##### Inputs: Changed files, linked issues, prior ACE memory segments.
      - ##### Actions
        - Collect dependency graph via `poetry export`/`pipdeptree` snapshot.
        - Run static analysis (ruff/mypy) scoped to diff.
        - Generate context bundle (design docs, configs) and publish to shared artefact store.
      - ##### Outputs: `retriever_report.json` with dependencies, touched modules, detected risks.
    - #### Planner Agent
      - ##### Inputs: Retriever bundle, PR description, rubric baseline.
      - ##### Actions
        - Map changes to rubric categories; design targeted test plan.
        - Orchestrate execution plan: unit/integration tests, smoke flows, data migrations.
        - Emit `plan.md` enumerating ordered checks with fallback strategies.
      - ##### Outputs: Signed plan referencing commands + expected artefacts.
    - #### Critic Agent
      - ##### Inputs: Execution artefacts (test logs, coverage), retriever + planner reports.
      - ##### Actions
        - Validate command results vs. expectations; compute rubric deltas.
        - Enforce policy gates (no category <7; average ≥8).
        - File automated review comment & update ACE memory/logs.
      - ##### Outputs: `critic_verdict.md`, status signal (pass/block), rubric table diff.
  - ### Automation Orchestration
    - #### Pipeline Layout
      - ##### Stage 1 — Context Sync: Triggered GitHub Action collects diff metadata → kicks Retriever container job.
      - ##### Stage 2 — Plan Synthesis: Planner container runs after Retriever artefact upload → produces YAML plan.
      - ##### Stage 3 — Execution & Critique: Re-uses plan to run tests (via reusable workflow) → Critic validates outputs.
    - #### Data Persistence
      - ##### Artefacts stored under `build_logs/<date>/ace/<pr-id>/` for traceability.
      - ##### ACE memory appended programmatically via repo API to `memory/ace_state.jsonl`.
    - #### Notifications
      - ##### GitHub PR comment summarising rubric scores + gating decision.
      - ##### Optional Slack webhook for failed checks with remediation pointers.

- ## Implementation Roadmap Notes
  - ### Phase A — Automation Scaffolding
    - #### Define GitHub reusable workflows for Retriever/Planner/Critic containers.
  - ### Phase B — Artefact Schema Stabilisation
    - #### Publish JSON schema for reports, enforce via CI validation step.
  - ### Phase C — Policy Enforcement
    - #### Wire rubric gating + status checks blocking merges on failure.
