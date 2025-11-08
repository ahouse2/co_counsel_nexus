name: "Spec — Forensics Core"
version: 0.1

## Goals
- Guarantee per‑file: cryptographic hash (SHA‑256), metadata capture, structure checks, and authenticity analysis where applicable.
- Provide financial forensics baseline for spreadsheets/PDF statements.
- Produce forensic artifacts and chain‑of‑custody friendly outputs.

## Inputs
- Files from ingestion (docs, images, emails, PDFs, spreadsheets, media)

## Outputs (per file)
- hash.json — { sha256, size, created_at }
- metadata.json — extracted metadata (EXIF, PDF props, email headers)
- structure.json — PDF object map, image/container checks, email header parse
- authenticity.json — image: EXIF sanity, ELA score map, PRNU/clone hits; doc: suspicious edits flags
- financial.json — totals checks, anomalies, entities (payees, accounts)

## APIs
- GET /forensics/document?id=FILE_ID
- GET /forensics/image?id=FILE_ID
- GET /forensics/financial?id=FILE_ID

## Methods (initial toolbox)
- Hashing: hashlib SHA‑256
- Metadata: exifread/Pillow (images), pypdf/pdfminer (PDF), email.parser (EML/MSG)
- Structure: PDF object traversal; JPEG/PNG container integrity checks
- Authenticity: EXIF date/device consistency; Error Level Analysis (ELA); clone/region duplication heuristics; optional PRNU
- Financial: CSV/XLSX parsing; totals reconciliation; outlier detection; named entity extraction (payees, accounts)

## Artifacts
- Stored at ./storage/forensics/{fileId}/

## Validation
- Unit tests for each analyzer; golden samples
- Integration: run across sample corpus; ensure artifact presence and non‑empty fields

