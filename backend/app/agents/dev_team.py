from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from agents.toolkit.sandbox import SandboxExecutionHarness, SandboxExecutionResult

from ..storage.agent_memory_store import (
    AgentMemoryStore,
    ImprovementTaskRecord,
    PatchProposalRecord,
)


__all__ = [
    "FeatureRequest",
    "ProposalContext",
    "DevTeamPlanner",
    "DevTeamExecutor",
    "DevTeamAgent",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class FeatureRequest:
    """Normalized feature request observed by the Dev Team planner."""

    request_id: str
    title: str
    description: str
    priority: str
    requested_by: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ProposalContext:
    """Context that feeds into proposal generation."""

    title: str
    summary: str
    diff: str
    rationale: List[str] = field(default_factory=list)
    validation_preview: Dict[str, Any] | None = None


class DevTeamPlanner:
    """Planner persona mirroring Microsoft Agents SDK planning semantics."""

    def __init__(self, memory_store: AgentMemoryStore) -> None:
        self.memory_store = memory_store

    def triage(
        self,
        feature: FeatureRequest,
        *,
        planner_notes: Iterable[str] | None = None,
        risk_score: float | None = None,
    ) -> ImprovementTaskRecord:
        existing = self.memory_store.find_task_by_feature(feature.request_id)
        notes = [note.strip() for note in (planner_notes or []) if note.strip()]
        now = _utcnow()
        metadata = {
            "requested_by": dict(feature.requested_by),
            "tags": sorted(feature.tags),
            "source": "DevTeamPlanner",
            **feature.metadata,
        }
        if existing:
            existing.title = feature.title
            existing.description = feature.description
            existing.priority = feature.priority
            existing.status = "triaged"
            if notes:
                existing.planner_notes = notes
            existing.risk_score = risk_score if risk_score is not None else existing.risk_score
            existing.metadata.update(metadata)
            self.memory_store.update_task(existing)
            return existing
        task = ImprovementTaskRecord(
            task_id=str(uuid4()),
            feature_request_id=feature.request_id,
            title=feature.title,
            description=feature.description,
            priority=feature.priority,
            status="triaged",
            created_at=now,
            updated_at=now,
            planner_notes=notes,
            risk_score=risk_score,
            metadata=metadata,
        )
        self.memory_store.write_task(task)
        return task


class DevTeamExecutor:
    """Executor persona responsible for assembling actionable patch proposals."""

    def __init__(
        self,
        memory_store: AgentMemoryStore,
        sandbox: SandboxExecutionHarness,
    ) -> None:
        self.memory_store = memory_store
        self.sandbox = sandbox

    def propose(
        self,
        task: ImprovementTaskRecord,
        actor: Dict[str, Any],
        context: ProposalContext,
    ) -> PatchProposalRecord:
        proposal = PatchProposalRecord(
            proposal_id=str(uuid4()),
            task_id=task.task_id,
            title=context.title,
            summary=context.summary,
            diff=context.diff,
            created_at=_utcnow(),
            created_by=dict(actor),
            status="pending",
            validation=context.validation_preview or {"status": "pending"},
            approvals=[],
            rationale=list(context.rationale),
        )
        updated = self.memory_store.append_proposal(task.task_id, proposal)
        return next(item for item in updated.proposals if item.proposal_id == proposal.proposal_id)

    def validate(self, proposal: PatchProposalRecord) -> SandboxExecutionResult:
        return self.sandbox.validate(proposal.diff)


class DevTeamAgent:
    """Facade aggregating planner and executor behaviours for dev operations."""

    def __init__(
        self,
        memory_store: AgentMemoryStore,
        sandbox: SandboxExecutionHarness,
    ) -> None:
        self.memory_store = memory_store
        self.planner = DevTeamPlanner(memory_store)
        self.executor = DevTeamExecutor(memory_store, sandbox)

    def observe_feature_request(
        self,
        feature: FeatureRequest,
        *,
        planner_notes: Iterable[str] | None = None,
        risk_score: float | None = None,
    ) -> ImprovementTaskRecord:
        return self.planner.triage(feature, planner_notes=planner_notes, risk_score=risk_score)

    def register_proposal(
        self,
        task: ImprovementTaskRecord,
        actor: Dict[str, Any],
        context: ProposalContext,
    ) -> PatchProposalRecord:
        return self.executor.propose(task, actor, context)

    def validate_proposal(self, proposal: PatchProposalRecord) -> SandboxExecutionResult:
        return self.executor.validate(proposal)

