# Roadmap — Ingestion Connector Error Coverage Reinforcement

## Volume I — Regression Fortification
- ### Chapter 1 — CourtListener Edge Safeguards
  - #### Paragraph A — Credential Presence Enforcement
    - ##### Sentence i — Inspect existing fixtures to reuse `_prime_settings` helper.
      - ###### Word α — Confirm registry payload requires `credRef`.
      - ###### Word β — Model missing `credRef` invocation raising `HTTPException` with 400 status.
    - ##### Sentence ii — Craft test ensuring `_load_credentials` surfaces 404 when registry lacks entry.
      - ###### Word γ — Prime registry without referenced credential and assert raised error detail.
  - #### Paragraph B — HTTP Failure Resilience
    - ##### Sentence i — Introduce retry/backoff to CourtListener `_request` for 429/5xx classes.
      - ###### Word δ — Inject awaitable sleep hook for deterministic tests.
      - ###### Word ε — Log retry metadata for observability.
    - ##### Sentence ii — Extend tests with FakeAsyncClient emitting 429 then 200 to verify reuse after retry.
      - ###### Word ζ — Assert call count equals retries + success.
      - ###### Word η — Ensure cache reuse still functions when digest present.

- ### Chapter 2 — Web Search Credential Integrity
  - #### Paragraph A — API Key Requirement Validation
    - ##### Sentence i — Exercise connector with credential missing `api_key` to confirm 422 response.
      - ###### Word θ — Ensure detail string references missing api_key.
  - #### Paragraph B — Upstream HTTP Error Handling
    - ##### Sentence i — Simulate 500 response to verify translated 502 HTTPException.
      - ###### Word ι — Confirm detail mentions upstream failure text.

- ### Chapter 3 — Utilities & Fixtures Harmonisation
  - #### Paragraph A — FakeAsyncClient Enhancements
    - ##### Sentence i — Record each call for assertions without altering interface.
      - ###### Word κ — Provide helper to seed responses conveniently.
  - #### Paragraph B — Logging Noise Containment
    - ##### Sentence i — Route test loggers to `NullHandler` to avoid clutter.

## Volume II — Validation & Stewardship
- ### Chapter 4 — Test Execution
  - #### Paragraph A — Run targeted pytest module `backend/tests/test_ingestion_connectors.py -q`.
  - #### Paragraph B — If stable, execute full backend test sweep.
- ### Chapter 5 — Artefact Stewardship
  - #### Paragraph A — Update build log entry summarising regression coverage.
  - #### Paragraph B — Append ACE memory note capturing retriever/planner/critic deliberations.
  - #### Paragraph C — Extend root `AGENTS.md` Chain of Stewardship log with work summary.
