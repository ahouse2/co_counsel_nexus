# 2025-11-24 – Knowledge Hub Release Validation

## Overview
- Hardened knowledge service dependencies, telemetry spans, and frontend testing harness to stabilise curated legal resource delivery.
- Added roadmap notes capturing dependency remediation, telemetry instrumentation, and verification plan.

## Commands Executed
- `pytest backend/tests/test_knowledge.py -q` 【2ab5f9†L1-L33】
- `pytest backend/tests -q` 【2789ea†L1-L40】
- `npx vitest run tests/knowledgeHub.test.tsx` 【c924ac†L1-L11】

## Notable Changes
- Installed missing Python packages: email-validator, pandas, piexif, python-docx, extract-msg, mail-parser, pikepdf, pypdf, scikit-learn, boto3, Office365-REST-Python-Client.
- Ensured embedding creation falls back to local shim when HuggingFace integration absent.
- Updated mTLS validity window handling to support `cryptography` 41+ API changes.
- Expanded retrieval telemetry spans and aligned dummy services/tests with production contracts.
- Normalised Testing Library queries to tolerate duplicate headings/snippets in KnowledgeHub component.

## Follow-ups
- Document dependency pin updates for CI/uv lockfile refresh.
- Monitor FastAPI `on_event` deprecation warnings for eventual lifespan migration.
