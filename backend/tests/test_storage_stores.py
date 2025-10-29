from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.storage.document_store import DocumentStore
from backend.app.storage.job_store import JobStore
from backend.app.utils.storage import read_json


def _key() -> bytes:
    return os.urandom(32)


def test_document_store_round_trip(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path, key=_key(), retention_days=30)
    store.write_document("doc-1", {"id": "doc-1", "title": "Doc"})
    payload = store.read_document("doc-1")
    assert payload["title"] == "Doc"

    store.write_document("doc-2", {"id": "doc-2", "title": "Second"})
    documents = store.list_documents()
    ids = {doc["id"] for doc in documents}
    assert ids == {"doc-1", "doc-2"}

    store.remove("doc-1")
    with pytest.raises(FileNotFoundError):
        store.read_document("doc-1")

    store.clear()
    assert store.list_documents() == []


def test_document_store_skips_invalid_json(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path, key=_key(), retention_days=30)
    garbage_file = tmp_path / "bad.json"
    garbage_file.write_text("not-json")
    assert store.list_documents() == []


def test_job_store_round_trip(tmp_path: Path) -> None:
    store = JobStore(tmp_path, key=_key(), retention_days=30)
    manifest = {"job_id": "job-1", "status": "running"}
    store.write_job("job-1", manifest)
    assert store.read_job("job-1")["status"] == "running"

    store.write_job("job-2", {"job_id": "job-2", "status": "queued"})
    jobs = store.list_jobs()
    job_ids = {job["job_id"] for job in jobs}
    assert job_ids == {"job-1", "job-2"}

    store.clear()
    assert store.list_jobs() == []


def test_job_store_missing_file(tmp_path: Path) -> None:
    store = JobStore(tmp_path, key=_key(), retention_days=30)
    with pytest.raises(FileNotFoundError):
        store.read_job("absent")


def test_job_store_retention_prunes_expired(tmp_path: Path) -> None:
    store = JobStore(tmp_path, key=_key(), retention_days=1)
    job_id = "job-expire"
    store.write_job(job_id, {"job_id": job_id, "status": "queued"})
    manifest_file = next(tmp_path.glob("*.json"))
    envelope = read_json(manifest_file)
    envelope["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    manifest_file.write_text(json.dumps(envelope))
    with pytest.raises(FileNotFoundError):
        store.read_job(job_id)
    assert store.list_jobs() == []
