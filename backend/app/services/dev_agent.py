from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
        proposal.validation = execution.to_json()
        proposal.status = "validated" if execution.success else "failed"
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
        task.status = "approved" if execution.success else "needs_revision"
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
        return ProposalApplicationResult(proposal=proposal, task=task, execution=execution)

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


_dev_agent_service: DevAgentService | None = None


def get_dev_agent_service() -> DevAgentService:
    global _dev_agent_service
    if _dev_agent_service is None:
        _dev_agent_service = DevAgentService()
    return _dev_agent_service


def reset_dev_agent_service() -> None:
    global _dev_agent_service
    _dev_agent_service = None
