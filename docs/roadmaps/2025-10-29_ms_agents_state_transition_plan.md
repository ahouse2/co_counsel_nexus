# 2025-10-29 — MS Agents Workflow State & Telemetry Enhancements

## 1. Vision Capsule
- Deliver richer operational blueprint for Co-Counsel MS Agents + Swarms workflow.
- Encode explicit state machines, failure semantics, and retry strategies in both spec and tooling registry.
- Add visual sequence diagrams clarifying node handoffs.
- Capture per-agent contracts (inputs/outputs/telemetry/memory) to de-risk implementation.

## 2. Decision Tree Overview
- Branch A — Documentation scope alignment
  - Confirm impacted artifacts (spec + tool registry) vs. auxiliary planning log.
  - Ensure coherence with prior roadmap docs.
- Branch B — State machine design depth
  - Choose representation (tables + pseudo-BPMN) ensuring deterministic transitions.
  - Determine error taxonomies aligning with ACE guidance.
- Branch C — Diagramming approach
  - Adopt Mermaid sequence diagrams for repo consistency.
  - Validate readability (lane ordering, alt/opt blocks) for ingestion → forensics chain.
- Branch D — Agent contract granularity
  - Define minimum field set for inputs/outputs (structured + memory handles).
  - Specify telemetry events & metrics anchored to OTel conventions.

## 3. Decomposition (Books → Chapters → Paragraphs → Sentences)
- Book 1 — Specification augmentation
  - Chapter 1.1 — Draft agent state lifecycle tables
    - Paragraph 1.1.a — Enumerate canonical states per agent (Init, Pending, Active, Success, SoftFail, HardFail, Cancelled).
    - Paragraph 1.1.b — Map transitions triggered by events (ingestion completed, timeout, retry budget exhausted).
    - Paragraph 1.1.c — Encode retry policy (backoff, max attempts) and escalation path.
  - Chapter 1.2 — Embed failure handling narrative
    - Paragraph 1.2.a — Align with ACE failure classes (transient vs fatal).
    - Paragraph 1.2.b — Document mitigation hooks (circuit breaker, human review queue).
  - Chapter 1.3 — Integrate per-agent contract tables
    - Paragraph 1.3.a — Inputs (data payloads, context tokens).
    - Paragraph 1.3.b — Outputs (artifacts, status, telemetry emission IDs).
    - Paragraph 1.3.c — Memory usage (short-term scratchpads vs. persistent stores).
  - Chapter 1.4 — Add sequence diagrams section
    - Paragraph 1.4.a — Ingestion → GraphBuilder → Research.
    - Paragraph 1.4.b — Research → Timeline.
    - Paragraph 1.4.c — Timeline → Forensics fan-out.
- Book 2 — Tool registry enrichment
  - Chapter 2.1 — Reflect new state + retry semantics
    - Paragraph 2.1.a — Update agent descriptions with state machines.
    - Paragraph 2.1.b — Add failure & retry tables referencing spec states.
  - Chapter 2.2 — Add per-agent contract/telemetry summary mirroring spec tables
    - Paragraph 2.2.a — Inputs/Outputs.
    - Paragraph 2.2.b — Telemetry events & metrics.
    - Paragraph 2.2.c — Memory footprint expectations.
- Book 3 — Consistency and QA
  - Chapter 3.1 — Cross-verify spec vs registry alignment.
    - Paragraph 3.1.a — Ensure terminology identical (state names, event triggers).
  - Chapter 3.2 — Validate markdown structure.
    - Paragraph 3.2.a — Headings anchored for navigation.
    - Paragraph 3.2.b — Mermaid blocks renderable.
  - Chapter 3.3 — Prepare final review checklist.

## 4. Execution Checklist (Sentences → Words → Characters)
- Draft state table skeleton in scratch buffer.
- Populate agent contract matrix ensuring column alignment.
- Compose Mermaid sequence diagrams with activation boxes for clarity.
- Mirror data in AGENT_TOOL_REGISTRY; re-read to avoid drift.
- Run `git status` sanity check.
- Perform dual-pass proofreading focusing on:
  - Terminology consistency.
  - Table formatting (pipes, alignment).
  - Citation anchor references for final summary.
- Update Chain of Stewardship log post-commit.
- Execute `git diff` (plain) and review end-to-end twice.

## 5. Risk Register
- R1 — Misaligned state names between spec and registry ➜ Mitigation: central glossary table.
- R2 — Mermaid syntax errors ➜ Mitigation: local lint via visual inspection; ensure `sequenceDiagram` spelled correctly.
- R3 — Overly verbose tables reduce readability ➜ Mitigation: use multi-row descriptions with `<br>` for clarity.

## 6. Personal Notes (Memory Aid)
- Maintain 1:1 mapping of agents: Ingestion, GraphBuilder, Research, Timeline, Forensics (Document/Image/Financial) + Coordinator context.
- Telemetry schema anchored on `span`, `event`, `metric` triad.
- Memory tiers: ephemeral (conversation), working set (vector scratch), persistent (Neo4j/Qdrant/Blob).
- Retry defaults: 3 attempts, exponential backoff base 2, jitter recommended.
- Failure escalation: after hard fail, emit `case_handoff_required` event for human intervention queue.
