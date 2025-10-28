from __future__ import annotations

from pathlib import Path

import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.storage.document_store import DocumentStore
from backend.app.storage.job_store import JobStore

def test_document_store_round_trip(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
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
    store = DocumentStore(tmp_path)
    garbage_file = tmp_path / "bad.json"
    garbage_file.write_text("not-json")
    assert store.list_documents() == []


def test_job_store_round_trip(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
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
    store = JobStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read_job("absent")
