"""Planner stage synthesising execution plan from retriever artefacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .artefacts import PlanStep, PlannerPlan, RetrieverReport, hydrate_retriever_report
from .config import load_config
from .fs import ensure_stage_directory
from .schema import validate_planner_plan


def _should_include(command_name: str, report: RetrieverReport) -> bool:
    changed = report.changed_files
    if command_name == "pytest-core":
        return any(path.endswith(".py") for path in changed)
    if command_name == "documentation-integrity":
        return any(path.startswith("docs/") for path in changed) or not changed
    if command_name == "reproducibility-regression":
        return any(
            path.startswith(prefix)
            for prefix in ("backend/", "services/", "apps/", "tools/ace")
            for path in changed
        )
    return True


def _rationale_for(command_name: str) -> str:
    if command_name == "pytest-core":
        return "Python sources changed — running pytest ensures behavioural integrity."
    if command_name == "documentation-integrity":
        return "Documentation touched — validating hyperlinks avoids broken onboarding flows."
    if command_name == "reproducibility-regression":
        return "Core services modified — replaying ingestion guards deterministic forensics output."
    return "Baseline governance requirement."


def synthesise_plan(pr_number: str, report_path: Path, output_dir: Path) -> Path:
    config = load_config()
    report = hydrate_retriever_report(report_path)

    steps: List[PlanStep] = []
    rationales: List[str] = []
    step_counter = 1
    for command in config.planner_commands:
        if not _should_include(command.name, report):
            continue
        identifier = f"step-{step_counter:02d}"
        step_counter += 1
        steps.append(
            PlanStep(
                identifier=identifier,
                name=command.name,
                description=command.description,
                command=command.command,
                rubric_categories=command.rubric_categories,
                continue_on_error=command.continue_on_error,
            )
        )
        rationales.append(_rationale_for(command.name))

    if not steps:
        fallback = config.planner_commands[0]
        steps.append(
            PlanStep(
                identifier="step-01",
                name=fallback.name,
                description=fallback.description,
                command=fallback.command,
                rubric_categories=fallback.rubric_categories,
                continue_on_error=fallback.continue_on_error,
            )
        )
        rationales.append("No specific heuristics triggered — defaulting to baseline test run.")

    metadata = {
        **report.metadata,
        "pr_number": pr_number,
        "changed_file_count": len(report.changed_files),
        "planner_version": "2025.11.03",
    }

    plan = PlannerPlan(metadata=metadata, steps=steps, rationale=rationales)
    payload = plan.to_dict()
    validate_planner_plan(payload)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "plan.json"
    plan.dump(json_path)

    markdown_path = output_dir / "plan.md"
    with markdown_path.open("w", encoding="utf-8") as handle:
        handle.write("# ACE Planner Execution Plan\n\n")
        for step in steps:
            handle.write(f"## {step.identifier} — {step.name}\n")
            handle.write(f"- Description: {step.description}\n")
            handle.write(f"- Command: ``{' '.join(step.command)}``\n")
            handle.write(
                "- Rubric coverage: {}\n\n".format(", ".join(step.rubric_categories))
            )
        handle.write("## Rationale\n")
        for item in rationales:
            handle.write(f"- {item}\n")

    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ACE planner stage")
    parser.add_argument("--pr-number", default="local-run", help="Pull request identifier")
    parser.add_argument(
        "--retriever-report",
        type=Path,
        required=True,
        help="Path to retriever_report.json",
    )
    parser.add_argument("--output-dir", type=Path, help="Directory for plan artefacts")
    args = parser.parse_args()

    output_dir = args.output_dir or ensure_stage_directory(args.pr_number, "planner")
    plan_path = synthesise_plan(args.pr_number, args.retriever_report, output_dir)
    print(f"Planner artefacts written to {plan_path.parent}")


if __name__ == "__main__":
    main()
