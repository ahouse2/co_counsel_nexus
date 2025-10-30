from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, TYPE_CHECKING

from ..config import get_settings
from ..services.errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowSeverity
from ..services.privilege import PrivilegeDecision
from ..utils.audit import AuditEvent, AuditTrail, get_audit_trail

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .authz import Principal


_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PrivilegePolicyDecision:
    status: str
    requires_review: bool
    blocked: bool
    flagged_documents: List[str] = field(default_factory=list)
    max_score: float = 0.0
    threshold: float = 0.0
    block_threshold: float = 0.0
    actions: List[str] = field(default_factory=list)
    triggered_rules: List[str] = field(default_factory=list)
    audit_reference: str | None = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "requires_review": self.requires_review,
            "blocked": self.blocked,
            "flagged_documents": list(self.flagged_documents),
            "max_score": round(self.max_score, 4),
            "threshold": round(self.threshold, 4),
            "block_threshold": round(self.block_threshold, 4),
            "actions": list(self.actions),
            "triggered_rules": list(self.triggered_rules),
            "audit_reference": self.audit_reference,
            "notes": list(self.notes),
        }


class PrivilegePolicyEngine:
    """Evaluate privilege classifier output against runtime policy rules."""

    def __init__(
        self,
        *,
        review_threshold: float,
        block_threshold: float,
        audit_category: str = "security.privilege",
        audit_trail: AuditTrail | None = None,
    ) -> None:
        self.review_threshold = float(review_threshold)
        self.block_threshold = float(max(block_threshold, review_threshold))
        self.audit_category = audit_category
        self._audit_trail = audit_trail

    @property
    def audit_trail(self) -> AuditTrail:
        if self._audit_trail is None:
            self._audit_trail = get_audit_trail()
        return self._audit_trail

    def evaluate(
        self,
        decisions: Iterable[PrivilegeDecision],
        *,
        principal: "Principal | None" = None,
        query: str | None = None,
        context: Dict[str, object] | None = None,
        correlation_id: str | None = None,
    ) -> PrivilegePolicyDecision:
        context = dict(context or {})
        decisions_list: List[PrivilegeDecision] = list(decisions)
        flagged_documents = [decision.doc_id for decision in decisions_list if decision.label == "privileged"]
        max_score = max((decision.score for decision in decisions_list), default=0.0)
        triggered_rules: List[str] = []
        actions: List[str] = []
        notes: List[str] = [f"decisions={len(decisions_list)}"]
        status = "allow"
        requires_review = False
        blocked = False

        if max_score >= self.block_threshold:
            status = "block"
            blocked = True
            requires_review = True
            triggered_rules.extend(["score_above_block_threshold"])
            actions.extend(["halt_response", "notify_privilege_officer"])
            notes.append(f"max_score={max_score:.4f} >= block_threshold")
        elif flagged_documents or max_score >= self.review_threshold:
            status = "review"
            requires_review = True
            triggered_rules.append("score_above_review_threshold")
            if flagged_documents:
                triggered_rules.append("documents_flagged")
            actions.append("route_privilege_review")
            if max_score:
                notes.append(f"max_score={max_score:.4f}")
        if flagged_documents:
            notes.append(f"flagged={','.join(flagged_documents)}")

        actions = list(dict.fromkeys(actions))
        triggered_rules = list(dict.fromkeys(triggered_rules))

        decision = PrivilegePolicyDecision(
            status=status,
            requires_review=requires_review,
            blocked=blocked,
            flagged_documents=flagged_documents,
            max_score=max_score,
            threshold=self.review_threshold,
            block_threshold=self.block_threshold,
            actions=actions,
            triggered_rules=triggered_rules,
            notes=notes,
        )

        outcome = "blocked" if blocked else ("review" if requires_review else "allowed")
        audit_reference = self._record_audit(
            decision,
            principal=principal,
            query=query,
            context=context,
            correlation_id=correlation_id,
            outcome=outcome,
        )
        decision.audit_reference = audit_reference
        return decision

    def enforce(
        self,
        decisions: Iterable[PrivilegeDecision],
        *,
        principal: "Principal | None" = None,
        query: str | None = None,
        context: Dict[str, object] | None = None,
        correlation_id: str | None = None,
        raise_on_block: bool = True,
    ) -> PrivilegePolicyDecision:
        decision = self.evaluate(
            decisions,
            principal=principal,
            query=query,
            context=context,
            correlation_id=correlation_id,
        )
        if decision.blocked and raise_on_block:
            error = WorkflowError(
                component=WorkflowComponent.SECURITY,
                code="privilege.blocked",
                message="Privilege policy blocked dissemination of retrieval results",
                severity=WorkflowSeverity.CRITICAL,
                context={
                    "flagged_documents": decision.flagged_documents,
                    "max_score": round(decision.max_score, 4),
                    "actions": decision.actions,
                    "triggered_rules": decision.triggered_rules,
                    "audit_reference": decision.audit_reference,
                },
            )
            raise WorkflowAbort(error, status_code=423)
        return decision

    def _record_audit(
        self,
        decision: PrivilegePolicyDecision,
        *,
        principal: "Principal | None" = None,
        query: str | None = None,
        context: Dict[str, object] | None = None,
        correlation_id: str | None = None,
        outcome: str,
    ) -> str | None:
        if not decision.requires_review and not decision.blocked:
            return None
        metadata = {
            "max_score": round(decision.max_score, 4),
            "flagged_documents": list(decision.flagged_documents),
            "actions": list(decision.actions),
            "triggered_rules": list(decision.triggered_rules),
        }
        if context:
            metadata.update({str(key): value for key, value in context.items()})
        if query:
            metadata["query"] = query
        actor: Dict[str, object] = {
            "client_id": getattr(principal, "client_id", "system"),
            "subject": getattr(principal, "subject", "system"),
            "tenant_id": getattr(principal, "tenant_id", "unknown"),
            "roles": sorted(getattr(principal, "roles", [])),
        }
        event = AuditEvent(
            category=self.audit_category,
            action="privilege.policy.evaluate",
            actor=actor,
            subject={"documents": list(decision.flagged_documents), "status": decision.status},
            outcome=outcome,
            severity="critical" if decision.blocked else "warning",
            correlation_id=correlation_id,
            metadata=metadata,
        )
        try:
            return self.audit_trail.append(event)
        except Exception:  # pragma: no cover - audit persistence failures should not break flow
            _LOGGER.exception("Failed to append privilege policy audit event", extra=metadata)
            return None


_policy_engine: PrivilegePolicyEngine | None = None


def get_privilege_policy_engine() -> PrivilegePolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        settings = get_settings()
        review_threshold = getattr(settings, "privilege_policy_review_threshold", settings.privilege_classifier_threshold)
        block_threshold = getattr(settings, "privilege_policy_block_threshold", max(review_threshold, 0.9))
        audit_category = getattr(settings, "privilege_policy_audit_category", "security.privilege")
        _policy_engine = PrivilegePolicyEngine(
            review_threshold=review_threshold,
            block_threshold=block_threshold,
            audit_category=audit_category,
        )
    return _policy_engine


def reset_privilege_policy_engine() -> None:
    global _policy_engine
    _policy_engine = None


__all__ = [
    "PrivilegePolicyDecision",
    "PrivilegePolicyEngine",
    "get_privilege_policy_engine",
    "reset_privilege_policy_engine",
]
