from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def agents_client(client: TestClient) -> TestClient:
    from backend.app.services import agents as agents_service

    agents_service.reset_agents_service()
    return client


def _ingest_sample(client: TestClient, sample_workspace: Path, headers: dict[str, str]) -> None:
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
        headers=headers,
    )
    assert response.status_code == 202


def test_agents_workflow_generates_thread(
    agents_client: TestClient,
    sample_workspace: Path,
    auth_headers_factory,
) -> None:
    headers = auth_headers_factory()
    _ingest_sample(agents_client, sample_workspace, headers)

    question = "Summarise the acquisition timeline for Acme."
    run_response = agents_client.post(
        "/agents/run",
        json={"case_id": "case-001", "question": question},
        headers=headers,
    )
    assert run_response.status_code == 200
    payload = run_response.json()

    assert payload["case_id"] == "case-001"
    assert payload["question"] == question
    assert payload["final_answer"]
    assert payload["citations"], "Expected citations in agent run response"
    assert len(payload["turns"]) == 3
    assert {turn["role"] for turn in payload["turns"]} == {"research", "forensics", "qa"}

    qa_scores = payload["qa_scores"]
    assert len(qa_scores) == 15
    assert all(score >= 7.0 for score in qa_scores.values())
    assert payload["telemetry"]["sequence_valid"] is True

    thread_id = payload["thread_id"]

    thread_response = agents_client.get(
        f"/agents/threads/{thread_id}", headers=headers
    )
    assert thread_response.status_code == 200
    thread_payload = thread_response.json()
    assert thread_payload["thread_id"] == thread_id
    assert thread_payload["qa_scores"] == qa_scores

    list_response = agents_client.get("/agents/threads", headers=headers)
    assert list_response.status_code == 200
    assert thread_id in list_response.json()["threads"]

    expected_average = sum(qa_scores.values()) / len(qa_scores)
    assert payload["telemetry"].get("qa_average") == pytest.approx(expected_average, rel=1e-3)
