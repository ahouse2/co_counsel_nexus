from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app import config
from backend.app.services.forensics import ForensicsService
from backend.app.storage.forensics_chain import ForensicsChainLedger
from backend.tools import verify_forensics_chain as verify_cli


def test_chain_ledger_append_and_verify(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = ForensicsChainLedger(ledger_path)
    first = ledger.append("tester", "ingest", {"file_id": "doc-1"})
    second = ledger.append("tester", "analyze", {"file_id": "doc-1", "checksum": "123"})

    assert second.prev_hash == first.digest
    ok, issues = ledger.verify()
    assert ok is True
    assert issues == []


def test_chain_ledger_detects_tampering(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = ForensicsChainLedger(ledger_path)
    ledger.append("tester", "create", {"file_id": "doc-1"})
    ledger.append("tester", "update", {"file_id": "doc-1"})

    lines = ledger_path.read_text().splitlines()
    tampered = json.loads(lines[1])
    tampered["payload"]["file_id"] = "doc-2"
    lines[1] = json.dumps(tampered)
    ledger_path.write_text("\n".join(lines) + "\n")

    ok, issues = ledger.verify()
    assert ok is False
    assert issues
    assert "digest" in issues[0] or "prev_hash" in issues[0]


def test_chain_cli_reports_status(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = ForensicsChainLedger(ledger_path)
    ledger.append("tester", "create", {"file_id": "doc-1"})
    exit_code = verify_cli.main(["--path", str(ledger_path), "--json"])
    assert exit_code == 0


def test_forensics_service_appends_ledger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    forensics_dir = tmp_path / "forensics"
    monkeypatch.setenv("FORENSICS_CHAIN_PATH", str(ledger_path))
    monkeypatch.setenv("FORENSICS_DIR", str(forensics_dir))
    config.reset_settings_cache()

    service = ForensicsService()
    sample = tmp_path / "document.txt"
    sample.write_text("Key evidence line")
    service.build_document_artifact("doc-ledger", sample)

    ledger = ForensicsChainLedger(ledger_path)
    entries = list(ledger.iter_entries())
    assert entries
    assert any(entry.payload.get("file_id") == "doc-ledger" for entry in entries)

    config.reset_settings_cache()
