"""Critic stage executing plan commands and evaluating rubric thresholds."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .artefacts import (
    CommandResult,
    CriticVerdict,
    PlanStep,
    PlannerPlan,
    RetrieverReport,
    RubricEntry,
    hydrate_planner_plan,
    hydrate_retriever_report,
)
from .config import load_config
from .fs import ensure_stage_directory
from .runner import CommandExecutionError, run_command
from .schema import validate_critic_verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_PATH = REPO_ROOT / "memory" / "ace_state.jsonl"


def _execute_step(step: PlanStep) -> CommandResult:
    try:
        return run_command(
            step.name,
            step.command,
            cwd=str(REPO_ROOT),
            optional=step.continue_on_error,
        )
    except CommandExecutionError as exc:
        if step.continue_on_error:
            return exc.result
        raise


def _initial_scores(categories: List[str]) -> Dict[str, float]:
    return {category: 8.5 for category in categories}


def _update_scores(
    scores: Dict[str, float],
    step: PlanStep,
    result: CommandResult,
) -> None:
    for category in step.rubric_categories:
        baseline = scores.get(category, 8.0)
        if result.status == "success":
            scores[category] = min(10.0, baseline + 0.4)
        elif result.status == "skipped":
            scores[category] = min(baseline, 7.0)
        else:
            scores[category] = 5.0


def _scores_to_entries(scores: Dict[str, float]) -> List[RubricEntry]:
    return [
        RubricEntry(category=category, score=value, rationale="Automated evaluation")
        for category, value in scores.items()
    ]


def _summarise_recommendations(
    plan: PlannerPlan,
    results: List[CommandResult],
) -> List[str]:
    notes: List[str] = []
    for step, result in zip(plan.steps, results):
        if result.status == "failure":
            notes.append(
                f"{step.name}: command {' '.join(step.command)} failed with exit code {result.exit_code}."
            )
        elif result.status == "skipped":
            notes.append(
                f"{step.name}: executable '{step.command[0]}' missing — install before merging."
            )
    if not notes:
        notes.append("All planned checks succeeded.")
    return notes


def _should_block(scores: Dict[str, float], average_min: float, category_min: float) -> bool:
    average = sum(scores.values()) / len(scores)
    minimum = min(scores.values())
    return average < average_min or minimum < category_min


def _append_memory(verdict: CriticVerdict, retriever: RetrieverReport, plan: PlannerPlan) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "ChatGPT",
        "role": "critic",
        "summary": verdict.metadata.get("summary"),
        "files": retriever.changed_files,
        "ci_checks": [
            {
                "command": " ".join(result.command),
                "status": result.status,
                "exit_code": result.exit_code,
            }
            for result in verdict.command_results
        ],
        "notes": " | ".join(verdict.recommendations),
    }
    with MEMORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload))
        handle.write("\n")


def evaluate(
    *,
    pr_number: str,
    retriever_report: Path,
    planner_plan: Path,
    output_dir: Path,
    update_memory: bool = False,
) -> Path:
    config = load_config()
    retriever = hydrate_retriever_report(retriever_report)
    plan = hydrate_planner_plan(planner_plan)

    results: List[CommandResult] = []
    for step in plan.steps:
        result = _execute_step(step)
        results.append(result)

    scores = _initial_scores(config.rubric_categories)
    for step, result in zip(plan.steps, results):
        _update_scores(scores, step, result)

    entries = _scores_to_entries(scores)
    average = sum(scores.values()) / len(scores)
    minimum = min(scores.values())
    block = _should_block(scores, config.thresholds.average_min, config.thresholds.category_min)

    status = "block" if block or any(result.status == "failure" for result in results) else "pass"

    metadata: Dict[str, object] = {
        "pr_number": pr_number,
        "retriever_report": str(retriever_report),
        "planner_plan": str(planner_plan),
        "summary": f"ACE critic {'blocked' if status == 'block' else 'approved'} the PR.",
    }

    verdict = CriticVerdict(
        status=status,
        average_score=average,
        minimum_score=minimum,
        rubric=entries,
        command_results=results,
        recommendations=_summarise_recommendations(plan, results),
        metadata=metadata,
    )
    payload = verdict.to_dict()
    validate_critic_verdict(payload)

    output_dir.mkdir(parents=True, exist_ok=True)
    verdict_path = output_dir / "critic_verdict.json"
    verdict.dump(verdict_path)

    markdown_path = output_dir / "critic_verdict.md"
    with markdown_path.open("w", encoding="utf-8") as handle:
        handle.write("# ACE Critic Verdict\n\n")
        handle.write(f"- Status: {status}\n")
        handle.write(f"- Average score: {average:.2f}\n")
        handle.write(f"- Minimum score: {minimum:.2f}\n\n")
        handle.write("## Rubric Scores\n")
        for entry in entries:
            handle.write(f"- {entry.category}: {entry.score:.2f} — {entry.rationale}\n")
        handle.write("\n## Recommendations\n")
        for note in verdict.recommendations:
            handle.write(f"- {note}\n")

    if update_memory:
        _append_memory(verdict, retriever, plan)

    comment_path = output_dir / "pr_comment.md"
    with comment_path.open("w", encoding="utf-8") as handle:
        emoji = "✅" if status == "pass" else "❌"
        handle.write(f"{emoji} **ACE Critic {status.upper()}**\n\n")
        handle.write(f"Average score: {average:.2f} (min {minimum:.2f})\n\n")
        handle.write("| Category | Score |\n| --- | --- |\n")
        for entry in entries:
            handle.write(f"| {entry.category} | {entry.score:.2f} |\n")
        handle.write("\n")
        for note in verdict.recommendations:
            handle.write(f"> {note}\n")

    return verdict_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ACE critic stage")
    parser.add_argument("--pr-number", default="local-run", help="Pull request identifier")
    parser.add_argument("--retriever-report", type=Path, required=True)
    parser.add_argument("--planner-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, help="Directory for critic artefacts")
    parser.add_argument("--update-memory", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir or ensure_stage_directory(args.pr_number, "critic")
    verdict_path = evaluate(
        pr_number=args.pr_number,
        retriever_report=args.retriever_report,
        planner_plan=args.planner_plan,
        output_dir=output_dir,
        update_memory=args.update_memory,
    )
    print(f"Critic artefacts written to {verdict_path.parent}")


if __name__ == "__main__":
    main()
