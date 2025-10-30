from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from ..config import get_settings


@dataclass
class PrivilegeDecision:
    doc_id: str
    label: str
    score: float
    explanation: str
    source: str = "classifier"

    def to_dict(self) -> Dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "label": self.label,
            "score": round(self.score, 4),
            "explanation": self.explanation,
            "source": self.source,
        }


@dataclass
class PrivilegeSummary:
    label: str
    score: float
    flagged: List[str]
    rationale: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "score": round(self.score, 4),
            "flagged": list(self.flagged),
            "rationale": self.rationale,
        }


class PrivilegeClassifierService:
    """Lightweight privilege classifier trained on curated exemplars."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.threshold = float(self.settings.privilege_classifier_threshold)
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            stop_words="english",
            max_features=4096,
            lowercase=True,
        )
        self.model = LogisticRegression(max_iter=250, random_state=42)
        self._train()

    def classify(self, doc_id: str, text: str, metadata: Dict[str, object] | None = None) -> PrivilegeDecision:
        metadata = metadata or {}
        text = (text or "").strip()
        linked_summary = metadata.get("linked_doc_summary")
        if linked_summary and isinstance(linked_summary, str):
            summary_clean = linked_summary.strip()
            if summary_clean:
                text = f"{text}\n\n{summary_clean}" if text else summary_clean
        source_type = str(metadata.get("source_type") or "").lower()
        if source_type in {"courtlistener", "caselaw"}:
            explanation = self._build_external_explanation(metadata)
            return PrivilegeDecision(
                doc_id=doc_id,
                label="non_privileged",
                score=0.0,
                explanation=explanation,
                source="classifier",
            )
        if not text:
            explanation = "No textual content supplied for privilege analysis."
            return PrivilegeDecision(doc_id=doc_id, label="unknown", score=0.0, explanation=explanation)
        features = self.vectorizer.transform([text])
        probabilities = self.model.predict_proba(features)[0]
        privileged_score = float(probabilities[1])
        label = "privileged" if privileged_score >= self.threshold else "non_privileged"
        explanation = self._build_explanation(privileged_score, metadata)
        return PrivilegeDecision(doc_id=doc_id, label=label, score=privileged_score, explanation=explanation)

    def classify_many(
        self, documents: Iterable[tuple[str, str, Dict[str, object] | None]]
    ) -> List[PrivilegeDecision]:
        decisions: List[PrivilegeDecision] = []
        for doc_id, text, metadata in documents:
            decisions.append(self.classify(doc_id, text, metadata))
        return decisions

    def aggregate(self, decisions: List[PrivilegeDecision]) -> PrivilegeSummary:
        if not decisions:
            return PrivilegeSummary(label="unknown", score=0.0, flagged=[], rationale="No evidence scored.")
        max_decision = max(decisions, key=lambda decision: decision.score)
        flagged = [decision.doc_id for decision in decisions if decision.label == "privileged"]
        label = "privileged" if flagged else "non_privileged"
        average_score = float(np.mean([decision.score for decision in decisions]))
        rationale_parts = [
            f"max={max_decision.doc_id}:{max_decision.score:.2f}",
            f"avg={average_score:.2f}",
            f"flagged={len(flagged)}",
        ]
        return PrivilegeSummary(label=label, score=average_score, flagged=flagged, rationale="; ".join(rationale_parts))

    def format_trace(self, decisions: List[PrivilegeDecision]) -> Dict[str, object]:
        summary = self.aggregate(decisions)
        return {
            "decisions": [decision.to_dict() for decision in decisions],
            "aggregate": summary.to_dict(),
        }

    def _train(self) -> None:
        privileged_samples = [
            "attorney-client communication regarding settlement strategy and trial preparation",
            "legal advice memo marked privileged and confidential from counsel to executive team",
            "internal audit findings shared with outside counsel for pending litigation",
            "draft contract annotated by lawyer containing privileged negotiation posture",
            "email summarising witness interview prepared at direction of legal department",
        ]
        non_privileged_samples = [
            "press release describing acquisition timeline and key milestones",
            "public filing summarising quarterly revenue and operational metrics",
            "customer support transcript discussing product configuration steps",
            "meeting minutes circulated to entire staff outlining marketing roadmap",
            "news article recapping regulatory approval received last month",
        ]
        corpus = privileged_samples + non_privileged_samples
        labels = [1] * len(privileged_samples) + [0] * len(non_privileged_samples)
        features = self.vectorizer.fit_transform(corpus)
        self.model.fit(features, labels)

    def _build_explanation(self, score: float, metadata: Dict[str, object] | None) -> str:
        if metadata is None:
            metadata = {}
        hints: List[str] = []
        subject = metadata.get("subject") or metadata.get("title")
        if subject:
            hints.append(f"subject={subject}")
        if metadata.get("type"):
            hints.append(f"type={metadata['type']}")
        hints.append(f"confidence={score:.2f}")
        return ", ".join(hints)

    def _build_external_explanation(self, metadata: Dict[str, object]) -> str:
        hints: List[str] = ["source=external_case_law"]
        case_name = metadata.get("case_name") or metadata.get("title")
        if case_name:
            hints.append(f"case={case_name}")
        linked = metadata.get("linked_doc_title")
        if linked:
            hints.append(f"linked={linked}")
        return ", ".join(hints)


_PRIVILEGE_CLASSIFIER: PrivilegeClassifierService | None = None


def get_privilege_classifier_service() -> PrivilegeClassifierService:
    global _PRIVILEGE_CLASSIFIER
    if _PRIVILEGE_CLASSIFIER is None:
        _PRIVILEGE_CLASSIFIER = PrivilegeClassifierService()
    return _PRIVILEGE_CLASSIFIER


def reset_privilege_classifier_service() -> None:
    global _PRIVILEGE_CLASSIFIER
    _PRIVILEGE_CLASSIFIER = None


__all__ = [
    "PrivilegeClassifierService",
    "PrivilegeDecision",
    "PrivilegeSummary",
    "get_privilege_classifier_service",
    "reset_privilege_classifier_service",
]
