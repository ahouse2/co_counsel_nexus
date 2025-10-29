# Knowledge Hub Hardening Roadmap (2025-11-24)

## Volume I – Platform Stabilisation
### Chapter 1 – Dependency Landscape
#### Section 1.1 – Runtime Environment
- Install email-validator, pandas, piexif, python-docx, extract-msg, mail-parser, pikepdf, pypdf, scikit-learn, boto3, Office365-REST-Python-Client to align FastAPI + ingestion stacks.
- Verify compatibility with Python 3.12; document required pins for CI parity.
#### Section 1.2 – Optional Embedding Fallbacks
- Adjust `backend/ingestion/llama_index_factory.py` to favour `LocalHuggingFaceEmbedding` when upstream integrations absent.
- Confirm knowledge service instantiation succeeds without remote HuggingFace dependencies.

### Chapter 2 – Security & Compliance Assurance
#### Section 2.1 – mTLS Compatibility Guardrails
- Update `backend/app/security/mtls.py` to gracefully handle `cryptography` 41+ certificate APIs lacking `*_utc` helpers.
- Add regression coverage via existing security suite to prevent future attribute regressions.

## Volume II – Knowledge Experience Refinement
### Chapter 3 – Backend Knowledge APIs
#### Section 3.1 – Profile & Bookmark Persistence
- Validate knowledge endpoints read/write curated JSON catalog and profile progress.
- Ensure search falls back to keyword scoring when embeddings unavailable.
#### Section 3.2 – Telemetry & Trace Hygiene
- Expand retrieval telemetry spans (`retrieval.vector_search`) and align tests with updated metrics payload.
- Harden dummy test services (graph, document store) to emulate production contracts.

### Chapter 4 – Frontend Knowledge Hub UX
#### Section 4.1 – Component Behaviour
- Ensure `KnowledgeHub` renders catalog, handles bookmarks/progress toggles, and surfaces search results.
- Normalise Testing Library queries to tolerate duplicate headings/snippets using `findAllByRole` / `findAllByText`.
#### Section 4.2 – Styling & Accessibility
- Maintain accessible landmarks for search/lesson views; review ARIA attributes post-render.

## Volume III – Verification & Stewardship
### Chapter 5 – Automated Coverage
#### Section 5.1 – Backend Suites
- Execute `pytest backend/tests/test_knowledge.py -q` for targeted validation.
- Execute `pytest backend/tests -q` ensuring telemetry and ingestion suites remain stable.
#### Section 5.2 – Frontend Suites
- Run `npx vitest run tests/knowledgeHub.test.tsx` to confirm React knowledge hub behaviour.

### Chapter 6 – Operational Artifacts
#### Section 6.1 – Build Logs & Stewardship
- Record execution in `build_logs/2025-11-24_knowledge_hub_release.md` with command outputs.
- Append ACE state entry summarising retriever/planner/critic loop and tests executed.
- Update `AGENTS.md` stewardship log with rubric + results.
