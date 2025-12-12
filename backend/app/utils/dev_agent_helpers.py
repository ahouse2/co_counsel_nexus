from ..services.dev_agent import SandboxExecutionResult
from ..models.api import (
    DevAgentProposalModel,
    DevAgentTaskModel,
    SandboxCommandResultModel,
    SandboxExecutionModel,
)
from ..storage.agent_memory_store import ImprovementTaskRecord, PatchProposalRecord

def proposal_from_record(
    task: ImprovementTaskRecord,
    proposal: PatchProposalRecord,
) -> DevAgentProposalModel:
    return DevAgentProposalModel(
        proposal_id=proposal.proposal_id,
        task_id=proposal.task_id,
        feature_request_id=task.feature_request_id,
        title=proposal.title,
        summary=proposal.summary,
        diff=proposal.diff,
        status=proposal.status,
        created_at=proposal.created_at,
        created_by=dict(proposal.created_by),
        validation=dict(proposal.validation),
        approvals=[dict(entry) for entry in proposal.approvals],
        rationale=list(proposal.rationale),
        validated_at=proposal.validated_at,
        governance=dict(proposal.governance),
    )


def task_from_record(task: ImprovementTaskRecord) -> DevAgentTaskModel:
    proposals = [proposal_from_record(task, proposal) for proposal in task.proposals]
    return DevAgentTaskModel(
        task_id=task.task_id,
        feature_request_id=task.feature_request_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        planner_notes=list(task.planner_notes),
        risk_score=task.risk_score,
        metadata=dict(task.metadata),
        proposals=proposals,
    )


def execution_from_result(result: SandboxExecutionResult) -> SandboxExecutionModel:
    return SandboxExecutionModel(
        success=result.success,
        workspace_id=result.workspace_id,
        commands=[
            SandboxCommandResultModel(
                command=list(command.command),
                return_code=command.return_code,
                stdout=command.stdout,
                stderr=command.stderr,
                duration_ms=command.duration_ms,
            )
            for command in result.commands
        ],
    )
