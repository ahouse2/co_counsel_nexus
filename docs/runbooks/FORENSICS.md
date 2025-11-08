# Forensics Runbook (Core)

Scope
- Ensure per-file forensic artifacts are generated and retrievable via API.

Artifacts (per file)
- hash.json, metadata.json, structure.json, authenticity.json, financial.json (as applicable)
- Location: ./storage/forensics/{fileId}/

Operations
- Re-run forensics: trigger reprocess endpoint (to be added) or CLI
- Verify artifacts: check presence and basic schema

Troubleshooting
- Missing authenticity: confirm file type supported; check logs for ELA/PRNU errors
- Financial parsing issues: validate file structure (CSV/XLSX/PDF), fall back to OCR+Vision classification

Security
- Preserve originals; never mutate ingested files
- Log access to forensic artifacts for audit

