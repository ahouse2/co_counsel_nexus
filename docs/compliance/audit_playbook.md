# Audit Playbook — Privileged Access & Lifecycle Evidence

## 1. Scope & Objectives
- Establish append-only, hash-chained evidence for privileged security decisions, ingestion lifecycle transitions, and agent orchestration outcomes.
- Ensure audit artifacts remain tamper-evident, confidentiality-preserving, and rapidly reviewable under regulatory and internal governance controls.

## 2. Rotation & Key Management
- **Manifest Encryption Key**
  - Stored in hardened secret manager; projected locally as `MANIFEST_ENCRYPTION_KEY_PATH`.
  - Rotate every **90 days** or immediately after suspected compromise.
  - Rotation Procedure:
    1. Generate a 256-bit AES-GCM key using FIPS-compliant tooling (`openssl rand -out manifest.key 32`).
    2. Stage key in secret manager and schedule deployment window.
    3. Drain ingestion queues; pause worker execution to prevent partial writes.
    4. Deploy new key, update environment variables, and restart API/worker processes.
    5. Verify by decrypting a sample manifest and appending a canary audit entry.
    6. Shred retired key material and update rotation ledger in the stewardship log.
- **Audit Trail Hash Chain**
  - No key rotation required; integrity derives from SHA-256 lineage chain.
  - Maintain off-host checksum of last known hash to detect rollback attacks.

## 3. Review Cadence
- **Daily Spot Checks**
  - Validate audit log freshness (entries within last 24h) and chain integrity using `python -m backend.app.utils.audit verify` (see runbooks/CLI snippet).
  - Confirm ingestion/job manifest retention pruning executed via automated job or manual `list_jobs()` sanity check.
- **Weekly Compliance Review**
  - Sample 5% of privileged access events (security category) and reconcile against authorization requests.
  - Cross-check ingestion lifecycle events for terminal outcomes vs. job manifests.
  - Document findings, anomalies, and remediation actions in `docs/validation/weekly_audit_review.md` (create if absent).
- **Quarterly Executive Review**
  - Aggregate metrics: counts of allowed/denied privileged requests, ingestion successes/failures, agent thread completions.
  - Present to Compliance & Platform guilds; ratify rotation status and backlog of corrective actions.

## 4. Break-Glass & Incident Reconciliation
- **Trigger Conditions**: Unauthorized access attempt, audit chain verification failure, or manifest integrity breach.
- **Immediate Actions**
  1. Freeze ingestion workers and disable agent execution endpoints (toggle feature flag or scale to zero).
  2. Snapshot audit log and manifests to immutable storage (append timestamped copy under `archive/<date>/audit/`).
  3. Run `AuditTrail.verify()` and compare against off-host checksum to isolate tampered segments.
  4. Regenerate manifests from secure backups if corruption detected; document hash differences.
- **Root-Cause Analysis**
  - Triangulate security-denied events, ingestion failures, and system alerts to reconstruct timeline.
  - Capture RCA in incident response template; include hash chain proofs and manifest diff artifacts.
- **Reconciliation Closure**
  - Restore services post-key rotation (if required) and replay pending ingestion tasks.
  - Submit signed-off incident report, update stewardship log with remediation summary, and annotate validation matrix linkage.

## 5. Operational Checklists
- **Daily Operator Checklist**
  - [ ] Confirm audit log appended since last shift change.
  - [ ] Run manifest retention pruning dry-run and verify deletions logged.
  - [ ] Spot check at least one security denial for accurate scope/role metadata.
- **Release Checklist**
  - [ ] Validate new codepaths emit `AuditEvent` with populated actor/subject metadata.
  - [ ] Execute end-to-end ingestion + query flow; inspect audit chain for status transitions and authz decisions.
  - [ ] Update stewardship log entry with rotation status, review cadence confirmations, and incident backlog delta.

## 6. Stewardship Interfaces
- **Validation Matrix**: Reference this playbook for compliance evidence expectations and review cadences.
- **Chain of Stewardship Log**: Each deployment or rotation must annotate the log with execution timestamp, tests run, rubric snapshot, and link back to this playbook section.
- **Runbooks**: Embed CLI invocations for verifying audit trails and decrypting manifests for approved investigations.

## 7. Appendices
- **CLI Snippets**
  - Verify audit chain: `python - <<'PY'
from pathlib import Path
from backend.app.utils.audit import AuditTrail
path = Path("storage/audit.log")
print("audit-ok" if AuditTrail(path).verify() else "audit-corrupt")
PY`
  - Inspect encrypted manifest: use `decrypt_manifest` helper with read-only key material in offline environment.
- **Escalation Contacts**
  - Primary: Platform Security On-Call (`sec-oncall@cocounsel.test`)
  - Secondary: Compliance Duty Officer (`compliance-duty@cocounsel.test`)
  - Audit Artefact Custodian: `audit-custodian@cocounsel.test`
