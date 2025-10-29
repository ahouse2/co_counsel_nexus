import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.services import ingestion as ingestion_module
from backend.app.services.ingestion_worker import (
    IngestionJobAlreadyQueued,
    IngestionTaskRetry,
    IngestionWorker,
)


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


def test_worker_retries_after_retry_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    def handler(task):
        attempts.append(task.job_id)
        if len(attempts) < 2:
            raise IngestionTaskRetry("transient failure")

    worker = IngestionWorker(
        handler,
        maxsize=1,
        concurrency=1,
        name="retry-worker",
        max_retries=2,
        retry_backoff=0.0,
    )
    worker.start()
    try:
        worker.enqueue("job-retry", {"sources": []})
        assert worker.wait_for_idle(timeout=5.0)
    finally:
        worker.stop(timeout=1.0)
    assert attempts == ["job-retry", "job-retry"]


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


def test_ingestion_pipeline_emits_ocr_metadata(
    client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestion_module.shutdown_ingestion_worker(timeout=1.0)
    worker = ingestion_module.get_ingestion_worker()

    def fake_image_to_data(image, lang, config, output_type):  # noqa: D401 - test helper
        return {
            "text": ["Acme", "2024-10-02"],
            "conf": ["92", "88"],
            "left": [0, 60],
            "top": [0, 0],
            "width": [40, 80],
            "height": [20, 20],
        }

    monkeypatch.setattr(
        "backend.ingestion.ocr.pytesseract.image_to_data",
        fake_image_to_data,
    )

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

    assert worker.wait_for_idle(timeout=10.0)

    status_response = client.get(f"/ingest/{job_id}", headers=status_headers)
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["status"] == "succeeded"
    documents = payload["documents"]
    assert documents, "Expected at least one ingested document"
    graph_details = payload["status_details"]["graph"]
    assert graph_details["nodes"] > 0
    assert graph_details["triples"] >= 0

    ingested_doc = documents[0]
    doc_id = ingested_doc["id"]
    service = ingestion_module.get_ingestion_service()
    stored = service.document_store.read_document(doc_id)
    assert stored.get("chunk_count", 0) > 0
    assert stored.get("entity_labels"), "Entity labels should be captured"
    assert stored.get("ocr_confidence") is not None
    ingestion_module.shutdown_ingestion_worker(timeout=1.0)


def test_ingestion_emits_queue_and_status_metrics(
    client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingestion_module.shutdown_ingestion_worker(timeout=1.0)

    queue_events: list[tuple[str, str, dict[str, object]]] = []
    transitions: list[tuple[str, str | None, str]] = []

    def capture_queue_event(job_id: str, event: str, *, reason: str | None = None) -> None:
        payload: dict[str, object] = {"event": event}
        if reason:
            payload["reason"] = reason
        queue_events.append((job_id, event, payload))

    def capture_transition(job_id: str, previous: str | None, new: str) -> None:
        transitions.append((job_id, previous, new))

    monkeypatch.setattr(ingestion_module, "record_queue_event", capture_queue_event)
    monkeypatch.setattr(ingestion_module, "record_job_transition", capture_transition)

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

    worker = ingestion_module.get_ingestion_worker()
    assert worker.wait_for_idle(timeout=10.0)

    status_response = client.get(f"/ingest/{job_id}", headers=status_headers)
    assert status_response.status_code == 200

    assert any(event == "enqueued" for _, event, _ in queue_events)
    assert any(event == "claimed" for _, event, _ in queue_events)
    assert any(new == "succeeded" for _, _, new in transitions)
    assert any(previous == "queued" and new == "running" for _, previous, new in transitions)

    ingestion_module.shutdown_ingestion_worker(timeout=1.0)
