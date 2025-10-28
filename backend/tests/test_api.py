from __future__ import annotations

import importlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from PIL import Image

@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setenv("NEO4J_URI", "memory://")
    monkeypatch.setenv("QDRANT_PATH", ":memory:")
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.setenv("VECTOR_DIR", str(storage_root / "vector"))
    monkeypatch.setenv("FORENSICS_DIR", str(storage_root / "forensics"))
    monkeypatch.setenv("TIMELINE_PATH", str(storage_root / "timeline.jsonl"))
    monkeypatch.setenv("JOB_STORE_DIR", str(storage_root / "jobs"))
    monkeypatch.setenv("DOCUMENT_STORE_DIR", str(storage_root / "documents"))

    from backend.app import config
    from backend.app.services import graph as graph_service
    from backend.app.services import vector as vector_service

    config.reset_settings_cache()
    vector_service.reset_vector_service()
    graph_service.reset_graph_service()

    main_module = importlib.import_module("backend.app.main")
    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture()
def sample_workspace(tmp_path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    text = root / "case_notes.txt"
    text.write_text(
        "Acme Corporation acquired Beta LLC on 2024-10-01 after the initial filing on 2024-09-15."
    )
    image = root / "evidence.png"
    img = Image.new("RGB", (16, 16), color=(123, 45, 67))
    img.save(image)
    csv_file = root / "ledger.csv"
    csv_file.write_text("entity,amount\nAcme,100.0\nBeta,100.0\nBeta,400.0\n")
    return root


def _read_job_manifest(job_dir: Path, job_id: str) -> Dict[str, object]:
    manifest = job_dir / f"{job_id}.json"
    assert manifest.exists(), f"Expected manifest {manifest}"
    return json.loads(manifest.read_text())


def test_ingestion_and_retrieval(client: TestClient, sample_workspace: Path, tmp_path: Path) -> None:
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_manifest = _read_job_manifest(Path(os.environ["JOB_STORE_DIR"]), job_id)
    documents = job_manifest["documents"]
    assert len(documents) == 3
    doc_map = {doc["type"]: doc for doc in documents}
    assert job_manifest["status"] == "succeeded"
    ingestion_details = job_manifest["status_details"]["ingestion"]
    assert ingestion_details["documents"] == 3
    assert not ingestion_details["skipped"]
    assert job_manifest["status_details"]["timeline"]["events"] >= 1
    status_details = job_manifest["status_details"]
    graph_details = status_details["graph"]
    assert graph_details["nodes"] == 5
    assert graph_details["edges"] == 3
    assert graph_details["triples"] == 1
    forensics_details = status_details["forensics"]
    assert len(forensics_details["artifacts"]) == 3
    assert forensics_details["last_run_at"] is not None
    for artifact in forensics_details["artifacts"]:
        assert artifact["schema_version"]
        assert artifact["report_path"].endswith("report.json")
        assert artifact["document_id"]
        assert artifact["type"] in {"document", "image", "financial"}
    for doc in documents:
        metadata = doc["metadata"]
        assert metadata["checksum_sha256"]
        assert metadata["ingested_uri"].startswith("/")

    query_response = client.get("/query", params={"q": "What happened with Acme?"})
    assert query_response.status_code == 200
    payload = query_response.json()
    assert "Acme" in payload["answer"]
    assert "Graph analysis highlights" in payload["answer"]
    assert payload["citations"]
    traces = payload["traces"]
    graph_edges = traces["graph"]["edges"]
    assert any(edge["type"] == "ACQUIRED" for edge in graph_edges)
    assert traces["forensics"]

    timeline_response = client.get("/timeline")
    assert timeline_response.status_code == 200
    timeline_payload = timeline_response.json()
    events = timeline_payload["events"]
    meta = timeline_payload["meta"]
    assert events and any("2024-10-01" in event["summary"] for event in events)
    assert meta["limit"] == 20
    assert meta["has_more"] is False

    graph_response = client.get("/graph/neighbor", params={"id": "entity::acme_corporation"})
    assert graph_response.status_code == 200
    graph_payload = graph_response.json()
    assert graph_payload["nodes"]
    assert any(edge["type"] == "ACQUIRED" for edge in graph_payload["edges"])

    doc_id = doc_map["text"]["id"]
    doc_forensics = client.get("/forensics/document", params={"id": doc_id})
    assert doc_forensics.status_code == 200
    doc_payload = doc_forensics.json()
    assert doc_payload["data"]["hashes"]["sha256"]
    assert doc_payload["schema_version"]

    image_id = doc_map["image"]["id"]
    image_forensics = client.get("/forensics/image", params={"id": image_id})
    assert image_forensics.status_code == 200
    image_payload = image_forensics.json()
    assert image_payload["data"]["ela"]["mean_absolute_error"] >= 0.0
    assert image_payload["fallback_applied"] is True

    financial_id = doc_map["financial"]["id"]
    financial_forensics = client.get("/forensics/financial", params={"id": financial_id})
    assert financial_forensics.status_code == 200
    totals = financial_forensics.json()["data"]["totals"]
    assert Decimal(totals["amount"]) == Decimal("600.0")

    status_response = client.get(f"/ingest/{job_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == job_id
    assert status_payload["status"] == "succeeded"
    assert status_payload["status_details"]["ingestion"]["documents"] == 3
    assert status_payload["documents"][0]["metadata"]["checksum_sha256"]


def test_timeline_pagination_and_filters(client: TestClient, sample_workspace: Path) -> None:
    from backend.app.storage.timeline_store import TimelineEvent, TimelineStore

    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
    )
    assert response.status_code == 202

    timeline_store = TimelineStore(Path(os.environ["TIMELINE_PATH"]))
    neutral_event = TimelineEvent(
        id="neutral::event::0",
        ts=datetime(2024, 12, 25, 0, 0, 0),
        title="Neutral reference",
        summary="Unrelated year-end milestone",
        citations=["neutral::doc"],
    )
    timeline_store.append([neutral_event])

    default_payload = client.get("/timeline").json()
    assert len(default_payload["events"]) >= 3

    page_one = client.get("/timeline", params={"limit": 1})
    assert page_one.status_code == 200
    page_one_payload = page_one.json()
    assert page_one_payload["meta"]["has_more"] is True
    cursor = page_one_payload["meta"]["cursor"]
    assert cursor

    page_two = client.get("/timeline", params={"limit": 1, "cursor": cursor})
    assert page_two.status_code == 200
    page_two_payload = page_two.json()
    assert page_two_payload["events"][0]["id"] != page_one_payload["events"][0]["id"]

    entity_payload = client.get("/timeline", params={"entity": "Acme Corporation"}).json()
    assert all(event["id"] != neutral_event.id for event in entity_payload["events"])

    ts_threshold = page_two_payload["events"][0]["ts"]
    range_payload = client.get("/timeline", params={"from_ts": ts_threshold}).json()
    assert all(event["ts"] >= ts_threshold for event in range_payload["events"])

    invalid_cursor = client.get("/timeline", params={"cursor": "@@bad"})
    assert invalid_cursor.status_code == 400

    aware_filter = client.get(
        "/timeline",
        params={"from_ts": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()},
    )
    assert aware_filter.status_code == 400
    assert "timezone-naive" in aware_filter.json()["detail"]


def test_ingestion_validation_errors(client: TestClient) -> None:
    bad_source = client.post("/ingest", json={"sources": [{"type": "sharepoint", "credRef": "x"}]})
    assert bad_source.status_code in {404, 503}
    assert bad_source.json()["detail"]

    missing_body = client.post("/ingest", json={"sources": []})
    assert missing_body.status_code == 400


def test_not_found_paths(client: TestClient) -> None:
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": "/nonexistent"}]},
    )
    assert response.status_code == 404

    graph_missing = client.get("/graph/neighbor", params={"id": "entity::Missing"})
    assert graph_missing.status_code == 404

    forensic_missing = client.get("/forensics/document", params={"id": "missing"})
    assert forensic_missing.status_code == 404


def test_ingest_status_not_found(client: TestClient) -> None:
    response = client.get("/ingest/unknown-job")
    assert response.status_code == 404

