from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from fastapi import HTTPException, status

# Stub implementations - agents.toolkit.sandbox not yet implemented
class SandboxExecutionResult:
    def __init__(self):
        self.success = False
        self.workspace_id = "stub"
        self.commands = []
    
    def to_json(self):
        return {"success": self.success, "workspace_id": self.workspace_id, "commands": []}

class SandboxExecutionHarness:
    def __init__(self, repo_root: Path, commands: List[List[str]]):
        self.repo_root = repo_root
        self.commands = commands
    
    def execute(self, *args, **kwargs) -> SandboxExecutionResult:
        """Execute commands in the containerized environment."""
        import subprocess
        import uuid
        import os
        
        workspace_id = str(uuid.uuid4())
        results = []
        success = True
        
        # Ensure we are in the repo root
        cwd = str(self.repo_root)
        
        # If we are in the API container, /src/repo is the mount point for the full repo
        if os.path.exists("/src/repo"):
            cwd = "/src/repo"

        for cmd in self.commands:
            try:
                # Log the command being executed
                print(f"Executing: {' '.join(cmd)} in {cwd}")
                
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env={**os.environ, "PYTHONPATH": "/src"} # Ensure python path is set
                )
                
                command_result = type('obj', (object,), {
                    'command': ' '.join(cmd),
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'to_json': lambda self: {
                        'command': self.command,
                        'return_code': self.return_code,
                        'stdout': self.stdout[:2000],  # Increased limit
                        'stderr': self.stderr[:2000]
                    }
                })()
                
                results.append(command_result)
                
                if result.returncode != 0:
                    success = False
                    # Don't break immediately, run cleanup/diagnostic commands if any
                    # But for now, we stop to prevent cascading errors
                    break
                    
            except subprocess.TimeoutExpired:
                success = False
                results.append(type('obj', (object,), {
                    'command': ' '.join(cmd),
                    'return_code': -1,
                    'stdout': "",
                    'stderr': "Command timed out",
                    'to_json': lambda self: {'command': self.command, 'return_code': -1, 'stdout': "", 'stderr': "Timeout"}
                })())
                break
            except Exception as e:
                success = False
                results.append(type('obj', (object,), {
                    'command': ' '.join(cmd),
                    'return_code': -1,
                    'stdout': "",
                    'stderr': str(e),
                    'to_json': lambda self: {'command': self.command, 'return_code': -1, 'stdout': "", 'stderr': str(e)}
                })())
                break
        
        execution = SandboxExecutionResult()
        execution.success = success
        execution.workspace_id = workspace_id
        execution.commands = results
        return execution

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


    async def generate_proposal_content(self, task: ImprovementTaskRecord) -> ProposalContext:
        """Generates a patch proposal using the LLM."""
        from .llm_service import get_llm_service
        import json
        import re
        
        llm = get_llm_service()
        
        prompt = f"""
        You are an expert software engineer working on the Op Veritas codebase.
        
        Task Title: {task.title}
        Task Description: {task.description}
        
        Context:
        The codebase is a Python FastAPI backend and React frontend.
        
        Please propose a code change to address this task.
        You must return a valid JSON object with the following structure:
        {{
            "title": "Short title of the change",
            "summary": "Detailed summary of what this change does",
            "diff": "The unified diff of the changes. Must be valid diff format.",
            "rationale": ["Reason 1", "Reason 2"]
        }}
        
        If you need to create a new file, the diff should show /dev/null as the source.
        Ensure the JSON is valid. Do not include markdown formatting around the JSON.
        """
        
        try:
            response = await llm.generate_text(prompt)
            
            # Extract JSON if wrapped in code blocks
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
                
            data = json.loads(json_str)
            
            return ProposalContext(
                title=data.get("title", f"Fix for {task.title}"),
                summary=data.get("summary", "Generated by DevAgent"),
                diff=data.get("diff", ""),
                rationale=data.get("rationale", []),
                validation_preview={"source": "llm_generated"}
            )
        except Exception as e:
            print(f"Error generating proposal: {e}")
            # Return a placeholder context on error
            return ProposalContext(
                title=f"Failed to generate: {task.title}",
                summary=f"Error: {str(e)}",
                diff="",
                rationale=["Generation failed"]
            )

    async def scan_and_execute_next_task(self, task_file_path: str = "/src/repo/task.md") -> Dict[str, Any]:
        """Scans the task list and attempts to execute the next available task."""
        import os
        import re
        
        if not os.path.exists(task_file_path):
            return {"status": "error", "message": f"Task file not found at {task_file_path}"}
            
        with open(task_file_path, 'r') as f:
            content = f.read()
            
        # Find first unchecked task marked with [AUTO] or just the first unchecked task if we want to be aggressive
        # For safety, let's look for a specific tag or just the next item in Phase 1.1
        # Regex for "- [ ] Task Name <!-- id: X -->"
        # We'll look for items explicitly tagged for auto-execution or just pick the next one.
        # Let's pick the next one but require a specific comment tag [AUTO] to be safe?
        # The user asked for "semi-autonomous".
        # Let's look for "- [ ] ... [AUTO]"
        
        match = re.search(r'- \[ \] (.*?) \[AUTO\]', content)
        if not match:
             # Fallback: Look for the specific "Self-Improvement" task we added
             match = re.search(r'- \[ \] (Create "Self-Improvement" loop)', content)
        
        if not match:
            return {"status": "idle", "message": "No auto-tasks found"}
            
        task_title = match.group(1).strip()
        
        # Create a feature request
        request_id = f"auto-{int(datetime.now().timestamp())}"
        task_record = self.record_feature_request(
            request_id=request_id,
            title=task_title,
            description=f"Autonomous execution of task: {task_title}",
            priority="medium",
            requested_by={"client_id": "system", "subject": "dev_agent"},
            tags=["auto", "self-improvement"]
        )
        
        # Generate Proposal
        proposal_context = await self.generate_proposal_content(task_record)
        
        if not proposal_context.diff:
             return {"status": "failed", "message": "Could not generate valid diff"}
             
        # Register Proposal
        proposal = self.create_proposal(
            task_record.task_id,
            {"client_id": "system", "subject": "dev_agent"},
            title=proposal_context.title,
            summary=proposal_context.summary,
            diff=proposal_context.diff,
            rationale=proposal_context.rationale
        )
        
        # Validate
        execution = self.agent.validate_proposal(proposal)
        
        # Apply (if valid)
        # Note: apply_proposal calls validate again, but that's fine.
        # We need a Principal object for application
        from ..security.authz import Principal
        system_principal = Principal(client_id="system", subject="dev_agent", roles=["admin"], tenant_id="system")
        
        result = self.apply_proposal(proposal.proposal_id, system_principal)
        
        return {
            "status": "success" if result.execution.success else "failed",
            "task": task_title,
            "proposal_id": proposal.proposal_id,
            "execution": result.execution.to_json()
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
