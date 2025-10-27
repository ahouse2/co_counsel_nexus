# Validation Matrix — PRP_Forensics_Core

Linked PRP: [Spec — Forensics Core](PRP_Forensics_Core_spec.md)

## Success Metrics
- **Citation Precision** — Ratio of correctly linked forensic findings to total references in generated reports. Target ≥ 0.98 over rolling 30-day window. Measured via automated diff of report citations against authoritative evidence IDs within `reports/forensics/ground_truth.csv` and adjudicated spot checks.
- **Timeline Accuracy** — Mean absolute deviation between extracted event timestamps and ground-truth chronology for each evidentiary set. Target ≤ 3 minutes per document set. Computed through replay of annotated timelines stored in `datasets/forensics/timelines/ground_truth.jsonl`.
- **Forensics Completeness** — Percentage of expected artifact files (`hash.json`, `metadata.json`, `structure.json`, `authenticity.json`, `financial.json`) produced per processed file. Target ≥ 0.97 with zero silent drops. Calculated via nightly batch audit over processing manifests.

## Required Datasets
- `datasets/forensics/hash_golden/` — Canonical inputs with known SHA-256 digests and tampering variants for hashing regression tests.
- `datasets/forensics/metadata_corpus/` — Mixed media (images, PDFs, emails) annotated with exhaustive metadata to validate extraction coverage and citation pointers.
- `datasets/forensics/structure_suite/` — Curated corrupt and well-formed container files for structure analysis and error handling validation.
- `datasets/forensics/authenticity_benchmark/` — Image sets with labeled manipulations (ELA heatmaps, PRNU baselines) and document edit histories for authenticity scoring calibration.
- `datasets/forensics/financial_ledgers/` — Spreadsheet and PDF statements with reconciled totals and tagged anomalies to verify financial analysis output and timeline synchronization.
- `datasets/forensics/e2e_casefiles/` — Multi-file case bundles with authoritative ground-truth timelines, citations, and expected API responses for end-to-end verification.

## Requirement-to-Test Coverage Matrix
| Requirement (PRP Section) | Unit Test Suite | Integration Suite | End-to-End Suite |
| --- | --- | --- | --- |
| Guarantee SHA-256 hashing for every file (Goals, Outputs) | `tests.unit.forensics.test_hashing::TestSha256Hasher` | `tests.integration.forensics.test_pipeline_io::TestHashArtifactFlow` | `tests.e2e.forensics.test_case_bundle::test_hash_artifacts_present` |
| Capture metadata for supported formats (Goals, Outputs, Methods) | `tests.unit.forensics.test_metadata_extractors::TestPdfMetadataExtractor`, `TestImageMetadataExtractor`, `TestEmailHeaderParser` | `tests.integration.forensics.test_metadata_pipeline::TestMetadataCorpusIngestion` | `tests.e2e.forensics.test_case_bundle::test_metadata_payload_matches_expectations` |
| Perform structure checks on PDFs/images/emails (Goals, Methods) | `tests.unit.forensics.test_structure_analyzers::TestPdfStructureValidator`, `TestImageContainerValidator` | `tests.integration.forensics.test_structure_suite::TestCorruptVsValidDetection` | `tests.e2e.forensics.test_case_bundle::test_structure_alerts_reported` |
| Authenticity analysis (EXIF sanity, ELA, clone detection, PRNU) (Goals, Methods) | `tests.unit.forensics.test_authenticity_signals::TestElaScorer`, `TestCloneDetector`, `TestPrnuMatcher` | `tests.integration.forensics.test_authenticity_pipeline::TestManipulationDetection` | `tests.e2e.forensics.test_case_bundle::test_authenticity_summary_citations` |
| Financial forensics baseline (Goals, Methods) | `tests.unit.forensics.test_financial_analyzer::TestLedgerReconciliation`, `TestEntityExtraction` | `tests.integration.forensics.test_financial_pipeline::TestLedgerAnomalyDetection` | `tests.e2e.forensics.test_case_bundle::test_financial_findings_and_timeline_alignment` |
| Produce complete artifact set per file in storage (Outputs, Artifacts) | `tests.unit.forensics.test_artifact_writers::TestArtifactSchema` | `tests.integration.forensics.test_pipeline_io::TestArtifactPersisted` | `tests.e2e.forensics.test_case_bundle::test_all_artifacts_accessible` |
| Serve GET /forensics/document API (APIs) | `tests.unit.api.test_forensics_document::TestDocumentHandler` | `tests.integration.api.test_forensics_endpoints::TestDocumentEndpointWithPipeline` | `tests.e2e.api.test_public_contract::test_forensics_document_contract` |
| Serve GET /forensics/image API (APIs) | `tests.unit.api.test_forensics_image::TestImageHandler` | `tests.integration.api.test_forensics_endpoints::TestImageEndpointWithPipeline` | `tests.e2e.api.test_public_contract::test_forensics_image_contract` |
| Serve GET /forensics/financial API (APIs) | `tests.unit.api.test_forensics_financial::TestFinancialHandler` | `tests.integration.api.test_forensics_endpoints::TestFinancialEndpointWithPipeline` | `tests.e2e.api.test_public_contract::test_forensics_financial_contract` |
| Maintain chain-of-custody friendly outputs (Goals, Artifacts) | `tests.unit.forensics.test_manifest_builder::TestChainOfCustodyManifest` | `tests.integration.forensics.test_manifest_pipeline::TestManifestConsistency` | `tests.e2e.forensics.test_case_bundle::test_chain_of_custody_report_links` |
| Integration over sample corpus with non-empty fields (Validation) | `tests.unit.forensics.test_validators::TestFieldPresenceValidator` | `tests.integration.forensics.test_corpus_processing::TestCorpusCompleteness` | `tests.e2e.forensics.test_case_bundle::test_report_completeness_metrics` |

## Traceability Notes
- Each suite is parameterized to emit metric deltas for citation precision, timeline accuracy, and forensics completeness into the observability layer so that pass/fail thresholds align with the success metrics above.
- Suites depend on datasets enumerated in this document; ingestion fixtures must validate checksums before execution to preserve evidentiary integrity.
