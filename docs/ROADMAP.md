# Roadmap — Phases and Milestones

Phase 0 — Repo & Guardrails
- Compose (api, neo4j, qdrant) up green; health endpoint
- CI basics; pre‑commit; build_logs/memory structure

Phase 1 — Data Foundations
- Neo4j constraints; vector store wiring; readiness/health endpoints

Phase 2 — Ingestion MVP
- LlamaHub loaders (local + one cloud); OCR required; Vision‑LLM agent for classification/tagging/scanned docs; chunk + embed; persist

Phase 3 — Context Engine
- Triples extraction → Neo4j; hybrid retriever; ContextPacket JSON

Phase 4 — Forensics Core (Non‑Negotiable)
- Hashing (SHA‑256), metadata extraction, PDF structure checks, email header analysis
- Image authenticity pipeline (EXIF, ELA, PRNU/clone detection where feasible)
- Financial forensics (basic): totals consistency, anomaly flags, entity extraction; produce forensics summary artifacts

Phase 5 — Multi‑Agent + ACE
- MS Agents workflow nodes; memory threads; QAAgent + rubric

Phase 6 — Timeline
- Event graph + API; UI timeline with cited pop‑outs

Phase 7 — Legal Research & Extended Forensics
- CourtListener/web search integrations; privilege detector; chain‑of‑custody exports

Phase 8–9 — API + Frontend
- /ingest, /query, /timeline, /graph/neighbor; neon UI chat/graph

Phase 10 — Testing/Hardening
- Unit/integration/e2e/load; security posture; orphan scan CI

Phase 11 — Packaging
- Installers/containers/binaries as needed
- Tiered Docker Compose profiles + `scripts/install_tier.sh` for Community/Professional/Enterprise deployments with OTLP & Grafana bundles
- Billing telemetry surface (`/billing/*`), onboarding flow, and commercial collateral tracked under `docs/commercial/`
