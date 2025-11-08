name: "Spec — Ingestion with OCR + Vision‑LLM"
version: 0.1

## Requirements
- Folder/directory uploads
- OCR pass on scanned docs (Tesseract or equivalent)
- Vision‑LLM agent (Gemini‑2.5‑Flash by default) to classify, tag, and summarize images and scanned documents
- Store tags/labels in metadata for retrieval and timeline/event extraction

## Pipeline
1) Detect file types and scanned docs
2) OCR scanned docs → text layer
3) Vision‑LLM agent: classification, key fields, document type, quality flags
4) Chunk + embed; persist vectors with enriched metadata
5) Graph triples extraction scheduled post‑ingest

## Validation
- Assert OCR or Vision‑LLM produced text/tags for scanned docs/images
- Metadata contains classification labels

