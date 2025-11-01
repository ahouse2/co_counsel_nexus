from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB

from ..config import get_settings
from .graph import GraphService, get_graph_service


_LOGGER = logging.getLogger(__name__)
_GRAPH_PRIVILEGE_KEYWORDS: Tuple[str, ...] = (
    "PRIVILEGED",
    "ATTORNEY",
    "WORK_PRODUCT",
    "LEGAL_HOLD",
    "REPRESENTS",
    "CONFIDENTIAL",
)


@dataclass
class PrivilegeDecision:
    doc_id: str
    label: str
    score: float
    explanation: str
    source: str = "classifier"
    signals: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "doc_id": self.doc_id,
            "label": self.label,
            "score": round(self.score, 4),
            "explanation": self.explanation,
            "source": self.source,
        }
        if self.signals:
            payload["signals"] = {key: round(value, 4) for key, value in self.signals.items()}
        if self.context:
            payload["context"] = self.context
        return payload


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
        self.secondary_model = ComplementNB()
        self._graph_service: GraphService | None = None
        self.ensemble_weights = {
            "logistic": 0.55,
            "nb": 0.35,
        }
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
        logistic_score = float(probabilities[1])
        nb_probabilities = self.secondary_model.predict_proba(features)[0]
        nb_score = float(nb_probabilities[1])
        metadata_score, metadata_weight, metadata_context = self._metadata_signal(metadata)
        graph_score, graph_weight, graph_context = self._graph_signal(doc_id, metadata)
        combined_score, signals = self._combine_scores(
            {"logistic": logistic_score, "nb": nb_score},
            (
                ("metadata", metadata_score, metadata_weight),
                ("graph", graph_score, graph_weight),
            ),
        )
        label = "privileged" if combined_score >= self.threshold else "non_privileged"
        explanation = self._build_explanation(
            combined_score,
            metadata,
            signals,
            metadata_context,
            graph_context,
        )
        context: Dict[str, object] = {}
        if metadata_context:
            context["metadata"] = metadata_context
        if graph_context:
            context["graph"] = graph_context
        return PrivilegeDecision(
            doc_id=doc_id,
            label=label,
            score=combined_score,
            explanation=explanation,
            signals=signals,
            context=context,
        )

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
        if max_decision.signals:
            dominant = max(max_decision.signals.items(), key=lambda item: item[1])
            rationale_parts.append(f"dominant={dominant[0]}:{dominant[1]:.2f}")
        return PrivilegeSummary(label=label, score=average_score, flagged=flagged, rationale="; ".join(rationale_parts))

    def format_trace(self, decisions: List[PrivilegeDecision]) -> Dict[str, object]:
        summary = self.aggregate(decisions)
        return {
            "decisions": [decision.to_dict() for decision in decisions],
            "aggregate": summary.to_dict(),
        }

    def _combine_scores(
        self,
        model_scores: Dict[str, float],
        contextual_signals: Sequence[Tuple[str, float, float]],
    ) -> Tuple[float, Dict[str, float]]:
        contributions: List[Tuple[str, float, float]] = []
        for name, score in model_scores.items():
            weight = float(self.ensemble_weights.get(name, 0.0))
            if weight <= 0.0:
                continue
            contributions.append((name, float(max(0.0, min(1.0, score))), weight))
        for name, score, weight in contextual_signals:
            if weight <= 0.0:
                continue
            contributions.append((name, float(max(0.0, min(1.0, score))), float(weight)))
        if not contributions:
            return 0.0, {}
        total_weight = sum(weight for _, _, weight in contributions)
        if total_weight == 0.0:
            total_weight = float(len(contributions))
        combined = sum(score * weight for _, score, weight in contributions) / total_weight
        signals = {name: round(score, 4) for name, score, _ in contributions}
        return float(max(0.0, min(1.0, combined))), signals

    def _metadata_signal(self, metadata: Dict[str, object]) -> Tuple[float, float, Dict[str, object]]:
        if not metadata:
            return 0.0, 0.0, {}
        markers: List[str] = []
        negative_markers: List[str] = []
        sensitivity_fields: Sequence[str] = (
            "classification",
            "sensitivity",
            "labels",
            "tags",
            "document_markings",
        )
        privileged_tokens = {"privileged", "attorney", "work product", "confidential"}
        public_tokens = {"public", "press", "newsletter", "announcement"}
        privileged_hits = 0
        negative_hits = 0
        for key in sensitivity_fields:
            raw = metadata.get(key)
            if raw is None:
                continue
            values: Sequence[str]
            if isinstance(raw, str):
                values = [raw]
            elif isinstance(raw, (list, tuple, set)):
                values = [str(item) for item in raw]
            else:
                continue
            for value in values:
                token = value.lower()
                if any(marker in token for marker in privileged_tokens):
                    privileged_hits += 1
                    markers.append(value)
                if any(marker in token for marker in public_tokens):
                    negative_hits += 1
                    negative_markers.append(value)
        actors = metadata.get("participants") or metadata.get("recipients") or metadata.get("authors")
        if isinstance(actors, (list, tuple, set)):
            for actor in actors:
                token = str(actor).lower()
                if "counsel" in token or "attorney" in token or "legal" in token:
                    privileged_hits += 1
                    markers.append(str(actor))
        score = 0.0
        weight = 0.0
        if privileged_hits:
            score = min(1.0, 0.65 + 0.07 * privileged_hits)
            weight = min(0.2, 0.05 * privileged_hits + 0.05)
        if negative_hits and score == 0.0:
            score = max(0.0, 0.2 - 0.05 * min(negative_hits, 3))
            weight = min(0.1, 0.03 * negative_hits)
        context: Dict[str, object] = {}
        if markers:
            context["markers"] = markers
        if negative_markers:
            context["negative_markers"] = negative_markers
        context["privileged_hits"] = privileged_hits
        context["negative_hits"] = negative_hits
        return score, weight, context

    def _graph_signal(
        self, doc_id: str, metadata: Dict[str, object]
    ) -> Tuple[float, float, Dict[str, object]]:
        neighbors = metadata.get("graph_neighbors")
        privileged_hits = 0
        total_edges = 0
        context: Dict[str, object] = {}
        if isinstance(neighbors, (list, tuple)):
            for entry in neighbors:
                if not isinstance(entry, dict):
                    continue
                relation = str(entry.get("type") or entry.get("relation") or "")
                if not relation:
                    continue
                total_edges += 1
                if any(keyword in relation.upper() for keyword in _GRAPH_PRIVILEGE_KEYWORDS):
                    privileged_hits += 1
            if total_edges:
                context["neighbors"] = min(total_edges, 10)
        entity_ids = metadata.get("entity_ids")
        if not privileged_hits and entity_ids:
            service = self._ensure_graph_service()
            if service is not None:
                try:
                    subgraph = service.subgraph([str(entity) for entity in entity_ids if entity is not None])
                except Exception as exc:  # pragma: no cover - defensive safeguard
                    _LOGGER.debug("Graph privilege enrichment failed", exc_info=exc)
                else:
                    sample_edges: List[Dict[str, object]] = []
                    for edge in subgraph.edges.values():
                        edge_doc = edge.properties.get("doc_id")
                        if edge_doc is not None and str(edge_doc) != doc_id:
                            continue
                        total_edges += 1
                        relation = str(edge.type)
                        if any(keyword in relation.upper() for keyword in _GRAPH_PRIVILEGE_KEYWORDS):
                            privileged_hits += 1
                            sample_edges.append({
                                "type": relation,
                                "properties": {
                                    key: value
                                    for key, value in edge.properties.items()
                                    if key in {"doc_id", "classification", "channel"}
                                },
                            })
                    if sample_edges:
                        context["edges"] = sample_edges[:3]
        if total_edges == 0:
            return 0.0, 0.0, context
        score = min(1.0, 0.6 + 0.08 * privileged_hits) if privileged_hits else 0.0
        weight = 0.0 if not privileged_hits else min(0.15, 0.05 * privileged_hits + 0.05)
        context["hits"] = privileged_hits
        context["observations"] = total_edges
        return score, weight, context

    def _ensure_graph_service(self) -> GraphService | None:
        if self._graph_service is not None:
            return self._graph_service
        try:
            self._graph_service = get_graph_service()
        except Exception:  # pragma: no cover - graph dependencies optional
            _LOGGER.debug("Graph service unavailable for privilege ensemble", exc_info=True)
            self._graph_service = None
        return self._graph_service

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
        self.secondary_model.fit(features, labels)

    def _build_explanation(
        self,
        score: float,
        metadata: Dict[str, object],
        signals: Dict[str, float],
        metadata_context: Dict[str, object],
        graph_context: Dict[str, object],
    ) -> str:
        hints: List[str] = []
        subject = metadata.get("subject") or metadata.get("title")
        if subject:
            hints.append(f"subject={subject}")
        if metadata.get("type"):
            hints.append(f"type={metadata['type']}")
        if metadata_context.get("markers"):
            hints.append(
                "markers=" + ";".join(str(marker) for marker in metadata_context["markers"][:3])
            )
        if graph_context.get("hits"):
            hints.append(f"graph_hits={graph_context['hits']}")
        if signals:
            ranked = sorted(signals.items(), key=lambda item: item[1], reverse=True)
            top = [f"{name}:{value:.2f}" for name, value in ranked[:3]]
            hints.append("signals=" + ";".join(top))
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
