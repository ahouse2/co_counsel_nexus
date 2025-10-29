from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.services.agents import AgentsService
from backend.app.services.errors import WorkflowAbort
from backend.app.storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord

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
    roles = [turn["role"] for turn in payload["turns"]]
    assert roles == ["strategy", "ingestion", "research", "cocounsel", "qa"]
    assert payload["status"] == "succeeded"
    assert payload["errors"] == []

    qa_scores = payload["qa_scores"]
    assert len(qa_scores) == 15
    assert all(score >= 7.0 for score in qa_scores.values())
    telemetry = payload["telemetry"]
    assert telemetry["sequence_valid"] is True
    assert telemetry["status"] == "succeeded"
    assert telemetry["errors"] == []
    assert telemetry["retries"] == {}
    assert telemetry["turn_roles"] == roles
    assert telemetry["hand_offs"] == [
        {"from": "strategy", "to": "ingestion", "via": "ingestion_audit"},
        {"from": "ingestion", "to": "research", "via": "research_retrieval"},
        {"from": "research", "to": "cocounsel", "via": "forensics_enrichment"},
        {"from": "cocounsel", "to": "qa", "via": "qa_rubric"},
    ]

    memory = payload["memory"]
    assert "plan" in memory and memory["plan"]["steps"]
    assert memory["insights"].get("ingestion", {}).get("status") in {"ready", "empty"}
    assert len(memory.get("turns", [])) == len(roles)

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
    assert thread_payload["memory"]["plan"] == memory["plan"]


class _StubDocumentStore:
    def read_document(self, doc_id: str) -> dict[str, str]:
        return {"type": "text"}

    def list_documents(self) -> list[dict[str, str]]:
        return [{"id": "doc-001", "type": "text"}]


class _StubForensicsService:
    def __init__(self) -> None:
        self.loaded: list[str] = []

    def report_exists(self, doc_id: str, artifact: str) -> bool:
        return True

    def load_artifact(self, doc_id: str, artifact: str) -> dict[str, object]:
        self.loaded.append(doc_id)
        return {"summary": "Clean", "signals": [], "schema_version": "1.0", "stages": []}


class _TransientRetrievalService:
    def __init__(self) -> None:
        self.calls = 0

    def query(self, question: str, page_size: int = 5) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("vector outage")
        return {
            "answer": "Board approval in January 2023, regulatory response in March 2023, integration completes April 2023.",
            "citations": [
                {"docId": "doc-001", "span": "Board approval"},
                {"docId": "doc-002", "span": "Integration window"},
                {"docId": "doc-003", "span": "Regulatory response"},
            ],
            "traces": {
                "vector": [{"id": "vec-1"}],
                "graph": {"nodes": [{"id": "entity::acme"}], "edges": [{"id": "edge::acme"}]},
                "privilege": {"aggregate": {"label": "non-privileged", "score": 0.1}, "decisions": []},
            },
        } 


class _SuccessfulRetrievalService:
    def query(self, question: str, page_size: int = 5) -> dict[str, object]:
        return {
            "answer": "Board approval in January 2023, regulatory response in March 2023, integration completes April 2023.",
            "citations": [
                {"docId": "doc-001", "span": "Board approval"},
                {"docId": "doc-002", "span": "Integration window"},
            ],
            "traces": {
                "vector": [{"id": "vec-1"}],
                "graph": {"nodes": [{"id": "entity::acme"}], "edges": [{"id": "edge::acme"}]},
                "privilege": {"aggregate": {"label": "non-privileged", "score": 0.1}, "decisions": []},
            },
        }


class _AlwaysFailRetrievalService:
    def query(self, question: str, page_size: int = 5) -> dict[str, object]:
        raise ValueError("query filters invalid")


def test_agents_service_retries_transient_error(tmp_path: Path) -> None:
    service = AgentsService(
        retrieval_service=_TransientRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=_StubDocumentStore(),
        memory_store=AgentMemoryStore(tmp_path / "threads"),
    )

    response = service.run_case("case-retry", "Summarise integration milestones.")

    assert response["status"] == "degraded"
    assert len(response["errors"]) == 1
    error = response["errors"][0]
    assert error["code"] == "RETRIEVAL_RUNTIME_ERROR"
    assert error["retryable"] is True
    telemetry = response["telemetry"]
    assert telemetry["status"] == "degraded"
    assert telemetry["retries"].get("retrieval") == 1
    assert telemetry["errors"]
    assert telemetry["turn_roles"] == ["strategy", "ingestion", "research", "cocounsel", "qa"]
    assert telemetry["hand_offs"][-1] == {
        "from": "cocounsel",
        "to": "qa",
        "via": "qa_rubric",
    }
    memory = response["memory"]
    assert memory["plan"]["steps"]
    assert service.memory_store.list_threads()


def test_agents_service_records_failure(tmp_path: Path) -> None:
    service = AgentsService(
        retrieval_service=_AlwaysFailRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=_StubDocumentStore(),
        memory_store=AgentMemoryStore(tmp_path / "threads"),
    )

    with pytest.raises(WorkflowAbort):
        service.run_case("case-failure", "Trigger invalid filters")

    threads = service.memory_store.list_threads()
    assert threads
    payload = service.memory_store.read(threads[0])
    assert payload["status"] == "failed"
    assert payload["errors"][0]["code"] == "RETRIEVAL_INVALID_INPUT"
    assert payload["telemetry"]["status"] == "failed"
    assert payload["telemetry"]["errors"]
    assert [turn["role"] for turn in payload["turns"]] == ["strategy", "ingestion"]


class _CountingMemoryStore(AgentMemoryStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.records: list[AgentThreadRecord] = []

    def write(self, record: AgentThreadRecord) -> None:  # type: ignore[override]
        self.records.append(record)
        super().write(record)


def test_agents_service_persists_memory_each_turn(tmp_path: Path) -> None:
    store = _CountingMemoryStore(tmp_path / "threads")
    service = AgentsService(
        retrieval_service=_SuccessfulRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=_StubDocumentStore(),
        memory_store=store,
    )

    response = service.run_case("case-memory", "Summarise integration milestones.")

    turn_count = len(response["turns"])
    # Five turns -> five per-turn writes + orchestrator final persist + service final snapshot
    assert len(store.records) == turn_count + 2
    intermediate_snapshots = [record.payload.get("memory", {}) for record in store.records[:-1]]
    assert any(snapshot.get("plan", {}).get("steps") for snapshot in intermediate_snapshots)
    assert response["telemetry"]["hand_offs"][-1]["via"] == "qa_rubric"
