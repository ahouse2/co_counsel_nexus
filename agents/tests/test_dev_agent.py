from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import List, Sequence, Tuple

import pytest

pytest.importorskip("fastapi")
from fastapi import HTTPException, status

from agents.toolkit.sandbox import (
    SandboxCommandResult,
    SandboxExecutionHarness,
)
from backend.app.config import get_settings, reset_settings_cache
from backend.app.security.authz import Principal
from backend.app.services.dev_agent import DevAgentService, reset_dev_agent_service
from backend.app.storage.agent_memory_store import AgentMemoryStore
from backend.app.utils.audit import reset_audit_trail


@pytest.fixture(autouse=True)
def _reset_state(tmp_path: Path) -> None:
    reset_dev_agent_service()
    reset_settings_cache()
    settings = get_settings()
    settings.agent_threads_dir = tmp_path / "threads"
    settings.audit_log_path = tmp_path / "audit.log"
    settings.dev_agent_validation_commands = (("lint", "--check"),)
    settings.dev_agent_rollout_stages = ("canary", "general")
    settings.dev_agent_feature_flag_prefix = "qa.flag"
    settings.dev_agent_ci_workflows = ("backend_ci.yml",)
    settings.dev_agent_governance_policy_version = "test-policy"
    settings.prepare_directories()
    reset_audit_trail()


def _stub_runner(commands_executed: List[Tuple[Sequence[str], Path]]):
    def _run(command: Sequence[str], cwd: Path) -> CompletedProcess:
        commands_executed.append((tuple(command), cwd))
        return CompletedProcess(command, 0, stdout="ok", stderr="")

    return _run


def test_dev_agent_proposal_lifecycle(tmp_path: Path) -> None:
    settings = get_settings()
    store = AgentMemoryStore(settings.agent_threads_dir)
    commands_executed: List[Tuple[Sequence[str], Path]] = []
    harness = SandboxExecutionHarness(
        Path(__file__).resolve().parents[2],
        commands=settings.dev_agent_validation_commands,
        command_runner=_stub_runner(commands_executed),
    )
    def _fake_apply(workspace: Path, diff: str) -> SandboxCommandResult:
        (workspace / "pending.diff").write_text(diff)
        return SandboxCommandResult(
            command=["git", "apply", "--whitespace=nowarn"],
            return_code=0,
            stdout="applied",
            stderr="",
            duration_ms=0.12,
        )

    harness._apply_diff = _fake_apply  # type: ignore[attr-defined]
    service = DevAgentService(memory_store=store, sandbox=harness)

    task = service.record_feature_request(
        request_id="FR-123",
        title="Harden ingestion polling",
        description="Operators need deterministic retries for ingestion jobs.",
        priority="high",
        requested_by={"email": "ops@example.com"},
        metadata={"source": "ops-portal"},
        tags=["ingestion", "reliability"],
        planner_notes=["confirm job store idempotency"],
        risk_score=0.42,
    )
    assert task.status == "triaged"

    proposal = service.create_proposal(
        task.task_id,
        actor={"subject": "dev.bot@example.com", "component": "planner"},
        title="Add retry jitter",
        summary="Introduce bounded exponential backoff to ingestion worker retries.",
        diff="diff --git a/placeholder b/placeholder\n",
        rationale=["prevents thundering herd"],
    )
    assert proposal.task_id == task.task_id
    assert proposal.status == "pending"

    principal = Principal(
        client_id="cli-dev",
        subject="dev.admin@example.com",
        tenant_id="tenant-one",
        roles={"PlatformEngineer"},
        token_roles=set(),
        certificate_roles=set(),
        scopes={"dev-agent:admin"},
        case_admin=False,
        attributes={},
    )

    result = service.apply_proposal(proposal.proposal_id, principal)
    assert result.execution.success is True
    assert result.proposal.status == "validated"
    assert result.rollout_plan is not None
    assert result.rollout_plan["policy_version"] == "test-policy"
    assert commands_executed, "sandbox commands should run"
    command, workspace = commands_executed[0]
    assert command == tuple(settings.dev_agent_validation_commands[0])
    assert workspace.name == "workspace"

    persisted = store.read_task(task.task_id)
    assert persisted.status == "rollout_pending"
    stored_proposal = persisted.proposals[0]
    assert stored_proposal.validation["success"] is True
    assert stored_proposal.validation["commands"][0]["command"][0] == "git"
    assert stored_proposal.validation["status"] == "validated"
    assert stored_proposal.validated_at is not None
    assert stored_proposal.governance["rollout"]["stages"][0]["toggle"] == "qa.flag.FR-123.canary"
    gate = stored_proposal.governance["regression_gate"]
    assert gate["status"] == "passed"
    assert gate["ci_workflows"][0]["workflow"] == "backend_ci.yml"

    audit_path = settings.audit_log_path
    assert audit_path.exists()
    lines = audit_path.read_text().strip().splitlines()
    assert lines, "audit log must contain an entry"
    last_record = json.loads(lines[-1])
    assert last_record["category"] == "dev_agent"
    assert last_record["subject"]["proposal_id"] == proposal.proposal_id
    assert last_record["metadata"]["status"] == "validated"

    metrics = service.metrics()
    assert metrics["validated_proposals"] == 1
    assert metrics["active_rollouts"] == 1
    assert metrics["feature_toggles"][0]["toggle"] == "qa.flag.FR-123.canary"


def test_dev_agent_proposal_validation_failure(tmp_path: Path) -> None:
    settings = get_settings()
    store = AgentMemoryStore(settings.agent_threads_dir)
    commands_executed: List[Tuple[Sequence[str], Path]] = []
    harness = SandboxExecutionHarness(
        Path(__file__).resolve().parents[2],
        commands=settings.dev_agent_validation_commands,
        command_runner=_stub_runner(commands_executed),
    )

    def _failing_apply(workspace: Path, diff: str) -> SandboxCommandResult:
        (workspace / "pending.diff").write_text(diff)
        return SandboxCommandResult(
            command=["git", "apply", "--whitespace=nowarn"],
            return_code=1,
            stdout="",
            stderr="patch failed",
            duration_ms=0.34,
        )

    harness._apply_diff = _failing_apply  # type: ignore[attr-defined]
    service = DevAgentService(memory_store=store, sandbox=harness)

    task = service.record_feature_request(
        request_id="FR-456",
        title="Repair sandbox diff",
        description="Ensure git apply failures are surfaced.",
        priority="high",
        requested_by={"email": "qa@example.com"},
    )
    proposal = service.create_proposal(
        task.task_id,
        actor={"subject": "dev.bot@example.com"},
        title="Re-run command",
        summary="Regression diff",
        diff="diff --git a/foo b/foo\n",
    )
    principal = Principal(
        client_id="cli-dev",
        subject="dev.admin@example.com",
        tenant_id="tenant-one",
        roles={"PlatformEngineer"},
        token_roles=set(),
        certificate_roles=set(),
        scopes={"dev-agent:admin"},
        case_admin=False,
        attributes={},
    )

    with pytest.raises(HTTPException) as excinfo:
        service.apply_proposal(proposal.proposal_id, principal)

    assert excinfo.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    payload = excinfo.value.detail
    assert payload["status"] == "failed"
    assert payload["commands"][0]["return_code"] == 1
    assert payload["commands"][0]["stderr"] == "patch failed"
    assert not commands_executed

    persisted = store.read_task(task.task_id)
    assert persisted.status == "needs_revision"
    failed_proposal = persisted.proposals[0]
    assert failed_proposal.status == "failed"
    assert failed_proposal.validation["success"] is False
    assert failed_proposal.governance["regression_gate"]["status"] == "failed"
    assert failed_proposal.validated_at is None

    audit_path = settings.audit_log_path
    lines = audit_path.read_text().strip().splitlines()
    last_record = json.loads(lines[-1])
    assert last_record["outcome"] == "failure"
    assert last_record["metadata"]["commands"][0]["stderr"] == "patch failed"
