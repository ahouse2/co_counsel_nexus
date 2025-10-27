#!/usr/bin/env python3
"""Replay ingestion runs to ensure deterministic outputs."""

from __future__ import annotations

import importlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from fastapi.testclient import TestClient
from PIL import Image


@dataclass
class Snapshot:
    job_manifest: Dict[str, object]
    timeline_events: List[Dict[str, object]]
    forensics_hashes: Dict[str, Dict[str, str]]


def _build_workspace(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "case_notes.txt").write_text(
        "Acme Corporation filed suit on 2024-09-15."
        " Settlement closed on 2024-10-01 with regulators notified."
    )
    Image.new("RGB", (32, 32), color=(120, 45, 90)).save(root / "evidence.png")
    (root / "ledger.csv").write_text("entity,amount\nAcme,100.0\nBeta,400.0\n")
    return root


def _configure_environment(tmp: Path) -> None:
    storage_root = tmp / "storage"
    storage_root.mkdir()
    os.environ["NEO4J_URI"] = "memory://"
    os.environ["QDRANT_PATH"] = str(storage_root / "qdrant")
    os.environ.pop("QDRANT_URL", None)
    os.environ["VECTOR_DIR"] = str(storage_root / "vector")
    os.environ["FORENSICS_DIR"] = str(storage_root / "forensics")
    os.environ["TIMELINE_PATH"] = str(storage_root / "timeline.jsonl")
    os.environ["JOB_STORE_DIR"] = str(storage_root / "jobs")
    os.environ["DOCUMENT_STORE_DIR"] = str(storage_root / "documents")
    for subdir in ("qdrant", "vector", "forensics", "jobs", "documents"):
        (storage_root / subdir).mkdir(exist_ok=True)


def _bootstrap_client() -> TestClient:
    from backend.app import config
    from backend.app.services import graph as graph_service
    from backend.app.services import vector as vector_service

    config.reset_settings_cache()
    vector_service.reset_vector_service()
    graph_service.reset_graph_service()

    main_module = importlib.import_module("backend.app.main")
    importlib.reload(main_module)
    return TestClient(main_module.app)


def _ingest(client: TestClient, workspace: Path) -> str:
    response = client.post(
        "/ingest",
        json={"sources": [{"type": "local", "path": str(workspace)}]},
    )
    response.raise_for_status()
    return response.json()["job_id"]


def _snapshot(tmp: Path, job_id: str) -> Snapshot:
    job_manifest = json.loads((tmp / "storage" / "jobs" / f"{job_id}.json").read_text())
    timeline_path = Path(os.environ["TIMELINE_PATH"])
    timeline_events = [json.loads(line) for line in timeline_path.read_text().splitlines() if line]
    forensics_root = Path(os.environ["FORENSICS_DIR"])
    hashes: Dict[str, Dict[str, str]] = {}
    if forensics_root.exists():
        for directory in forensics_root.iterdir():
            doc_hashes: Dict[str, str] = {}
            doc_file = directory / "document.json"
            if doc_file.exists():
                payload = json.loads(doc_file.read_text())
                doc_hashes = payload.get("hashes", {})
            hashes[directory.name] = doc_hashes
    return Snapshot(job_manifest=job_manifest, timeline_events=timeline_events, forensics_hashes=hashes)


def run_trial() -> Snapshot:
    with tempfile.TemporaryDirectory(prefix="nfr_replay_") as tmp_dir:
        tmp = Path(tmp_dir)
        _configure_environment(tmp)
        workspace = _build_workspace(tmp / "workspace")
        client = _bootstrap_client()
        job_id = _ingest(client, workspace)
        return _snapshot(tmp, job_id)


def main() -> None:
    first = run_trial()
    second = run_trial()

    assert first.job_manifest == second.job_manifest, "Job manifest drift detected"
    assert first.timeline_events == second.timeline_events, "Timeline events drift detected"
    assert first.forensics_hashes == second.forensics_hashes, "Forensics digests drift detected"
    print("Reproducibility check passed: no drift across consecutive runs")


if __name__ == "__main__":
    main()
