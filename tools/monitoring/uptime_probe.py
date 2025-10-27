#!/usr/bin/env python3
"""Continuously probe the health endpoint and report uptime statistics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import httpx


class ProbeResult:
    __slots__ = ("timestamp", "status", "latency_ms", "error")

    def __init__(self, timestamp: datetime, status: int | None, latency_ms: float | None, error: str | None) -> None:
        self.timestamp = timestamp
        self.status = status
        self.latency_ms = latency_ms
        self.error = error

    def as_row(self) -> List[str]:
        return [
            self.timestamp.isoformat(),
            "" if self.status is None else str(self.status),
            "" if self.latency_ms is None else f"{self.latency_ms:.2f}",
            self.error or "",
        ]


def probe(base_url: str, interval: float, duration: float) -> List[ProbeResult]:
    deadline = time.time() + duration
    client = httpx.Client(base_url=base_url, timeout=10.0)
    results: List[ProbeResult] = []
    try:
        while time.time() < deadline:
            started = time.perf_counter()
            timestamp = datetime.now(timezone.utc)
            try:
                response = client.get("/health")
                latency_ms = (time.perf_counter() - started) * 1000.0
                results.append(ProbeResult(timestamp, response.status_code, latency_ms, None))
            except Exception as exc:  # pragma: no cover - resilience path
                results.append(ProbeResult(timestamp, None, None, str(exc)))
            time.sleep(interval)
    finally:
        client.close()
    return results


def summarize(results: List[ProbeResult]) -> dict:
    successes = sum(1 for entry in results if entry.status == 200)
    total = len(results)
    uptime_ratio = successes / total if total else 0.0
    latencies = [entry.latency_ms for entry in results if entry.latency_ms is not None]
    return {
        "samples": total,
        "successes": successes,
        "failures": total - successes,
        "uptime_ratio": uptime_ratio,
        "max_latency_ms": max(latencies) if latencies else None,
    }


def write_csv(results: List[ProbeResult], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "status", "latency_ms", "error"])
        for entry in results:
            writer.writerow(entry.as_row())


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor API uptime via /health polling")
    parser.add_argument("--base-url", default=os.environ.get("UPTIME_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--interval", type=float, default=60.0, help="Polling cadence in seconds")
    parser.add_argument("--duration", type=float, default=3600.0, help="Total probe duration in seconds")
    parser.add_argument("--csv", type=Path, help="Optional path to persist raw probe samples")
    args = parser.parse_args()

    results = probe(args.base_url, args.interval, args.duration)
    if args.csv:
        write_csv(results, args.csv)
    summary = summarize(results)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
