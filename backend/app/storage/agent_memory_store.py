from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..utils.storage import atomic_write_json, safe_path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _from_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class AgentThreadRecord:
    """In-memory representation of a multi-agent thread."""

    thread_id: str
    payload: Dict[str, object]

    def to_json(self) -> Dict[str, object]:
        return dict(self.payload)


@dataclass
class ScenarioRunRecord:
    """Structured transcript for a scenario simulation run."""

    run_id: str
    scenario_id: str
    case_id: str
    created_at: datetime
    actor: Dict[str, Any]
    configuration: Dict[str, Any]
    transcript: List[Dict[str, Any]]
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "case_id": self.case_id,
            "created_at": _to_iso(self.created_at),
            "actor": dict(self.actor),
            "configuration": dict(self.configuration),
            "transcript": [dict(entry) for entry in self.transcript],
            "telemetry": dict(self.telemetry),
        }

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "ScenarioRunRecord":
        created_at_raw = payload.get("created_at")
        if not isinstance(created_at_raw, str):
            raise ValueError("Scenario run payload missing created_at timestamp")
        return cls(
            run_id=str(payload.get("run_id")),
            scenario_id=str(payload.get("scenario_id")),
            case_id=str(payload.get("case_id")),
            created_at=_from_iso(created_at_raw),
            actor=dict(payload.get("actor", {})),
            configuration=dict(payload.get("configuration", {})),
            transcript=[dict(entry) for entry in payload.get("transcript", [])],
            telemetry=dict(payload.get("telemetry", {})),
        )


@dataclass
class PatchProposalRecord:
    """Structured representation of a proposed patch for an improvement task."""

    proposal_id: str
    task_id: str
    title: str
    summary: str
    diff: str
    created_at: datetime
    created_by: Dict[str, Any]
    status: str = "pending"
    validation: Dict[str, Any] = field(default_factory=dict)
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)
    validated_at: datetime | None = None
    governance: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "task_id": self.task_id,
            "title": self.title,
            "summary": self.summary,
            "diff": self.diff,
            "created_at": _to_iso(self.created_at),
            "created_by": dict(self.created_by),
            "status": self.status,
            "validation": dict(self.validation),
            "approvals": [dict(entry) for entry in self.approvals],
            "rationale": list(self.rationale),
            "validated_at": _to_iso(self.validated_at) if self.validated_at else None,
            "governance": dict(self.governance),
        }

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "PatchProposalRecord":
        created_at_raw = payload.get("created_at")
        if not isinstance(created_at_raw, str):
            raise ValueError("Proposal payload missing created_at timestamp")
        validated_raw = payload.get("validated_at")
        governance_payload = payload.get("governance", {})
        governance: Dict[str, Any]
        if isinstance(governance_payload, dict):
            governance = dict(governance_payload)
        else:
            governance = {}
        return cls(
            proposal_id=str(payload.get("proposal_id")),
            task_id=str(payload.get("task_id")),
            title=str(payload.get("title", "")),
            summary=str(payload.get("summary", "")),
            diff=str(payload.get("diff", "")),
            created_at=_from_iso(created_at_raw),
            created_by=dict(payload.get("created_by", {})),
            status=str(payload.get("status", "pending")),
            validation=dict(payload.get("validation", {})),
            approvals=[dict(entry) for entry in payload.get("approvals", [])],
            rationale=[str(item) for item in payload.get("rationale", [])],
            validated_at=_from_iso(validated_raw) if isinstance(validated_raw, str) else None,
            governance=governance,
        )


@dataclass
class ImprovementTaskRecord:
    """Backlog record for a feature-request driven improvement task."""

    task_id: str
    feature_request_id: str
    title: str
    description: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    planner_notes: List[str] = field(default_factory=list)
    risk_score: float | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    proposals: List[PatchProposalRecord] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "feature_request_id": self.feature_request_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_at": _to_iso(self.created_at),
            "updated_at": _to_iso(self.updated_at),
            "planner_notes": list(self.planner_notes),
            "risk_score": self.risk_score,
            "metadata": dict(self.metadata),
            "proposals": [proposal.to_json() for proposal in self.proposals],
        }

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "ImprovementTaskRecord":
        created_at_raw = payload.get("created_at")
        updated_at_raw = payload.get("updated_at")
        if not isinstance(created_at_raw, str) or not isinstance(updated_at_raw, str):
            raise ValueError("Improvement task payload missing timestamp fields")
        proposals_payload = payload.get("proposals", [])
        if not isinstance(proposals_payload, list):
            raise ValueError("Improvement task proposals must be a list")
        proposals = [PatchProposalRecord.from_json(record) for record in proposals_payload]
        return cls(
            task_id=str(payload.get("task_id")),
            feature_request_id=str(payload.get("feature_request_id")),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            priority=str(payload.get("priority", "medium")),
            status=str(payload.get("status", "pending")),
            created_at=_from_iso(created_at_raw),
            updated_at=_from_iso(updated_at_raw),
            planner_notes=[str(note) for note in payload.get("planner_notes", [])],
            risk_score=(float(payload["risk_score"]) if payload.get("risk_score") is not None else None),
            metadata=dict(payload.get("metadata", {})),
            proposals=proposals,
        )

    def append_proposal(self, proposal: PatchProposalRecord) -> None:
        self.proposals.append(proposal)
        self.updated_at = _utcnow()


class AgentMemoryStore:
    """Filesystem-backed persistence for agent conversation threads."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.tasks_root = self.root / "improvement_tasks"
        self.tasks_root.mkdir(parents=True, exist_ok=True)
        self.scenario_root = self.root / "scenario_runs"
        self.scenario_root.mkdir(parents=True, exist_ok=True)

    def _path(self, thread_id: str) -> Path:
        return safe_path(self.root, thread_id)

    def _task_path(self, task_id: str) -> Path:
        return safe_path(self.tasks_root, f"{task_id}.json")

    def write(self, record: AgentThreadRecord) -> None:
        path = self._path(record.thread_id)
        atomic_write_json(path, record.to_json())

    def read(self, thread_id: str) -> Dict[str, object]:
        path = self._path(thread_id)
        if not path.exists():
            raise FileNotFoundError(f"Agent thread {thread_id} not found")
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Thread payload for {thread_id} is not a JSON object")
        return data

    def list_threads(self) -> List[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    def purge(self, thread_ids: Iterable[str]) -> None:
        for thread_id in thread_ids:
            path = self._path(thread_id)
            if path.exists():
                path.unlink()

    def write_task(self, record: ImprovementTaskRecord) -> None:
        path = self._task_path(record.task_id)
        atomic_write_json(path, record.to_json())

    def read_task(self, task_id: str) -> ImprovementTaskRecord:
        path = self._task_path(task_id)
        if not path.exists():
            raise FileNotFoundError(f"Improvement task {task_id} not found")
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Improvement task payload for {task_id} is not a JSON object")
        return ImprovementTaskRecord.from_json(data)

    def list_tasks(self) -> List[ImprovementTaskRecord]:
        records: List[ImprovementTaskRecord] = []
        for path in self.tasks_root.glob("*.json"):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            try:
                records.append(ImprovementTaskRecord.from_json(data))
            except (ValueError, TypeError):
                continue
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return records

    def find_task_by_feature(self, feature_request_id: str) -> Optional[ImprovementTaskRecord]:
        for record in self.list_tasks():
            if record.feature_request_id == feature_request_id:
                return record
        return None

    def append_proposal(self, task_id: str, proposal: PatchProposalRecord) -> ImprovementTaskRecord:
        task = self.read_task(task_id)
        task.append_proposal(proposal)
        self.write_task(task)
        return task

    def update_task(self, record: ImprovementTaskRecord) -> None:
        record.updated_at = _utcnow()
        self.write_task(record)

    def _scenario_path(self, run_id: str) -> Path:
        return safe_path(self.scenario_root, run_id)

    def write_scenario(self, record: ScenarioRunRecord) -> None:
        path = self._scenario_path(record.run_id)
        atomic_write_json(path, record.to_json())

    def read_scenario(self, run_id: str) -> ScenarioRunRecord:
        path = self._scenario_path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"Scenario run {run_id} not found")
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Scenario run payload for {run_id} is not a JSON object")
        return ScenarioRunRecord.from_json(data)

    def list_scenarios(self) -> List[str]:
        return sorted(path.stem for path in self.scenario_root.glob("*.json"))

