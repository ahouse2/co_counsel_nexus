from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest
from PIL import Image
from docx import Document
from pypdf import PdfWriter

from backend.app import config
from backend.app.services.forensics import SCHEMA_VERSION, ForensicsService


@pytest.fixture()
def forensics_service(tmp_path, monkeypatch) -> ForensicsService:
    storage = tmp_path / "forensics"
    monkeypatch.setenv("FORENSICS_DIR", str(storage))
    config.reset_settings_cache()
    return ForensicsService()


def test_document_pipeline_stages(forensics_service: ForensicsService, tmp_path: Path) -> None:
    text_file = tmp_path / "brief.txt"
    text_file.write_text(
        "Table of Contents\n\nSECTION ONE\nAcme Corp entered into a settlement."
    )
    report = forensics_service.build_document_artifact("doc-1", text_file)
    assert report.schema_version == SCHEMA_VERSION
    assert [stage.name for stage in report.stages] == ["canonicalise", "metadata", "analyse"]
    assert report.data["hashes"]["sha256"]
    assert report.metadata["mime_type"].startswith("text/")
    assert report.summary
    stored = forensics_service.load_artifact("doc-1", "document")
    assert stored["schema_version"] == SCHEMA_VERSION


def test_image_low_resolution_fallback(forensics_service: ForensicsService, tmp_path: Path) -> None:
    image_path = tmp_path / "thumb.png"
    image = Image.new("RGB", (64, 64), color=(200, 100, 50))
    image.save(image_path)
    report = forensics_service.build_image_artifact("img-1", image_path)
    assert report.fallback_applied is True
    payload = forensics_service.load_artifact("img-1", "image")
    assert payload["fallback_applied"] is True
    assert payload["data"]["ela"]["mean_absolute_error"] >= 0.0


def test_financial_anomaly_detection(forensics_service: ForensicsService, tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.csv"
    frame = pd.DataFrame(
        {
            "entity": ["Acme", "Acme", "Beta", "Beta", "Omega"],
            "amount": [100, 100, 400, 100, 5000],
            "balance": [100, 105, 110, 111, 9999],
        }
    )
    frame.to_csv(ledger, index=False)
    report = forensics_service.build_financial_artifact("fin-1", ledger)
    totals = report.data["totals"]
    assert Decimal(totals["amount"]) == Decimal("5700")
    assert report.data["anomalies"], "Expected anomalies to be flagged"
    stored = forensics_service.load_artifact("fin-1", "financial")
    assert stored["signals"]


def test_document_pdf_branch(forensics_service: ForensicsService, tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_path = tmp_path / "sample.pdf"
    with pdf_path.open("wb") as handle:
        writer.write(handle)
    report = forensics_service.build_document_artifact("pdf-1", pdf_path)
    analysis = report.data.get("analysis", {})
    assert analysis.get("page_count") == 1
    assert report.metadata["extension"] == ".pdf"


def test_document_docx_branch(forensics_service: ForensicsService, tmp_path: Path) -> None:
    doc_path = tmp_path / "sample.docx"
    document = Document()
    document.add_paragraph("Body paragraph")
    document.save(doc_path)
    report = forensics_service.build_document_artifact("docx-1", doc_path)
    analysis = report.data.get("analysis", {})
    assert analysis.get("paragraph_count", 0) >= 1
    assert any(signal.type == "document.docx.toc" for signal in report.signals)


def test_image_high_resolution_analysis(forensics_service: ForensicsService, tmp_path: Path) -> None:
    image_path = tmp_path / "hires.png"
    image = Image.new("RGB", (256, 256), color=(10, 20, 30))
    image.save(image_path)
    report = forensics_service.build_image_artifact("img-hi", image_path)
    assert report.fallback_applied is False
    assert report.data["ela"]["mean_absolute_error"] >= 0.0
