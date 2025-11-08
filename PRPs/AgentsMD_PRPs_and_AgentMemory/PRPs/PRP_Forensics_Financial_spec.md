name: "Spec — Financial Forensics"
version: 0.1

## Scope
- Analyze financial documents (PDF/CSV/XLSX) to detect anomalies, inconsistencies, and extract entities.
- Optional: generate leads for hidden assets (heuristics + OSINT APIs where available).

## Inputs/Outputs
- Input: file id
- Output: financial.json with totals, anomalies, entities, summary; optional leads.json

## Methods
- Parsing: pandas/openpyxl/tabula as appropriate
- Checks: totals consistency, duplicates, missing entries, unusual spikes, counterparty anomalies
- Entities: names, accounts, institutions, addresses
- Leads: optional OSINT hooks (config‑gated)

