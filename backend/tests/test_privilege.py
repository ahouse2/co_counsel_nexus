from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.security.privilege_policy import PrivilegePolicyEngine
from backend.app.services.errors import WorkflowAbort
from backend.app.services.privilege import PrivilegeClassifierService, PrivilegeDecision
from backend.app.utils.audit import AuditTrail


@pytest.fixture()
def privilege_service() -> PrivilegeClassifierService:
    return PrivilegeClassifierService()


def test_privilege_classifier_incorporates_metadata_markers(privilege_service: PrivilegeClassifierService) -> None:
    decision = privilege_service.classify(
        "doc-meta",
        "Executive summary regarding settlement options and litigation posture.",
        {
            "classification": ["Attorney-Client Privileged"],
            "participants": ["Outside Counsel", "Chief Legal Officer"],
        },
    )
    assert decision.label == "privileged"
    assert decision.signals.get("metadata", 0.0) > 0.0
    assert "metadata" in decision.context
    assert "markers" in decision.context["metadata"]
    assert "Attorney-Client Privileged" in decision.context["metadata"]["markers"]


def test_privilege_classifier_graph_neighbors_boosts_score(privilege_service: PrivilegeClassifierService) -> None:
    decision = privilege_service.classify(
        "doc-graph",
        "Meeting notes documenting attorney-client review of discovery obligations.",
        {
            "graph_neighbors": [{"type": "ATTORNEY_CLIENT_PRIVILEGED"}],
        },
    )
    assert decision.label == "privileged"
    assert decision.signals.get("graph", 0.0) > 0.0
    assert decision.context.get("graph", {}).get("hits", 0) >= 1


def test_privilege_classifier_handles_empty_text(privilege_service: PrivilegeClassifierService) -> None:
    decision = privilege_service.classify("doc-empty", "", {})
    assert decision.label == "unknown"
    assert decision.score == 0.0


def test_privilege_policy_engine_blocks_high_risk(tmp_path: Path) -> None:
    audit = AuditTrail(tmp_path / "audit.log")
    engine = PrivilegePolicyEngine(review_threshold=0.6, block_threshold=0.9, audit_trail=audit)
    high_risk = PrivilegeDecision(
        doc_id="doc-critical",
        label="privileged",
        score=0.95,
        explanation="",
        source="test",
    )
    with pytest.raises(WorkflowAbort) as exc:
        engine.enforce([high_risk], query="sensitive query", correlation_id="trace-1234")
    assert exc.value.error.code == "privilege.blocked"
    assert audit.verify()


def test_privilege_policy_engine_flags_review_without_block(tmp_path: Path) -> None:
    audit = AuditTrail(tmp_path / "audit.log")
    engine = PrivilegePolicyEngine(review_threshold=0.5, block_threshold=0.9, audit_trail=audit)
    borderline = PrivilegeDecision(
        doc_id="doc-review",
        label="privileged",
        score=0.64,
        explanation="",
        source="test",
    )
    decision = engine.enforce([borderline], query="status", correlation_id="trace-5678", raise_on_block=False)
    assert decision.status == "review"
    assert decision.requires_review
    assert not decision.blocked
    assert decision.audit_reference is not None
    assert audit.verify()
