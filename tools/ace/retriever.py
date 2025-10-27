"""Retriever stage implementation for ACE."""

from __future__ import annotations

import argparse

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from .artefacts import CommandResult, ContextBundle, DependencyRecord, RetrieverReport
from .config import load_config
from .fs import ensure_bundle_directory, ensure_stage_directory
from .runner import CommandExecutionError, run_command
from .schema import validate_retriever_report

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _collect_changed_files(base_ref: Optional[str], head_ref: Optional[str]) -> List[str]:
    head = head_ref or "HEAD"
    paths: Set[str] = set()
    try:
        if base_ref:
            diff_output = _git("diff", "--name-only", f"{base_ref}...{head}")
        else:
            diff_output = _git("diff", "--name-only", head)
        paths.update(filter(None, (line.strip() for line in diff_output.splitlines())))
    except subprocess.CalledProcessError:
        pass

    if not paths:
        status = _git("status", "--short")
        for line in status.splitlines():
            line = line.strip()
            if not line:
                continue
            components = line.split(maxsplit=1)
            if len(components) == 2:
                paths.add(components[1])

    return sorted(paths)


def _collect_dependencies() -> List[DependencyRecord]:
    try:
        output = subprocess.run(
            ["pipdeptree", "--json-tree"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        payload = json.loads(output)
        records: List[DependencyRecord] = []
        for package in payload:
            name = package.get("package", {}).get("key")
            version = package.get("package", {}).get("installed_version")
            if name and version:
                records.append(DependencyRecord(name=name, version=version))
        if records:
            return sorted(records, key=lambda record: record.name.lower())
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        pass

    fallback = subprocess.run(
        ["python", "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    payload = json.loads(fallback)
    records = [
        DependencyRecord(name=item["name"], version=item["version"])
        for item in payload
    ]
    return sorted(records, key=lambda record: record.name.lower())


def _gather_context_files(changed_files: Sequence[str], limit: int = 20) -> List[str]:
    references: List[str] = []
    for doc_path in DOCS_ROOT.rglob("*.md"):
        if len(references) >= limit:
            break
        try:
            text = doc_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(changed in text for changed in changed_files):
            references.append(str(doc_path.relative_to(REPO_ROOT)))
    if "docs/validation/2025-11-02_phase1_quality_review.md" not in references and (
        DOCS_ROOT / "validation" / "2025-11-02_phase1_quality_review.md"
    ).exists():
        references.append("docs/validation/2025-11-02_phase1_quality_review.md")
    return references[:limit]


def _derive_risks(
    changed_files: Sequence[str], static_analysis: Sequence[CommandResult]
) -> List[str]:
    risks: List[str] = []
    for entry in static_analysis:
        if entry.status == "failure":
            risks.append(
                f"Static analysis command '{entry.name}' failed; review stderr for remediation."
            )
    for path in changed_files:
        if path.startswith("backend/app/storage"):
            risks.append(
                "Storage layer touched — ensure path sanitisation and locking checks remain intact."
            )
        if path.startswith("docs/validation"):
            risks.append("Validation playbooks updated — confirm ACE workflows stay aligned with governance.")
        if path.startswith("tools/ace"):
            risks.append("ACE automation changed — run end-to-end pipeline dry run before merge.")
    return risks or ["No blocking risks detected; continue with planner synthesis."]


def build_report(
    *,
    pr_number: str,
    base_ref: Optional[str],
    head_ref: Optional[str],
    output_dir: Optional[Path] = None,
    context_limit: int = 20,
) -> Path:
    config = load_config()
    changed_files = _collect_changed_files(base_ref, head_ref)
    dependencies = _collect_dependencies()

    static_results: List[CommandResult] = []
    for command in config.static_analysis:
        try:
            result = run_command(
                command.name,
                command.command,
                cwd=command.working_directory,
                env=command.env,
                optional=command.optional,
            )
        except CommandExecutionError as exc:
            static_results.append(exc.result)
            raise
        else:
            static_results.append(result)

    context_dir = ensure_bundle_directory(pr_number)
    context_files = _gather_context_files(changed_files, context_limit)
    for relative_path in context_files:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        source = REPO_ROOT / relative
        if source.is_file():
            destination = context_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(source.read_text(encoding="utf-8"))
    manifest_path = context_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"files": context_files}, indent=2))

    metadata: Dict[str, object] = {
        "pr_number": pr_number,
        "base_ref": base_ref,
        "head_ref": head_ref or "HEAD",
        "repository": REPO_ROOT.name,
    }

    report = RetrieverReport(
        metadata=metadata,
        changed_files=changed_files,
        dependency_snapshot=dependencies,
        static_analysis=static_results,
        context_bundle=ContextBundle(
            root=str(context_dir.relative_to(REPO_ROOT)),
            files=context_files,
        ),
        risks=_derive_risks(changed_files, static_results),
    )
    payload = report.to_dict()
    validate_retriever_report(payload)

    stage_dir = output_dir or ensure_stage_directory(pr_number, "retriever")
    report_path = stage_dir / "retriever_report.json"
    report.dump(report_path)
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ACE retriever stage")
    parser.add_argument("--pr-number", default="local-run", help="Pull request number or identifier")
    parser.add_argument("--base-ref", help="Base git ref for diff")
    parser.add_argument("--head-ref", help="Head git ref for diff")
    parser.add_argument("--output-dir", type=Path, help="Directory to write artefacts into")
    parser.add_argument(
        "--context-limit", type=int, default=20, help="Maximum number of context documents to collect"
    )
    args = parser.parse_args()

    try:
        report_path = build_report(
            pr_number=args.pr_number,
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            output_dir=args.output_dir,
            context_limit=args.context_limit,
        )
    except CommandExecutionError as exc:
        print(exc)
        raise SystemExit(1)

    print(f"Retriever report written to {report_path}")


if __name__ == "__main__":
    main()
