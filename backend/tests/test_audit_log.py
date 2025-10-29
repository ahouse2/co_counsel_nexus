from __future__ import annotations

import json
from pathlib import Path

from backend.app.utils.audit import AuditEvent, AuditTrail


def test_audit_trail_append_and_verify(tmp_path: Path) -> None:
    trail = AuditTrail(tmp_path / "audit.jsonl")
    event1 = AuditEvent(
        category="security",
        action="security.authz",
        actor={"id": "client-1"},
        subject={"resource": "ingest.enqueue"},
        outcome="allowed",
        metadata={"status_code": 200},
    )
    event2 = AuditEvent(
        category="ingestion",
        action="ingest.job.accepted",
        actor={"id": "client-1"},
        subject={"job_id": "job-123"},
        outcome="accepted",
        metadata={"source_count": 2},
    )
    trail.append(event1)
    trail.append(event2)
    assert trail.verify() is True

    audit_path = tmp_path / "audit.jsonl"
    records = audit_path.read_text().splitlines()
    tampered = json.loads(records[0])
    tampered["metadata"]["status_code"] = 500
    records[0] = json.dumps(tampered)
    audit_path.write_text("\n".join(records) + "\n")
    assert trail.verify() is False


def test_audit_trail_lineage_stable(tmp_path: Path) -> None:
    trail = AuditTrail(tmp_path / "lineage.jsonl")
    event = AuditEvent(
        category="agents",
        action="agents.thread.created",
        actor={"id": "orchestrator", "roles": ["System"]},
        subject={"thread_id": "thread-1"},
        outcome="accepted",
        metadata={},
    )
    digest = trail.append(event)
    assert isinstance(digest, str) and len(digest) == 64
    with (tmp_path / "lineage.jsonl").open("r", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    assert record["lineage"] == event.to_payload()["lineage"]
