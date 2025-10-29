import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.services import ingestion as ingestion_module
from backend.app.services.ingestion_worker import IngestionJobAlreadyQueued, IngestionWorker


def test_worker_prevents_duplicate_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    started = threading.Event()
    release = threading.Event()
    processed: list[str] = []

    def handler(task):
        started.set()
        release.wait(timeout=2.0)
        processed.append(task.job_id)

    worker = IngestionWorker(handler, maxsize=2, concurrency=1, name="test-worker")
    worker.start()
    try:
        worker.enqueue("job-1", {"sources": []})
        assert started.wait(timeout=1.0)
        with pytest.raises(IngestionJobAlreadyQueued):
            worker.enqueue("job-1", {"sources": []})
        release.set()
        assert worker.wait_for_idle(timeout=5.0)
    finally:
        release.set()
        worker.stop(timeout=1.0)
    assert processed == ["job-1"]


def test_ingest_endpoint_reports_running_status_during_execution(
    client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestion_module.shutdown_ingestion_worker(timeout=1.0)

    original_handler = ingestion_module._handle_ingestion_task
    started = threading.Event()
    release = threading.Event()

    def blocking_handler(task):
        started.set()
        if not release.wait(timeout=5.0):
            raise TimeoutError("Release signal not received for test handler")
        original_handler(task)

    monkeypatch.setattr(ingestion_module, "_handle_ingestion_task", blocking_handler)
    try:
        ingestion_module.shutdown_ingestion_worker(timeout=1.0)
        ingestion_module.get_ingestion_worker()

        headers = auth_headers_factory()
        status_headers = auth_headers_factory(
            scopes=["ingest:status"],
            roles=["CaseCoordinator"],
            audience=["co-counsel.ingest"],
        )
        response = client.post(
            "/ingest",
            json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
            headers=headers,
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        assert started.wait(timeout=2.0)
        pending_status = client.get(f"/ingest/{job_id}", headers=status_headers)
        assert pending_status.status_code == 202

        release.set()
        worker = ingestion_module.get_ingestion_worker()
        assert worker.wait_for_idle(timeout=10.0)

        completed_status = client.get(f"/ingest/{job_id}", headers=status_headers)
        assert completed_status.status_code == 200
        assert completed_status.json()["status"] == "succeeded"
    finally:
        release.set()
        ingestion_module.shutdown_ingestion_worker(timeout=2.0)
        monkeypatch.setattr(ingestion_module, "_handle_ingestion_task", original_handler)
        ingestion_module.get_ingestion_worker()
