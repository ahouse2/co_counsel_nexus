# Reference Assets Integration Plan — 2025-10-30

## Phase 0 — Situation Assessment
- ### Repository Inventory
  - #### Directory Claims vs Reality
    - ##### Reference Assets
      - Current docs promise `Reference Code/` but directory absent.
      - External SDK acquisition steps undocumented.
    - ##### Command Automation
      - `.codex/commands/` referenced for process automation but missing on disk.
  - #### Documentation Integrity
    - ##### Cross-link Reliability
      - Multiple PRPs and onboarding rely on relative links; no automated verification exists.
- ### Constraints & Quality Gates
  - #### Repository Hygiene
    - ##### Agent Stewardship Log
      - Must append root `AGENTS.md` with contribution details post-change.
  - #### Tooling Expectations
    - ##### Validation
      - Implement deterministic cross-link verifier; document in commands catalog.

## Phase 1 — Directory Materialization
- ### Reference Code Workspace
  - #### Structure Definition
    - ##### Core Files
      - `Reference Code/README.md` describing purpose, sync policy, and licensing notes.
      - `Reference Code/catalog.yaml` enumerating upstream repositories, revisions, and license metadata.
      - `Reference Code/sync_reference_code.py` automates shallow clone/update of catalog entries.
  - #### Governance Hooks
    - ##### Git Hygiene
      - `.gitignore` entries to exclude cloned upstream repositories (`Reference Code/*/.git`).
- ### .codex Command Suite
  - #### Command Catalog Initialization
    - ##### `docs/AgentsMD_PRPs_and_AgentMemory/.codex/commands/`
      - `README.md` documenting execution semantics and environment expectations.
      - Command manifests (YAML) for syncing reference code and validating documentation links.

## Phase 2 — Documentation Alignment
- ### Onboarding Guide Updates
  - #### Repository Structure Section
    - Reflect newly materialized directories.
  - #### External Dependency Setup
    - Provide explicit acquisition steps leveraging `sync_reference_code.py`.
    - Include manual fallback instructions (git clone commands).
- ### PRPs & Registry Integrity
  - #### Cross-link Verification
    - Execute new validator to confirm all markdown links resolve locally.
    - Patch any broken references identified.

## Phase 3 — Validation & Stewardship
- ### Automated Link Check
  - Run `python Reference Code/sync_reference_code.py --help` smoke test for script docstring integrity.
  - Execute cross-link validator command (documented under `.codex/commands`).
- ### Documentation Review
  - Proofread onboarding additions and command docs for accuracy/completeness.
- ### Stewardship Log Update
  - Append contribution entry to root `AGENTS.md` with files touched and validation commands executed.
