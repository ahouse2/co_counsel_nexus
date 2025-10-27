"""Validate that Markdown cross-links resolve within the repository.

The validator scans:
- docs/ONBOARDING.md
- docs/AgentsMD_PRPs_and_AgentMemory/PRPs/**/*.md

Absolute HTTP(S) links are ignored; only relative links are checked.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

RE_MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)#]+(?:#[^)]+)?)\)")

DEFAULT_TARGETS = [
    Path("docs/ONBOARDING.md"),
    *sorted(Path("docs/AgentsMD_PRPs_and_AgentMemory/PRPs").rglob("*.md")),
]


class LinkError(RuntimeError):
    """Raised when a referenced file does not exist."""


def extract_links(markdown: str) -> Sequence[str]:
    matches = RE_MARKDOWN_LINK.findall(markdown)
    return list(matches)


def is_external(link: str) -> bool:
    lowered = link.lower()
    return lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("mailto:")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding="utf-8")
    for raw_link in extract_links(content):
        link, *_ = raw_link.split("#", 1)
        link = link.strip()
        if not link or is_external(link):
            continue
        target = (path.parent / link).resolve()
        try:
            target.relative_to(Path.cwd())
        except ValueError:
            errors.append(f"{path}: link '{raw_link}' resolves outside repository")
            continue
        if not target.exists():
            errors.append(f"{path}: missing target '{raw_link}' -> {target}")
    return errors


def collect_targets(include: Iterable[str] | None = None) -> Sequence[Path]:
    if not include:
        return DEFAULT_TARGETS
    targets: list[Path] = []
    for entry in include:
        path = Path(entry)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.md")))
        else:
            targets.append(path)
    return targets


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files or directories to validate. Defaults to onboarding and PRP docs.",
    )
    args = parser.parse_args(argv)

    targets = collect_targets(args.paths)
    missing = []
    for target in targets:
        if not target.exists():
            missing.append(f"Target file not found: {target}")
            continue
        missing.extend(validate_file(target))

    if missing:
        for error in missing:
            print(error, file=sys.stderr)
        return 1

    print(f"Validated {len(targets)} markdown files. All links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
