from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from fastapi import HTTPException, status

from agents.toolkit.sandbox import SandboxExecutionHarness, SandboxExecutionResult

from ..agents.dev_team import DevTeamAgent, FeatureRequest, ProposalContext
from ..config import get_settings
from ..security.authz import Principal
from ..storage.agent_memory_store import (
    AgentMemoryStore,
    ImprovementTaskRecord,
    PatchProposalRecord,
)
from ..utils.audit import AuditEvent, get_audit_trail


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ProposalApplicationResult:
    proposal: PatchProposalRecord
    task: ImprovementTaskRecord
    execution: SandboxExecutionResult
    regression_gate: Dict[str, Any]
    rollout_plan: Dict[str, Any] | None


class DevAgentService:
    """Coordinates dev-agent planner/executor lifecycle and auditability."""

    def __init__(
        self,
        *,
        memory_store: AgentMemoryStore | None = None,
        sandbox: SandboxExecutionHarness | None = None,
    ) -> None:
        self.settings = get_settings()
        self.memory_store = memory_store or AgentMemoryStore(self.settings.agent_threads_dir)
        repo_root = Path(__file__).resolve().parents[3]
        commands = [list(cmd) for cmd in self.settings.dev_agent_validation_commands]
        self.sandbox = sandbox or SandboxExecutionHarness(repo_root, commands)
        self.agent = DevTeamAgent(self.memory_store, self.sandbox)
        self.audit = get_audit_trail()

    def record_feature_request(
        self,
        *,
        request_id: str,
        title: str,
        description: str,
        priority: str,
        requested_by: Dict[str, object],
        metadata: Dict[str, object] | None = None,
        tags: Iterable[str] | None = None,
        planner_notes: Iterable[str] | None = None,
        risk_score: float | None = None,
    ) -> ImprovementTaskRecord:
        feature = FeatureRequest(
            request_id=request_id,
            title=title,
            description=description,
            priority=priority,
            requested_by=dict(requested_by),
            metadata=dict(metadata or {}),
            tags=[str(tag) for tag in (tags or [])],
        )
        return self.agent.observe_feature_request(feature, planner_notes=planner_notes, risk_score=risk_score)

    def create_proposal(
        self,
        task_id: str,
        actor: Dict[str, Any],
        *,
        title: str,
        summary: str,
        diff: str,
        rationale: Iterable[str] | None = None,
    ) -> PatchProposalRecord:
        task = self.memory_store.read_task(task_id)
        context = ProposalContext(
            title=title,
            summary=summary,
            diff=diff,
            rationale=[note for note in (rationale or [])],
        )
        return self.agent.register_proposal(task, actor, context)

    def list_backlog(self) -> List[ImprovementTaskRecord]:
        return self.memory_store.list_tasks()

    def list_proposals(self) -> List[Tuple[ImprovementTaskRecord, PatchProposalRecord]]:
        backlog: List[Tuple[ImprovementTaskRecord, PatchProposalRecord]] = []
        for task in self.list_backlog():
            for proposal in task.proposals:
                backlog.append((task, proposal))
        backlog.sort(key=lambda item: item[1].created_at, reverse=True)
        return backlog

    def apply_proposal(self, proposal_id: str, principal: Principal) -> ProposalApplicationResult:
        task, proposal = self._locate_proposal(proposal_id)
        execution = self.agent.validate_proposal(proposal)
        regression_gate = self._build_regression_gate(execution)
        validated_at = _utcnow() if execution.success else None
        validation_payload = execution.to_json()
        validation_payload["status"] = "validated" if execution.success else "failed"
        validation_payload["validated_at"] = validated_at.isoformat() if validated_at else None
        validation_payload["regression_gate"] = regression_gate
        proposal.validation = validation_payload
        proposal.status = "validated" if execution.success else "failed"
        proposal.validated_at = validated_at
        proposal.approvals.append(
            {
                "actor": {
                    "client_id": principal.client_id,
                    "subject": principal.subject,
                    "roles": sorted(principal.roles),
                },
                "timestamp": _utcnow().isoformat(),
                "outcome": proposal.status,
            }
        )
        rollout_plan: Dict[str, Any] | None = None
        if execution.success:
            rollout_plan = self._schedule_rollout(task, principal, validated_at)
            proposal.governance = {
                "regression_gate": regression_gate,
                "rollout": rollout_plan,
            }
            task.status = "rollout_pending"
        else:
            proposal.governance = {"regression_gate": regression_gate}
            task.status = "needs_revision"
        self.memory_store.update_task(task)
        self._audit_application(principal, task, proposal, execution)
        if not execution.success:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "proposal_id": proposal.proposal_id,
                    "status": proposal.status,
                    "workspace_id": execution.workspace_id,
                    "success": execution.success,
                    "commands": [command.to_json() for command in execution.commands],
                },
            )
        return ProposalApplicationResult(
            proposal=proposal,
            task=task,
            execution=execution,
            regression_gate=regression_gate,
            rollout_plan=rollout_plan,
        )

    def metrics(self) -> Dict[str, Any]:
        tasks = self.list_backlog()
        now = _utcnow()
        proposals = [proposal for task in tasks for proposal in task.proposals]
        validated = [proposal for proposal in proposals if proposal.status == "validated"]
        total_runs = [
            proposal
            for proposal in proposals
            if isinstance(proposal.validation, dict) and "success" in proposal.validation
        ]
        passed = [
            proposal
            for proposal in proposals
            if isinstance(proposal.validation, dict) and bool(proposal.validation.get("success"))
        ]
        window_start = now - timedelta(days=7)
        recent_validated = [
            proposal
            for proposal in validated
            if proposal.validated_at and proposal.validated_at >= window_start
        ]
        velocity = len(recent_validated) / 7.0 if recent_validated else 0.0
        pass_rate = (len(passed) / len(total_runs)) if total_runs else 0.0
        rollout_candidates = 0
        active_toggles: List[Dict[str, Any]] = []
        for proposal in proposals:
            governance = proposal.governance if isinstance(proposal.governance, dict) else {}
            rollout = governance.get("rollout") if governance else None
            if isinstance(rollout, dict):
                stages = rollout.get("stages")
                if isinstance(stages, list):
                    stage_active = False
                    for stage in stages:
                        if not isinstance(stage, dict):
                            continue
                        status = str(stage.get("status", "")).lower()
                        toggle_name = stage.get("toggle")
                        if status not in {"complete", "completed"} and toggle_name:
                            stage_active = True
                            active_toggles.append(
                                {
                                    "stage": stage.get("name") or stage.get("stage"),
                                    "toggle": toggle_name,
                                    "status": status or "pending",
                                }
                            )
                    if stage_active:
                        rollout_candidates += 1
        return {
            "generated_at": now.isoformat(),
            "total_tasks": len(tasks),
            "triaged_tasks": sum(1 for task in tasks if task.status == "triaged"),
            "rollout_pending": sum(1 for task in tasks if task.status == "rollout_pending"),
            "validated_proposals": len(validated),
            "quality_gate_pass_rate": round(pass_rate, 4),
            "velocity_per_day": round(velocity, 4),
            "active_rollouts": rollout_candidates,
            "ci_workflows": list(self.settings.dev_agent_ci_workflows),
            "feature_toggles": active_toggles,
        }

    def _locate_proposal(self, proposal_id: str) -> Tuple[ImprovementTaskRecord, PatchProposalRecord]:
        for task in self.list_backlog():
            for proposal in task.proposals:
                if proposal.proposal_id == proposal_id:
                    return task, proposal
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    def _audit_application(
        self,
        principal: Principal,
        task: ImprovementTaskRecord,
        proposal: PatchProposalRecord,
        execution: SandboxExecutionResult,
    ) -> None:
        event = AuditEvent(
            category="dev_agent",
            action="dev_agent.proposal.applied",
            actor={
                "client_id": principal.client_id,
                "subject": principal.subject,
                "roles": sorted(principal.roles),
                "tenant_id": principal.tenant_id,
            },
            subject={
                "task_id": task.task_id,
                "feature_request_id": task.feature_request_id,
                "proposal_id": proposal.proposal_id,
            },
            outcome="success" if execution.success else "failure",
            severity="info" if execution.success else "warning",
            correlation_id=proposal.proposal_id,
            metadata={
                "status": proposal.status,
                "commands": [command.to_json() for command in execution.commands],
            },
        )
        self.audit.append(event)

    def _build_regression_gate(self, execution: SandboxExecutionResult) -> Dict[str, Any]:
        failed = [command.to_json() for command in execution.commands if command.return_code != 0]
        status_value = "passed" if execution.success else "failed"
        workflows = []
        for workflow in self.settings.dev_agent_ci_workflows:
            workflows.append(
                {
                    "workflow": workflow,
                    "status": "scheduled" if execution.success else "blocked",
                    "trigger": f"gh workflow run {workflow}",
                }
            )
        return {
            "status": status_value,
            "failed_commands": failed,
            "ci_workflows": workflows,
        }

    def _schedule_rollout(
        self,
        task: ImprovementTaskRecord,
        principal: Principal,
        validated_at: datetime | None,
    ) -> Dict[str, Any]:
        prefix = self.settings.dev_agent_feature_flag_prefix
        stages: List[Dict[str, Any]] = []
        for index, stage in enumerate(self.settings.dev_agent_rollout_stages):
            toggle_name = f"{prefix}.{task.feature_request_id}.{stage}"
            stages.append(
                {
                    "name": stage,
                    "toggle": toggle_name,
                    "status": "ready" if index == 0 else "pending",
                    "activated_at": None,
                }
            )
        return {
            "policy_version": self.settings.dev_agent_governance_policy_version,
            "created_at": (validated_at or _utcnow()).isoformat(),
            "feature_request_id": task.feature_request_id,
            "scheduled_by": {
                "client_id": principal.client_id,
                "subject": principal.subject,
            },
            "stages": stages,
        }


_dev_agent_service: DevAgentService | None = None


def get_dev_agent_service() -> DevAgentService:
    global _dev_agent_service
    if _dev_agent_service is None:
        _dev_agent_service = DevAgentService()
    return _dev_agent_service


def reset_dev_agent_service() -> None:
    global _dev_agent_service
    _dev_agent_service = None
