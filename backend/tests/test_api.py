from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict

from fastapi.testclient import TestClient

from backend.app.utils.storage import decrypt_manifest

def _read_job_manifest(job_dir: Path, job_id: str) -> Dict[str, object]:
    manifest = job_dir / f"{job_id}.json"
    assert manifest.exists(), f"Expected manifest {manifest}"
    envelope = manifest.read_text()
    key_path = Path(os.environ["MANIFEST_ENCRYPTION_KEY_PATH"])
    key = key_path.read_bytes()
    return decrypt_manifest(json.loads(envelope), key, associated_data=job_id)


def _wait_for_job_completion(job_dir: Path, job_id: str, timeout: float = 10.0) -> Dict[str, object]:
    deadline = time.time() + timeout
    while True:
        manifest = _read_job_manifest(job_dir, job_id)
        status = manifest.get("status")
        if status in {"succeeded", "failed", "cancelled"}:
            return manifest
        if time.time() >= deadline:
            raise AssertionError(f"Timed out waiting for ingestion job {job_id} to complete")
        time.sleep(0.05)


def _wait_for_job(
    client: TestClient,
    job_id: str,
    *,
    timeout: float = 5.0,
    headers: Dict[str, str] | None = None,
) -> Dict[str, object]:
    deadline = time.time() + timeout
    last_payload: Dict[str, object] | None = None
    while time.time() < deadline:
        request_headers = headers or dict(client.headers)
        response = client.get(f"/ingest/{job_id}", headers=request_headers)
        assert response.status_code in {200, 202}
        last_payload = response.json()
        status_value = last_payload.get("status")
        if status_value in {"succeeded", "failed", "cancelled"}:
            return last_payload
        time.sleep(0.1)
    pytest.fail(f"Ingestion job {job_id} did not reach terminal state; last payload={last_payload}")
def test_ingestion_and_retrieval(
    client: TestClient,
    sample_workspace: Path,
    tmp_path: Path,
    auth_headers_factory,
) -> None:
    headers = auth_headers_factory()
    status_headers = auth_headers_factory(
        scopes=["ingest:status"],
        roles=["CaseCoordinator", "PlatformEngineer"],
        audience=["co-counsel.ingest"],
    )
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
        headers=headers,
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_payload = _wait_for_job(client, job_id, headers=headers)
    assert status_payload["status"] == "succeeded"

    job_manifest = _wait_for_job_completion(Path(os.environ["JOB_STORE_DIR"]), job_id)
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

    query_response = client.get("/query", params={"q": "What happened with Acme?"}, headers=headers)
    assert query_response.status_code == 200
    payload = query_response.json()
    assert "Acme" in payload["answer"]
    assert "Graph analysis highlights" in payload["answer"]
    assert payload["citations"]
    meta = payload["meta"]
    assert meta["page"] == 1
    assert meta["page_size"] == 10
    assert meta["total_items"] >= 1
    assert isinstance(meta["has_next"], bool)
    assert len(payload["citations"]) <= meta["page_size"]
    traces = payload["traces"]
    graph_edges = traces["graph"]["edges"]
    assert any(edge["type"] == "ACQUIRED" for edge in graph_edges)
    assert traces["forensics"]
    assert len(traces["vector"]) <= meta["page_size"]
    privilege = traces["privilege"]
    assert privilege["aggregate"]["label"] in {"non_privileged", "privileged", "unknown"}
    assert isinstance(privilege["decisions"], list)

    timeline_response = client.get("/timeline", headers=headers)
    assert timeline_response.status_code == 200
    timeline_payload = timeline_response.json()
    events = timeline_payload["events"]
    meta = timeline_payload["meta"]
    assert events and any("2024-10-01" in event["summary"] for event in events)
    assert meta["limit"] == 20
    assert meta["has_more"] is False

    graph_response = client.get(
        "/graph/neighbor", params={"id": "entity::acme_corporation"}, headers=headers
    )
    assert graph_response.status_code == 200
    graph_payload = graph_response.json()
    assert graph_payload["nodes"]
    assert any(edge["type"] == "ACQUIRED" for edge in graph_payload["edges"])

    doc_id = doc_map["text"]["id"]
    doc_forensics = client.get("/forensics/document", params={"id": doc_id}, headers=headers)
    assert doc_forensics.status_code == 200
    doc_payload = doc_forensics.json()
    assert doc_payload["data"]["hashes"]["sha256"]
    assert doc_payload["schema_version"]

    image_id = doc_map["image"]["id"]
    image_forensics = client.get("/forensics/image", params={"id": image_id}, headers=headers)
    assert image_forensics.status_code == 200
    image_payload = image_forensics.json()
    assert image_payload["data"]["ela"]["mean_absolute_error"] >= 0.0
    assert image_payload["fallback_applied"] is True

    financial_id = doc_map["financial"]["id"]
    financial_forensics = client.get(
        "/forensics/financial", params={"id": financial_id}, headers=headers
    )
    assert financial_forensics.status_code == 200
    totals = financial_forensics.json()["data"]["totals"]
    assert Decimal(totals["amount"]) == Decimal("600.0")

    status_payload = _wait_for_job(client, job_id, headers=headers)
    status_response = client.get(f"/ingest/{job_id}", headers=headers)
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == job_id
    assert status_payload["status_details"]["ingestion"]["documents"] == 3
    assert status_payload["documents"][0]["metadata"]["checksum_sha256"]


def test_query_filters_and_pagination(
    client: TestClient, sample_workspace: Path, auth_headers_factory
) -> None:
    headers = auth_headers_factory()
    followup = sample_workspace / "followup_notes.txt"
    followup.write_text(
        "Acme Corporation met Contoso Analytics on 2024-08-10 to audit Beta LLC ledgers and discuss compliance."
    )

    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
        headers=headers,
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    _wait_for_job_completion(Path(os.environ["JOB_STORE_DIR"]), job_id)

    first_page = client.get(
        "/query",
        params={"q": "Acme compliance history", "page_size": 1},
        headers=headers,
    )
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert first_payload["meta"]["page"] == 1
    assert first_payload["meta"]["page_size"] == 1
    assert first_payload["meta"]["total_items"] >= 1
    assert len(first_payload["citations"]) <= 1

    second_page = client.get(
        "/query",
        params={"q": "Acme compliance history", "page": 2, "page_size": 1},
        headers=headers,
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert second_payload["meta"]["page"] == 2
    assert second_payload["meta"]["total_items"] == first_payload["meta"]["total_items"]
    assert len(second_payload["citations"]) <= 1

    source_filtered = client.get(
        "/query",
        params={"q": "Acme compliance history", "filters[source]": "local"},
        headers=headers,
    )
    assert source_filtered.status_code == 200

    missing_source = client.get(
        "/query",
        params={"q": "Acme compliance history", "filters[source]": "s3"},
        headers=headers,
    )
    assert missing_source.status_code == 204

    entity_filtered = client.get(
        "/query",
        params={"q": "Acme compliance history", "filters[entity]": "Acme"},
        headers=headers,
    )
    assert entity_filtered.status_code == 200

    missing_entity = client.get(
        "/query",
        params={"q": "Acme compliance history", "filters[entity]": "Gamma"},
        headers=headers,
    )
    assert missing_entity.status_code == 204

    rerank_enabled = client.get(
        "/query",
        params={"q": "Acme compliance history", "rerank": True},
        headers=headers,
    )
    assert rerank_enabled.status_code == 200
    assert rerank_enabled.json()["meta"]["total_items"] >= 1

    invalid_filter = client.get(
        "/query",
        params={"q": "Acme compliance history", "filters[source]": "ftp"},
        headers=headers,
    )
    assert invalid_filter.status_code == 400


def test_timeline_pagination_and_filters(
    client: TestClient, sample_workspace: Path, auth_headers_factory
) -> None:
    from backend.app.storage.timeline_store import TimelineEvent, TimelineStore

    headers = auth_headers_factory()
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
        headers=headers,
    )
    assert response.status_code == 202
    _wait_for_job_completion(Path(os.environ["JOB_STORE_DIR"]), response.json()["job_id"])

    timeline_store = TimelineStore(Path(os.environ["TIMELINE_PATH"]))
    neutral_event = TimelineEvent(
        id="neutral::event::0",
        ts=datetime(2024, 12, 25, 0, 0, 0),
        title="Neutral reference",
        summary="Unrelated year-end milestone",
        citations=["neutral::doc"],
    )
    timeline_store.append([neutral_event])

    default_payload = client.get("/timeline", headers=headers).json()
    assert len(default_payload["events"]) >= 3

    page_one = client.get("/timeline", params={"limit": 1}, headers=headers)
    assert page_one.status_code == 200
    page_one_payload = page_one.json()
    assert page_one_payload["meta"]["has_more"] is True
    cursor = page_one_payload["meta"]["cursor"]
    assert cursor

    page_two = client.get(
        "/timeline", params={"limit": 1, "cursor": cursor}, headers=headers
    )
    assert page_two.status_code == 200
    page_two_payload = page_two.json()
    assert page_two_payload["events"][0]["id"] != page_one_payload["events"][0]["id"]

    entity_payload = client.get(
        "/timeline", params={"entity": "Acme Corporation"}, headers=headers
    ).json()
    assert all(event["id"] != neutral_event.id for event in entity_payload["events"])
    assert "entity_highlights" in entity_payload["events"][0]
    assert "relation_tags" in entity_payload["events"][0]
    assert "confidence" in entity_payload["events"][0]

    ts_threshold = page_two_payload["events"][0]["ts"]
    range_payload = client.get(
        "/timeline", params={"from_ts": ts_threshold}, headers=headers
    ).json()
    assert all(event["ts"] >= ts_threshold for event in range_payload["events"])

    invalid_cursor = client.get("/timeline", params={"cursor": "@@bad"}, headers=headers)
    assert invalid_cursor.status_code == 400
    invalid_payload = invalid_cursor.json()["detail"]
    assert invalid_payload["code"] == "TIMELINE_CURSOR_INVALID"
    assert invalid_payload["component"] == "timeline"
    assert invalid_payload["retryable"] is False

    aware_filter = client.get(
        "/timeline",
        params={"from_ts": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()},
        headers=headers,
    )
    assert aware_filter.status_code == 400
    aware_payload = aware_filter.json()["detail"]
    assert aware_payload["code"] == "TIMELINE_TIMEZONE_AWARE"
    assert "timezone-naive" in aware_payload["message"]


def test_ingestion_validation_errors(client: TestClient, auth_headers_factory) -> None:
    headers = auth_headers_factory()
    bad_source = client.post(
        "/ingest", json={"sources": [{"type": "sharepoint", "credRef": "x"}]}, headers=headers
    )
    assert bad_source.status_code == 202
    bad_job = _wait_for_job_completion(Path(os.environ["JOB_STORE_DIR"]), bad_source.json()["job_id"])
    assert bad_job["status"] == "failed"
    assert any(error.get("code") in {"404", "INGESTION_ERROR"} for error in bad_job["errors"])

    missing_body = client.post("/ingest", json={"sources": []}, headers=headers)
    assert missing_body.status_code == 400


def test_not_found_paths(client: TestClient, auth_headers_factory) -> None:
    headers = auth_headers_factory()
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": "/nonexistent"}]},
        headers=headers,
    )
    assert response.status_code == 202
    manifest = _wait_for_job_completion(Path(os.environ["JOB_STORE_DIR"]), response.json()["job_id"])
    assert manifest["status"] == "failed"
    assert any(error.get("code") == "404" for error in manifest["errors"])

    graph_missing = client.get(
        "/graph/neighbor", params={"id": "entity::Missing"}, headers=headers
    )
    assert graph_missing.status_code == 404

    forensic_missing = client.get(
        "/forensics/document", params={"id": "missing"}, headers=headers
    )
    assert forensic_missing.status_code == 404


def test_ingest_status_not_found(client: TestClient, auth_headers_factory) -> None:
    headers = auth_headers_factory()
    response = client.get("/ingest/unknown-job", headers=headers)
    assert response.status_code == 404

