from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.storage.job_store import JobStore


def _perform_ingestion(client: TestClient, workspace: Path, auth_headers_factory) -> None:
    headers = auth_headers_factory()
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(workspace)}]},
        headers=headers,
    )
    assert response.status_code == 202


def test_query_requires_scope(
    client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
) -> None:
    _perform_ingestion(client, sample_workspace, auth_headers_factory)
    headers = auth_headers_factory(scopes=["timeline:read"], roles=["ResearchAnalyst"], audience=["co-counsel.query"])
    response = client.get("/query", params={"q": "Acme"}, headers=headers)
    assert response.status_code == 403
    assert "scope" in response.json()["detail"].lower()


def test_case_coordinator_traces_redacted_without_trace_scope(
    client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
) -> None:
    _perform_ingestion(client, sample_workspace, auth_headers_factory)
    headers = auth_headers_factory(
        scopes=["query:read", "timeline:read"],
        roles=["CaseCoordinator"],
        audience=["co-counsel.query"],
    )
    response = client.get("/query", params={"q": "Acme"}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["traces"]["vector"] == []
    assert payload["traces"]["graph"] == {"nodes": [], "edges": []}
    assert payload["traces"]["forensics"] == []


def test_research_analyst_blocked_until_ingest_complete(
    client: TestClient,
    auth_headers_factory,
) -> None:
    job_store_dir = Path(os.environ["JOB_STORE_DIR"])
    job_store = JobStore(job_store_dir)
    job_id = "job-running"
    job_store.write_job(
        job_id,
        {
            "job_id": job_id,
            "status": "running",
            "submitted_at": "2025-11-12T00:00:00Z",
            "updated_at": "2025-11-12T00:00:00Z",
            "documents": [],
            "errors": [],
            "status_details": {
                "ingestion": {"documents": 0, "skipped": []},
                "timeline": {"events": 0},
                "forensics": {"artifacts": [], "last_run_at": None},
                "graph": {"nodes": 0, "edges": 0, "triples": 0},
            },
        },
    )
    headers = auth_headers_factory(
        scopes=["ingest:status"],
        roles=["ResearchAnalyst"],
        audience=["co-counsel.ingest"],
    )
    response = client.get(f"/ingest/{job_id}", headers=headers)
    assert response.status_code == 403


def test_automation_service_denied_query(
    client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
) -> None:
    _perform_ingestion(client, sample_workspace, auth_headers_factory)
    headers = auth_headers_factory(
        scopes=["query:read"],
        roles=["AutomationService"],
        audience=["co-counsel.query"],
    )
    response = client.get("/query", params={"q": "Acme"}, headers=headers)
    assert response.status_code == 403
