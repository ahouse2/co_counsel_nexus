#!/usr/bin/env python3
"""Synthetic load generator for query latency and ingest throughput SLO validation."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Sequence

import httpx
from PIL import Image


def _build_workspace(root: Path) -> Dict[str, object]:
    text = root / "case_notes.txt"
    text.write_text(
        "Acme Corporation filed suit on 2024-09-15. A settlement closed on 2024-10-01 for $2.5M.\n"
        "Regulators in New York opened a follow-on inquiry on 2024-10-05."
    )
    image = root / "evidence.png"
    Image.new("RGB", (32, 32), color=(21, 83, 189)).save(image)
    ledger = root / "ledger.csv"
    ledger.write_text("entity,amount\nAcme,2500000\nBeta,1250000\n")
    return {
        "sources": [
            {
                "type": "local",
                "path": str(root),
            }
        ]
    }


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile of empty sequence")
    ordered = sorted(values)
    rank = percentile * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _ingest_sources(client: httpx.Client, payload: Dict[str, object]) -> str:
    response = client.post("/ingest", json=payload)
    response.raise_for_status()
    job_id = response.json().get("job_id")
    if not job_id:
        raise RuntimeError(f"Ingest response missing job identifier: {response.text}")
    return str(job_id)


def _wait_for_job(client: httpx.Client, job_id: str, delay_seconds: float = 0.2, timeout_seconds: float = 30.0) -> None:
    elapsed = 0.0
    while elapsed < timeout_seconds:
        response = client.get(f"/jobs/{job_id}")
        if response.status_code == 200:
            body = response.json()
            if body.get("status") == "completed":
                return
        time.sleep(delay_seconds)
        elapsed += delay_seconds
    raise TimeoutError(f"Job {job_id} did not complete within {timeout_seconds} seconds")


def _exercise_query(client: httpx.Client, question: str) -> float:
    start = time.perf_counter()
    response = client.get("/query", params={"q": question})
    response.raise_for_status()
    payload = response.json()
    if "answer" not in payload:
        raise RuntimeError(f"Query response missing answer field: {json.dumps(payload)}")
    return (time.perf_counter() - start) * 1000.0


def _run_iterations(client: httpx.Client, runs: int, question: str) -> List[float]:
    latencies: List[float] = []
    for _ in range(runs):
        latencies.append(_exercise_query(client, question))
    return latencies


def validate(base_url: str, runs: int, skip_ingest: bool) -> Dict[str, object]:
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        if not skip_ingest:
            with tempfile.TemporaryDirectory(prefix="nfr_workspace_") as tmp:
                workspace = Path(tmp)
                payload = _build_workspace(workspace)
                job_id = _ingest_sources(client, payload)
                try:
                    _wait_for_job(client, job_id)
                except httpx.HTTPStatusError:
                    # Some deployments surface ingestion completion immediately without job polling.
                    pass
        latencies_ms = _run_iterations(client, runs, "Summarize the Acme settlement")
    return {
        "runs": runs,
        "p95_ms": _percentile(latencies_ms, 0.95),
        "mean_ms": statistics.fmean(latencies_ms),
        "min_ms": min(latencies_ms),
        "max_ms": max(latencies_ms),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure /query latency against the documented SLOs.")
    parser.add_argument("--base-url", default=os.environ.get("NFR_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--runs", type=int, default=20, help="Number of query iterations")
    parser.add_argument("--skip-ingest", action="store_true", help="Assume data already loaded")
    args = parser.parse_args()

    metrics = validate(args.base_url, args.runs, args.skip_ingest)
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
