"""Dataclasses representing ACE automation artefacts."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional

ISO8601 = "%Y-%m-%dT%H:%M:%S.%fZ"


@dataclass(slots=True)
class CommandResult:
    """Result of a shell command execution."""

    name: str
    command: List[str]
    cwd: str
    status: Literal["success", "failure", "skipped"]
    exit_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    stdout: str
    stderr: str

    def to_dict(self) -> Dict[str, object]:
        return dataclasses.asdict(self)


@dataclass(slots=True)
class DependencyRecord:
    """A single dependency entry from `pipdeptree` or `pip list`."""

    name: str
    version: str

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(slots=True)
class ContextBundle:
    """Context documents gathered by the retriever."""

    root: str
    files: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {"root": self.root, "files": list(self.files)}


@dataclass(slots=True)
class RetrieverReport:
    """Structured output of the Retriever stage."""

    metadata: Dict[str, object]
    changed_files: List[str]
    dependency_snapshot: List[DependencyRecord]
    static_analysis: List[CommandResult]
    context_bundle: ContextBundle
    risks: List[str]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(ISO8601)
    )

    def to_dict(self) -> Dict[str, object]:
        return {
            "metadata": self.metadata,
            "changed_files": list(self.changed_files),
            "dependency_snapshot": [record.to_dict() for record in self.dependency_snapshot],
            "static_analysis": [result.to_dict() for result in self.static_analysis],
            "context_bundle": self.context_bundle.to_dict(),
            "risks": list(self.risks),
            "generated_at": self.generated_at,
        }

    def dump(self, path: Path) -> None:
        path.write_text(_json_dumps(self.to_dict()))


@dataclass(slots=True)
class PlanStep:
    """Planner step that will be executed by the critic."""

    identifier: str
    name: str
    description: str
    command: List[str]
    rubric_categories: List[str]
    continue_on_error: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "description": self.description,
            "command": list(self.command),
            "rubric_categories": list(self.rubric_categories),
            "continue_on_error": self.continue_on_error,
        }


@dataclass(slots=True)
class PlannerPlan:
    """Output emitted by the planner stage."""

    metadata: Dict[str, object]
    steps: List[PlanStep]
    rationale: List[str]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(ISO8601)
    )

    def to_dict(self) -> Dict[str, object]:
        return {
            "metadata": self.metadata,
            "steps": [step.to_dict() for step in self.steps],
            "rationale": list(self.rationale),
            "generated_at": self.generated_at,
        }

    def dump(self, path: Path) -> None:
        path.write_text(_json_dumps(self.to_dict()))


@dataclass(slots=True)
class RubricEntry:
    """Score for a single rubric category."""

    category: str
    score: float
    rationale: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "category": self.category,
            "score": self.score,
            "rationale": self.rationale,
        }


@dataclass(slots=True)
class CriticVerdict:
    """Verdict emitted after executing the planner steps."""

    status: Literal["pass", "block"]
    average_score: float
    minimum_score: float
    rubric: List[RubricEntry]
    command_results: List[CommandResult]
    recommendations: List[str]
    metadata: Dict[str, object]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(ISO8601)
    )

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "average_score": self.average_score,
            "minimum_score": self.minimum_score,
            "rubric": [entry.to_dict() for entry in self.rubric],
            "command_results": [result.to_dict() for result in self.command_results],
            "recommendations": list(self.recommendations),
            "metadata": self.metadata,
            "generated_at": self.generated_at,
        }

    def dump(self, path: Path) -> None:
        path.write_text(_json_dumps(self.to_dict()))


def _json_dumps(payload: Dict[str, object]) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True)


def hydrate_retriever_report(path: Path) -> RetrieverReport:
    import json

    data = json.loads(path.read_text())
    deps = [
        DependencyRecord(name=item["name"], version=item["version"])
        for item in data.get("dependency_snapshot", [])
    ]
    static_analysis = [
        CommandResult(
            name=item["name"],
            command=list(item["command"]),
            cwd=item.get("cwd", "."),
            status=item["status"],
            exit_code=int(item["exit_code"]),
            started_at=item["started_at"],
            finished_at=item["finished_at"],
            duration_seconds=float(item["duration_seconds"]),
            stdout=item.get("stdout", ""),
            stderr=item.get("stderr", ""),
        )
        for item in data.get("static_analysis", [])
    ]
    bundle_payload = data.get("context_bundle", {})
    context_bundle = ContextBundle(
        root=bundle_payload.get("root", "."),
        files=[str(f) for f in bundle_payload.get("files", [])],
    )
    return RetrieverReport(
        metadata=data.get("metadata", {}),
        changed_files=[str(item) for item in data.get("changed_files", [])],
        dependency_snapshot=deps,
        static_analysis=static_analysis,
        context_bundle=context_bundle,
        risks=[str(item) for item in data.get("risks", [])],
        generated_at=data.get("generated_at", datetime.now(timezone.utc).strftime(ISO8601)),
    )


def hydrate_planner_plan(path: Path) -> PlannerPlan:
    import json

    data = json.loads(path.read_text())
    steps = [
        PlanStep(
            identifier=item["identifier"],
            name=item["name"],
            description=item["description"],
            command=list(item["command"]),
            rubric_categories=list(item.get("rubric_categories", [])),
            continue_on_error=bool(item.get("continue_on_error", False)),
        )
        for item in data.get("steps", [])
    ]
    return PlannerPlan(
        metadata=data.get("metadata", {}),
        steps=steps,
        rationale=list(data.get("rationale", [])),
        generated_at=data.get("generated_at", datetime.now(timezone.utc).strftime(ISO8601)),
    )


def hydrate_critic_verdict(path: Path) -> CriticVerdict:
    import json

    data = json.loads(path.read_text())
    rubric = [
        RubricEntry(
            category=item["category"],
            score=float(item["score"]),
            rationale=item.get("rationale", ""),
        )
        for item in data.get("rubric", [])
    ]
    command_results = [
        CommandResult(
            name=item["name"],
            command=list(item["command"]),
            cwd=item.get("cwd", "."),
            status=item["status"],
            exit_code=int(item["exit_code"]),
            started_at=item["started_at"],
            finished_at=item["finished_at"],
            duration_seconds=float(item["duration_seconds"]),
            stdout=item.get("stdout", ""),
            stderr=item.get("stderr", ""),
        )
        for item in data.get("command_results", [])
    ]
    return CriticVerdict(
        status=data.get("status", "block"),
        average_score=float(data.get("average_score", 0.0)),
        minimum_score=float(data.get("minimum_score", 0.0)),
        rubric=rubric,
        command_results=command_results,
        recommendations=list(data.get("recommendations", [])),
        metadata=data.get("metadata", {}),
        generated_at=data.get("generated_at", datetime.now(timezone.utc).strftime(ISO8601)),
    )


__all__ = [
    "CommandResult",
    "ContextBundle",
    "CriticVerdict",
    "DependencyRecord",
    "PlanStep",
    "PlannerPlan",
    "RetrieverReport",
    "RubricEntry",
    "hydrate_critic_verdict",
    "hydrate_planner_plan",
    "hydrate_retriever_report",
]
