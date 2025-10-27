#!/usr/bin/env python3
"""Audit LLM provider usage to ensure policy compliance."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Tuple


def load_events(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def compute_mix(events: Iterable[dict]) -> Tuple[Counter, int]:
    counter: Counter[str] = Counter()
    total = 0
    for event in events:
        provider = event.get("provider")
        if not provider:
            continue
        counter[provider] += 1
        total += 1
    return counter, total


def summarize(counter: Counter[str], total: int) -> dict:
    breakdown = {
        provider: {
            "count": count,
            "ratio": count / total if total else 0.0,
        }
        for provider, count in counter.items()
    }
    preferred = breakdown.get("gemini-2.5-flash", {"ratio": 0.0})
    fallback_ratio = sum(
        entry["ratio"]
        for provider, entry in breakdown.items()
        if provider != "gemini-2.5-flash"
    )
    return {
        "total_calls": total,
        "providers": breakdown,
        "preferred_ratio": preferred["ratio"],
        "fallback_ratio": fallback_ratio,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate provider policy compliance against invocation logs")
    parser.add_argument("log", type=Path, help="Path to JSONL log containing provider invocations")
    args = parser.parse_args()

    counter, total = compute_mix(load_events(args.log))
    report = summarize(counter, total)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
