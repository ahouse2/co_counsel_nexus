import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture()
def agents_client(tmp_path, monkeypatch) -> TestClient:
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
    monkeypatch.setenv("AGENT_THREADS_DIR", str(storage_root / "agent_threads"))

    from backend.app import config
    from backend.app.services import agents as agents_service
    from backend.app.services import graph as graph_service
    from backend.app.services import vector as vector_service

    config.reset_settings_cache()
    vector_service.reset_vector_service()
    graph_service.reset_graph_service()
    agents_service.reset_agents_service()

    main_module = importlib.import_module("backend.app.main")
    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture()
def sample_workspace(tmp_path: Path) -> Path:
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


def _ingest_sample(client: TestClient, sample_workspace: Path) -> None:
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(sample_workspace)}]},
    )
    assert response.status_code == 202


def test_agents_workflow_generates_thread(
    agents_client: TestClient,
    sample_workspace: Path,
) -> None:
    _ingest_sample(agents_client, sample_workspace)

    question = "Summarise the acquisition timeline for Acme."
    run_response = agents_client.post(
        "/agents/run",
        json={"case_id": "case-001", "question": question},
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

    thread_response = agents_client.get(f"/agents/threads/{thread_id}")
    assert thread_response.status_code == 200
    thread_payload = thread_response.json()
    assert thread_payload["thread_id"] == thread_id
    assert thread_payload["qa_scores"] == qa_scores

    list_response = agents_client.get("/agents/threads")
    assert list_response.status_code == 200
    assert thread_id in list_response.json()["threads"]

    expected_average = sum(qa_scores.values()) / len(qa_scores)
    assert payload["telemetry"].get("qa_average") == pytest.approx(expected_average, rel=1e-3)
