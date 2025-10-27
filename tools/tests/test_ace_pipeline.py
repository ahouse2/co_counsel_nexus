from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ace.artefacts import (
    ContextBundle,
    DependencyRecord,
    PlanStep,
    PlannerPlan,
    RetrieverReport,
)
from tools.ace.critic import evaluate
from tools.ace.planner import synthesise_plan
from tools.ace.runner import run_command
from tools.ace.schema import (
    validate_critic_verdict,
    validate_planner_plan,
    validate_retriever_report,
)


def _sample_retriever_report(tmp_path: Path) -> Path:
    report = RetrieverReport(
        metadata={
            "pr_number": "123",
            "head_ref": "feature/test",
            "base_ref": "main",
            "repository": "NinthOctopusMitten",
        },
        changed_files=["docs/README.md"],
        dependency_snapshot=[DependencyRecord(name="sample", version="1.0.0")],
        static_analysis=[],
        context_bundle=ContextBundle(root="docs", files=["docs/README.md"]),
        risks=["No blocking risks detected; continue with planner synthesis."],
    )
    report_path = tmp_path / "retriever_report.json"
    report.dump(report_path)
    return report_path


def test_runner_skips_missing_binary(tmp_path: Path) -> None:
    result = run_command("missing", ["definitely-not-a-real-binary"], optional=True)
    assert result.status == "skipped"
    assert result.exit_code == -1


def test_retriever_report_schema_round_trip(tmp_path: Path) -> None:
    report_path = _sample_retriever_report(tmp_path)
    payload = json.loads(report_path.read_text())
    validate_retriever_report(payload)


def test_planner_generates_plan(tmp_path: Path, monkeypatch) -> None:
    report_path = _sample_retriever_report(tmp_path)
    output_dir = tmp_path / "planner"
    plan_path = synthesise_plan("123", report_path, output_dir)
    assert plan_path.exists()
    plan_payload = json.loads(plan_path.read_text())
    validate_planner_plan(plan_payload)
    markdown = output_dir / "plan.md"
    assert markdown.exists()


def test_critic_evaluate_executes_plan(tmp_path: Path) -> None:
    report_path = _sample_retriever_report(tmp_path)
    plan = PlannerPlan(
        metadata={"pr_number": "123", "planner_version": "test", "changed_file_count": 1},
        steps=[
            PlanStep(
                identifier="step-01",
                name="echo-check",
                description="Ensure python executable available",
                command=["python", "-c", "print('ok')"],
                rubric_categories=["Technical Accuracy", "Robustness"],
                continue_on_error=False,
            )
        ],
        rationale=["Smoke check"],
    )
    plan_path = tmp_path / "plan.json"
    plan.dump(plan_path)
    payload = json.loads(plan_path.read_text())
    validate_planner_plan(payload)

    output_dir = tmp_path / "critic"
    verdict_path = evaluate(
        pr_number="123",
        retriever_report=report_path,
        planner_plan=plan_path,
        output_dir=output_dir,
        update_memory=False,
    )
    assert verdict_path.exists()
    verdict_payload = json.loads(verdict_path.read_text())
    validate_critic_verdict(verdict_payload)
    markdown = output_dir / "critic_verdict.md"
    assert markdown.exists()
