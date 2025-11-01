from __future__ import annotations

import random
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.services.agents import AdaptivePolicyEngine, AgentsService
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
        json={"case_id": "case-001", "question": question, "autonomy_level": "high"},
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
    assert telemetry["branching"] == []
    assert telemetry["plan_revisions"] == 0
    assert telemetry["hand_offs"] == [
        {"from": "strategy", "to": "ingestion", "via": "ingestion_audit"},
        {"from": "ingestion", "to": "research", "via": "research_retrieval"},
        {"from": "research", "to": "cocounsel", "via": "forensics_enrichment"},
        {"from": "cocounsel", "to": "qa", "via": "qa_rubric"},
    ]
    assert telemetry["autonomy_level"] == "high"
    assert telemetry["total_duration_ms"] >= 0

    delegators = {entry["from"] for entry in telemetry["delegations"]}
    assert {"Strategy", "Ingestion", "Research", "CoCounsel", "QA"}.issubset(delegators)
    assert all(entry["metadata"] for entry in telemetry["delegations"])

    memory = payload["memory"]
    assert "plan" in memory and memory["plan"]["steps"]
    assert memory["insights"].get("ingestion", {}).get("status") in {"ready", "empty"}
    assert len(memory.get("turns", [])) == len(roles)
    conversation = memory.get("conversation", [])
    assert conversation and conversation[0]["role"] == "user"
    agent_names = [entry.get("name") for entry in conversation if entry.get("role") == "agent"]
    assert agent_names == ["Strategy", "Ingestion", "Research", "CoCounsel", "QA"]

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


class _FlakyDocumentStore(_StubDocumentStore):
    def __init__(self) -> None:
        super().__init__()
        self.invocations = 0

    def list_documents(self) -> list[dict[str, str]]:  # type: ignore[override]
        self.invocations += 1
        if self.invocations <= 2:
            raise RuntimeError("workspace manifest unavailable")
        return super().list_documents()


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


class _ReplanRetrievalService:
    def __init__(self) -> None:
        self.calls = 0

    def query(self, question: str, page_size: int = 5) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            return {
                "answer": "",
                "citations": [],
                "traces": {
                    "vector": [],
                    "graph": {"nodes": [], "edges": []},
                    "privilege": {"aggregate": {"label": "non-privileged", "score": 0.05}},
                },
            }
        return _SuccessfulRetrievalService().query(question, page_size)


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
    telemetry = response["telemetry"]
    assert telemetry["status"] == "degraded"
    assert telemetry["retries"].get("retrieval") == 1
    assert telemetry["errors"][0]["code"] == "RETRIEVAL_RUNTIME_ERROR"
    assert telemetry["hand_offs"][-1] == {
        "from": "cocounsel",
        "to": "qa",
        "via": "qa_rubric",
    }
    assert response["memory"]["conversation"][0]["role"] == "user"


def test_agents_service_replans_on_empty_citations(tmp_path: Path) -> None:
    service = AgentsService(
        retrieval_service=_ReplanRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=_StubDocumentStore(),
        memory_store=AgentMemoryStore(tmp_path / "threads"),
    )

    response = service.run_case("case-replan", "Summarise integration milestones.")

    assert response["status"] == "succeeded"
    telemetry = response["telemetry"]
    assert telemetry["plan_revisions"] == 1
    assert telemetry["branching"]
    assert any(branch["reason"] == "missing_citations" for branch in telemetry["branching"])
    assert any("revision" in note for note in telemetry["notes"])
    turns = response["turns"]
    strategy_turns = [turn for turn in turns if turn["role"] == "strategy"]
    assert len(strategy_turns) == 2
    assert strategy_turns[-1]["annotations"]["plan_revision"] == 1
    assert response["memory"]["conversation"][1]["name"] == "Strategy"


def test_agents_service_records_failure(tmp_path: Path) -> None:
    service = AgentsService(
        retrieval_service=_AlwaysFailRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=_StubDocumentStore(),
        memory_store=AgentMemoryStore(tmp_path / "threads"),
    )

    with pytest.raises(WorkflowAbort):
        service.run_case("case-failure", "Trigger invalid filters", autonomy_level="low")

    threads = service.memory_store.list_threads()
    assert threads
    payload = service.memory_store.read(threads[0])
    assert payload["status"] == "failed"
    assert payload["errors"][0]["code"] == "RETRIEVAL_INVALID_INPUT"
    assert payload["telemetry"]["status"] == "failed"
    assert payload["turns"][-1]["action"].endswith("failed")


def test_agents_service_allows_partial_success(tmp_path: Path) -> None:
    service = AgentsService(
        retrieval_service=_AlwaysFailRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=_StubDocumentStore(),
        memory_store=AgentMemoryStore(tmp_path / "threads"),
    )

    response = service.run_case("case-partial", "Trigger invalid filters", autonomy_level="balanced")

    assert response["status"] == "degraded"
    telemetry = response["telemetry"]
    assert telemetry["status"] == "degraded"
    assert telemetry["branching"]
    assert telemetry["plan_revisions"] >= 1
    assert any(turn["action"].endswith("failed") for turn in response["turns"])
    assert response["errors"]
    assert any(entry.get("name") == "Strategy" for entry in response["memory"]["conversation"])


@pytest.mark.parametrize("seed", [1, 7, 21])
def test_agents_policy_rewires_graph_across_seeds(tmp_path: Path, seed: int) -> None:
    document_store = _FlakyDocumentStore()
    policy_settings = SimpleNamespace(
        agents_policy_enabled=True,
        agents_policy_initial_trust=0.5,
        agents_policy_trust_threshold=0.4,
        agents_policy_decay=0.0,
        agents_policy_success_reward=0.15,
        agents_policy_failure_penalty=0.6,
        agents_policy_exploration_probability=0.5,
        agents_policy_seed=seed,
        agents_policy_observable_roles=("strategy", "ingestion", "research", "cocounsel", "qa"),
        agents_policy_suppressible_roles=("ingestion", "cocounsel"),
    )
    policy_engine = AdaptivePolicyEngine(policy_settings)
    service = AgentsService(
        retrieval_service=_SuccessfulRetrievalService(),
        forensics_service=_StubForensicsService(),
        document_store=document_store,
        memory_store=AgentMemoryStore(tmp_path / f"threads-policy-{seed}"),
        policy_engine=policy_engine,
    )
    question = "Summarise integration milestones."
    case_prefix = f"case-policy-{seed}"

    with pytest.raises(WorkflowAbort):
        service.run_case(f"{case_prefix}-1", question, autonomy_level="balanced")

    first_decision = policy_engine.last_decision
    assert first_decision is not None
    expected_exploration = random.Random(seed).random() < policy_settings.agents_policy_exploration_probability
    assert first_decision.exploration == expected_exploration

    with pytest.raises(WorkflowAbort):
        service.run_case(f"{case_prefix}-2", question, autonomy_level="balanced")

    response = service.run_case(f"{case_prefix}-3", question, autonomy_level="balanced")
    telemetry = response["telemetry"]
    policy_snapshot = telemetry["policy"]

    assert policy_snapshot["enabled"] is True
    assert "ingestion" in policy_snapshot["suppressed_roles"]
    assert policy_snapshot["graph_overrides"]["strategy"] == ["research"]
    roles = [turn["role"] for turn in response["turns"]]
    assert "ingestion" not in roles
    assert policy_snapshot["trust"]["ingestion"] < policy_settings.agents_policy_trust_threshold
    assert policy_engine.state()["ingestion"] < policy_settings.agents_policy_trust_threshold


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
    assert len(store.records) == turn_count + 2
    intermediate_snapshots = [record.payload.get("memory", {}) for record in store.records[:-1]]
    assert any(snapshot.get("plan", {}).get("steps") for snapshot in intermediate_snapshots)
    assert response["telemetry"]["hand_offs"][-1]["via"] == "qa_rubric"
    assert [entry.get("name") for entry in response["memory"]["conversation"] if entry.get("role") == "agent"] == [
        "Strategy",
        "Ingestion",
        "Research",
        "CoCounsel",
        "QA",
    ]
