# Knowledge Hub Execution Plan — 2025-11-24

## Phase I · Foundation & Content Curation
- ### 1.1 · Repository scaffolding
  - #### 1.1.1 · Create curated legal resource corpus under `docs/knowledge/`
    - ##### 1.1.1.1 · Author doctrinal best-practice markdown dossiers with real guidance (discovery, deposition, privilege).
    - ##### 1.1.1.2 · Compose `catalog.json` enumerating lesson metadata, media references, and difficulty taxonomy.
  - #### 1.1.2 · Extend configuration primitives
    - ##### 1.1.2.1 · Add knowledge content + storage paths to `Settings` with deterministic defaults.
    - ##### 1.1.2.2 · Wire directory preparation (progress/bookmarks cache) into `prepare_directories` guardrails.

## Phase II · Backend Knowledge Service Layer
- ### 2.1 · Storage primitives
  - #### 2.1.1 · Implement `KnowledgeProfileStore`
    - ##### 2.1.1.1 · Persist per-user progress + bookmark envelopes with atomic writes + retention aware metadata.
    - ##### 2.1.1.2 · Provide read/update APIs returning structured completion metrics.
- ### 2.2 · LlamaIndex-powered retrieval
  - #### 2.2.1 · Materialise `KnowledgeService`
    - ##### 2.2.1.1 · Load catalog + markdown sections, synthesise deterministic section IDs, surface media payloads.
    - ##### 2.2.1.2 · Build in-memory `VectorStoreIndex` with shared embedding runtime, guard optional dependency gaps.
    - ##### 2.2.1.3 · Implement query routine with filter application (tags/difficulty/media) and snippet crafting.
  - #### 2.2.2 · Progress + bookmarking orchestration
    - ##### 2.2.2.1 · Compute completion ratios from section totals.
    - ##### 2.2.2.2 · Audit principal binding (tenant + subject) for multi-tenant safety.
- ### 2.3 · FastAPI endpoints
  - #### 2.3.1 · `/knowledge/search`
    - ##### 2.3.1.1 · Define request/response models with pagination metadata + relevance score.
    - ##### 2.3.1.2 · Apply `authorize_knowledge_read` dependency + audit.
  - #### 2.3.2 · `/knowledge/lessons`
    - ##### 2.3.2.1 · GET collection summarising lessons with user progress + bookmark state.
    - ##### 2.3.2.2 · GET item returning section payloads (markdown + media) and per-section completion flags.
    - ##### 2.3.2.3 · POST progress + bookmark mutations gated by `authorize_knowledge_write`.
- ### 2.4 · Security alignment
  - #### 2.4.1 · Expand OAuth scopes/audience defaults + Oso policy coverage.
  - #### 2.4.2 · Update integration tests + fixtures for new scopes.

## Phase III · Frontend Knowledge Hub
- ### 3.1 · API client & types
  - #### 3.1.1 · Extend `types.ts` + `apiClient.ts` for knowledge contracts.
  - #### 3.1.2 · Ensure error surfaces + filter serialization align with backend.
- ### 3.2 · UI components
  - #### 3.2.1 · Main `KnowledgeHub` shell with responsive layout + accessibility semantics.
    - ##### 3.2.1.1 · Search bar with filters (tags, difficulty, media) feeding backend query.
    - ##### 3.2.1.2 · Lesson catalog list with progress indicators + bookmark toggles.
    - ##### 3.2.1.3 · Interactive viewer rendering markdown + media gallery, section completion controls.
  - #### 3.2.2 · Integrate into `App` navigation + theme.
  - #### 3.2.3 · Update CSS for cards, filters, progress bars, and viewer states.
- ### 3.3 · State management
  - #### 3.3.1 · Local state for lessons/search results with optimistic updates on progress/bookmarks.
  - #### 3.3.2 · Debounce search input + handle loading/error feedback loops.

## Phase IV · Quality Gates
- ### 4.1 · Backend tests (`pytest`)
  - #### 4.1.1 · Search relevance regression using curated corpus.
  - #### 4.1.2 · Progress + bookmark persistence contract tests.
- ### 4.2 · Frontend tests (`vitest`)
  - #### 4.2.1 · Render knowledge hub skeleton + lesson selection flow.
  - #### 4.2.2 · Validate search/filter interactions and bookmarking UI state toggles.
- ### 4.3 · Lint/type guardrails (mypy/ruff, tsc) — run targeted to ensure no regressions.

## Phase V · Documentation & Stewardship
- ### 5.1 · Update PRP knowledge hub sections with endpoint contracts + UX flow.
- ### 5.2 · Append build log + ACE state memory entry capturing execution + validation.
- ### 5.3 · Extend `AGENTS.md` stewardship log with task + rubric summary.
