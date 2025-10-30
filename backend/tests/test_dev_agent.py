from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.dev_agent import DevAgentService, get_dev_agent_service, reset_dev_agent_service
from backend.app.storage.agent_memory_store import AgentMemoryStore


@dataclass
class _FakeCommand:
    command: List[str]
    return_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 10.0

    def to_json(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
        }


@dataclass
class _FakeExecution:
    success: bool
    workspace_id: str
    commands: List[_FakeCommand] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        return {
            "success": self.success,
            "workspace_id": self.workspace_id,
            "commands": [command.to_json() for command in self.commands],
        }


class _FakeSandbox:
    def __init__(self) -> None:
        self._queue: list[_FakeExecution] = []
        self.calls: list[str] = []

    def enqueue(self, execution: _FakeExecution) -> None:
        self._queue.append(execution)

    def validate(self, diff: str) -> _FakeExecution:
        self.calls.append(diff)
        if not self._queue:
            raise AssertionError("Sandbox validate called without queued execution")
        return self._queue.pop(0)


@pytest.fixture()
def dev_agent_test_service(tmp_path_factory: pytest.TempPathFactory) -> tuple[DevAgentService, _FakeSandbox]:
    sandbox = _FakeSandbox()
    store_root = tmp_path_factory.mktemp("dev-agent-store")
    service = DevAgentService(memory_store=AgentMemoryStore(store_root), sandbox=sandbox)
    reset_dev_agent_service()
    app.dependency_overrides[get_dev_agent_service] = lambda: service
    yield service, sandbox
    app.dependency_overrides.pop(get_dev_agent_service, None)
    reset_dev_agent_service()


def _dev_agent_headers(auth_headers_factory):
    return auth_headers_factory(
        scopes=["dev-agent:admin"],
        roles=["PlatformEngineer"],
        audience=["co-counsel.dev-agent"],
    )


def _seed_backlog(service: DevAgentService) -> str:
    task = service.record_feature_request(
        request_id="FR-001",
        title="Enable sandbox smoke tests",
        description="Add CI smoke tests for the dev agent sandbox",
        priority="high",
        requested_by={"name": "Case Coordinator"},
        metadata={"region": "us-east-1"},
        tags=["automation", "quality"],
        planner_notes=["Ensure commands are idempotent"],
        risk_score=0.4,
    )
    proposal = service.create_proposal(
        task.task_id,
        actor={"subject": "dev-bot", "roles": ["AutomationService"]},
        title="Add sandbox smoke tests",
        summary="Introduces a minimal pytest suite executed inside the sandbox.",
        diff="diff --git a/file b/file",
        rationale=["Catches regressions before promotion"],
    )
    return proposal.proposal_id


def test_dev_agent_proposals_returns_backlog(
    client: TestClient,
    auth_headers_factory,
    dev_agent_test_service,
) -> None:
    service, sandbox = dev_agent_test_service
    _seed_backlog(service)
    sandbox.enqueue(_FakeExecution(success=True, workspace_id="ws-123", commands=[]))

    headers = _dev_agent_headers(auth_headers_factory)
    response = client.get("/dev-agent/proposals", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert "backlog" in payload
    assert len(payload["backlog"]) == 1

    task = payload["backlog"][0]
    assert task["status"] == "triaged"
    assert task["planner_notes"] == ["Ensure commands are idempotent"]
    assert task["metadata"]["region"] == "us-east-1"
    assert len(task["proposals"]) == 1
    proposal = task["proposals"][0]
    assert proposal["title"] == "Add sandbox smoke tests"
    assert proposal["status"] == "pending"
    assert proposal["validation"]["status"] in {"pending", "validated"}


def test_dev_agent_apply_success(
    client: TestClient,
    auth_headers_factory,
    dev_agent_test_service,
) -> None:
    service, sandbox = dev_agent_test_service
    proposal_id = _seed_backlog(service)
    sandbox.enqueue(
        _FakeExecution(
            success=True,
            workspace_id="ws-success",
            commands=[
                _FakeCommand(command=["pytest", "-q"], return_code=0, stdout="1 passed", duration_ms=12.5)
            ],
        )
    )

    headers = _dev_agent_headers(auth_headers_factory)
    response = client.post("/dev-agent/apply", json={"proposal_id": proposal_id}, headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution"]["success"] is True
    assert payload["execution"]["workspace_id"] == "ws-success"
    assert payload["task"]["status"] == "approved"
    assert payload["proposal"]["status"] == "validated"
    assert payload["proposal"]["approvals"]
    assert payload["proposal"]["approvals"][0]["outcome"] == "validated"

    backlog = service.list_backlog()
    assert backlog[0].status == "approved"
    assert backlog[0].proposals[0].validation["success"] is True


def test_dev_agent_apply_failure_returns_validation_detail(
    client: TestClient,
    auth_headers_factory,
    dev_agent_test_service,
) -> None:
    service, sandbox = dev_agent_test_service
    proposal_id = _seed_backlog(service)
    sandbox.enqueue(
        _FakeExecution(
            success=False,
            workspace_id="ws-failure",
            commands=[
                _FakeCommand(
                    command=["npm", "test"],
                    return_code=1,
                    stdout="",
                    stderr="Tests failed",
                    duration_ms=25.0,
                )
            ],
        )
    )

    headers = _dev_agent_headers(auth_headers_factory)
    response = client.post("/dev-agent/apply", json={"proposal_id": proposal_id}, headers=headers)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["proposal_id"] == proposal_id
    assert detail["status"] == "failed"
    assert detail["workspace_id"] == "ws-failure"
    assert detail["success"] is False
    assert detail["commands"][0]["return_code"] == 1
    assert detail["commands"][0]["stderr"] == "Tests failed"

    backlog = service.list_backlog()
    assert backlog[0].status == "needs_revision"
    assert backlog[0].proposals[0].status == "failed"


def test_dev_agent_requires_privileged_scope(client: TestClient, auth_headers_factory, dev_agent_test_service) -> None:
    service, _ = dev_agent_test_service
    _seed_backlog(service)

    headers = auth_headers_factory()
    response = client.get("/dev-agent/proposals", headers=headers)

    assert response.status_code == 403
