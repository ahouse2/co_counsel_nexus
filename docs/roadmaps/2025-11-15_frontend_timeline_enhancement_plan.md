# 2025-11-15 Frontend & Timeline Integration Execution Plan

## Vision ("Series Overview")
- Deliver an integrated experience combining conversational query, citation review, and historical timeline insights with resilient offline support and telemetry-backed backend services.

## Volume I — Frontend Experience Overhaul
- ### Chapter 1 — Project Skeleton & Tooling
  - #### Paragraph A — Vite React Scaffolding
    - Create TypeScript Vite project under `frontend/` with strict linting, eslint/prettier alignment, and pnpm-based scripts for dev/build/test.
    - Configure path aliases, environment handling, and CI-friendly commands.
  - #### Paragraph B — Accessibility & Offline Foundations
    - Integrate semantic landmarks, keyboard focus traps, ARIA labelling, and high-contrast theme toggles.
    - Register service worker for offline caching of static assets, queries, and timeline payloads with graceful degradation.
- ### Chapter 2 — Conversational Workspace
  - #### Paragraph A — Chat Orchestrator
    - Implement state management for prompts, streaming tokens, and conversation history stored in IndexedDB-backed cache.
    - Wire REST `POST /query` submission with optimistic UI; fallback to SSE-compatible streaming.
    - Establish WebSocket channel `/query/stream` for incremental answer rendering, resuming on reconnect.
  - #### Paragraph B — Citation & Evidence Review
    - Build evidence list with filters, search, and accessible disclosure widgets.
    - Implement detachable pop-out panels via portals for focused reading, supporting keyboard navigation and reduced motion preferences.
- ### Chapter 3 — Timeline Explorer
  - #### Paragraph A — Timeline Data Access
    - Fetch `/timeline` with cursor pagination, entity filters, and caching strategy.
    - Render chronological cards with group-by-day summary, ensuring screen reader order.
  - #### Paragraph B — Cross-View Synchronisation
    - Link chat answers to timeline events via shared citation metadata.
    - Surface inline controls to jump between chat messages and timeline entries.

## Volume II — Backend Timeline Intelligence
- ### Chapter 4 — Metadata Persistence
  - #### Paragraph A — Graph-derived Enrichment
    - Extend `TimelineEvent` to capture entity highlights, relation tags, and confidence derived from `GraphService.document_entities` results.
    - Persist new fields in JSONL store with backward-compatible parsing and migration logic.
  - #### Paragraph B — Storage & Query Enhancements
    - Update filtering to leverage enriched metadata (entity categories, roles) while maintaining existing API contracts.
- ### Chapter 5 — Telemetry Instrumentation
  - #### Paragraph A — Counter Definitions
    - Introduce structured counters for event reads, filters applied, cache hits/misses, and graph augmentation outcomes.
    - Export metrics via existing telemetry interface for ingestion by monitoring stack.
  - #### Paragraph B — Test Reinforcement
    - Update backend unit/integration tests covering metadata persistence, timeline filtering, and counter increments.

## Volume III — Documentation & Governance
- ### Chapter 6 — Frontend README Refresh
  - #### Paragraph A — Developer Onboarding
    - Document setup commands, architectural overview, accessibility guarantees, and offline behaviours.
  - #### Paragraph B — Usage Guides
    - Provide instructions for chat, citation panels, and timeline interactions including troubleshooting tips.
- ### Chapter 7 — UX Acceptance Criteria Ledger
  - #### Paragraph A — Criteria Capture
    - Author `docs/roadmaps/2025-11-15_ux_acceptance_criteria.md` enumerating success metrics for chat, evidence, and timeline flows.
    - Align criteria with accessibility, performance, and resilience targets.

## Volume IV — Quality Gate & Stewardship
- ### Chapter 8 — Validation Matrix
  - #### Paragraph A — Automated Checks
    - Run backend pytest suite, frontend type checks, lint, and unit tests; document outcomes.
  - #### Paragraph B — Stewardship Updates
    - Append AGENTS.md chain of stewardship log entry; capture build log entry detailing artefacts and metrics.

## Appendix — Decision Trees & Contingencies
- WebSocket fallback path to REST polling when streaming unsupported.
- Offline caching invalidation strategy: stale-while-revalidate with cache versioning.
- Telemetry isolation ensures counters no-op when instrumentation disabled.
