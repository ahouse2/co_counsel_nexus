from __future__ import annotations

from typing import Any, Dict, List, Tuple


class QAAgent:
    """Rubric-based QA adjudicator mirroring the TRD evaluation categories."""

from backend.app.config import get_settings


    rubric_categories = [
        "Technical Accuracy",
        "Modularity",
        "Performance",
        "Security",
        "Scalability",
        "Robustness",
        "Maintainability",
        "Innovation",
        "UX/UI Quality",
        "Explainability",
        "Coordination",
        "DevOps Readiness",
        "Documentation",
        "Compliance",
        "Enterprise Value",
    ]

    def evaluate(
        self,
        question: str,
        retrieval: Dict[str, Any],
        forensics_bundle: Dict[str, Any],
        telemetry: Dict[str, Any],
    ) -> Tuple[Dict[str, float], List[str], float]:
        answer: str = retrieval.get("answer", "")
        citations: List[Dict[str, Any]] = retrieval.get("citations", [])
        traces: Dict[str, Any] = retrieval.get("traces", {})
        graph = traces.get("graph", {})
        vector_hits = len(traces.get("vector", []))
        graph_nodes = len(graph.get("nodes", []))
        graph_edges = len(graph.get("edges", []))
        privilege = traces.get("privilege", {})
        privileged_docs = [
            item for item in privilege.get("decisions", []) if item.get("label") == "privileged"
        ]
        privilege_max = max(
            (float(item.get("score", 0.0)) for item in privilege.get("decisions", [])),
            default=0.0,
        )
        artifacts: List[Dict[str, Any]] = forensics_bundle.get("artifacts", [])
        artifact_count = len(artifacts)
        forensics_signals = sum(len(item.get("signals", [])) for item in artifacts)
        turn_roles: List[str] = telemetry.get("turn_roles", [])
        durations: List[float] = telemetry.get("durations_ms", [])
        total_duration = telemetry.get("total_duration_ms", 0.0)
        max_duration = max(durations) if durations else 0.0

        def score(base: float, *adjustments: float) -> float:
            value = base + sum(adjustments)
            return round(max(1.0, min(10.0, value)), 2)

        has_citations = len(citations) > 0
        multi_citations = len(citations) >= 2
        answer_length = len(answer)
        sequence_valid = telemetry.get("sequence_valid", False)

        scores: Dict[str, float] = {}
        scores["Technical Accuracy"] = score(
            7.2,
            0.8 if answer_length > 120 else 0.3 if answer_length > 40 else 0.0,
            0.5 if graph_edges else 0.0,
            0.5 if artifact_count else 0.0,
        )
        scores["Modularity"] = score(
            7.0,
            0.7 if len(turn_roles) >= 3 else 0.3 if len(turn_roles) == 2 else 0.0,
            0.3 if artifact_count else 0.0,
        )
        scores["Performance"] = score(
            7.4,
            0.8 if total_duration < 1200 else (-0.3 if total_duration > 3200 else 0.0),
            0.4 if vector_hits >= 3 else 0.2 if vector_hits else 0.0,
        )
        scores["Security"] = score(
            7.0,
            0.6 if forensics_signals == 0 else 0.3,
            0.4 if has_citations else 0.0,
        )
        scores["Scalability"] = score(
            7.0,
            0.6 if vector_hits >= 3 else 0.3 if vector_hits else 0.0,
            0.4 if graph_nodes >= 3 else 0.1 if graph_nodes else 0.0,
        )
        scores["Robustness"] = score(
            7.2,
            0.5 if forensics_signals == 0 else 0.2,
            0.3 if multi_citations else 0.1 if has_citations else 0.0,
        )
        scores["Maintainability"] = score(
            7.3,
            0.5 if len(turn_roles) <= 4 else 0.2,
            0.2 if max_duration < 1500 else 0.0,
        )
        scores["Innovation"] = score(
            7.2,
            0.6 if graph_edges else 0.0,
            0.4 if artifact_count else 0.0,
        )
        scores["UX/UI Quality"] = score(
            7.1,
            0.6 if has_citations else 0.0,
            0.3 if 100 <= answer_length <= 400 else 0.1 if answer_length > 0 else 0.0,
        )
        scores["Explainability"] = score(
            8.0,
            0.7 if multi_citations else 0.4 if has_citations else 0.0,
            0.3 if artifact_count else 0.0,
        )
        scores["Coordination"] = score(
            7.4,
            0.6 if sequence_valid else 0.3 if len(turn_roles) >= 3 else 0.0,
            0.3 if total_duration and total_duration / max(len(turn_roles), 1) < 1500 else 0.0,
        )
        scores["DevOps Readiness"] = score(
            7.0,
            0.4 if total_duration <= 2500 else 0.0,
            0.4 if artifact_count else 0.2 if vector_hits else 0.0,
        )
        scores["Documentation"] = score(
            7.2,
            0.5 if has_citations else 0.0,
            0.3 if telemetry.get("notes", []) else 0.2,
        )
        scores["Compliance"] = score(
            7.0,
            0.5 if forensics_signals == 0 else 0.2,
            0.4 if artifact_count else 0.0,
            (-0.8 if privileged_docs else 0.0),
            (-0.4 if privilege_max >= 0.8 else (-0.2 if privilege_max >= 0.6 else 0.0)),
        )
        scores["Enterprise Value"] = score(
            7.1,
            0.6 if answer_length > 150 else 0.3 if answer_length else 0.0,
            0.4 if graph_edges or artifact_count else 0.0,
        )

        average = round(sum(scores.values()) / len(self.rubric_categories), 2)
        notes = [
            f"Answer length: {answer_length} characters.",
            f"Question tokens: {len(question.split())}.",
            f"Citations: {len(citations)}; Forensics artifacts: {artifact_count}; Graph edges: {graph_edges}.",
            f"Total runtime: {round(total_duration, 2)} ms across {len(turn_roles)} turns.",
        ]
        # HITL cue: surface a flag for supervisor review when HITL is enabled
        settings = get_settings()
        if getattr(settings, 'hitl_enabled', False):
            notes.append("HITL required: supervisor to review QA output before final action.")
            # We could also flag the telemetry or thread status here in a fuller implementation.

        if privileged_docs:
            doc_list = ", ".join(item.get("doc_id", "?") for item in privileged_docs)
            notes.append(f"Privilege alerts: {len(privileged_docs)} document(s) flagged ({doc_list}).")
        gating = telemetry.setdefault("gating", {})
        if privileged_docs:
            gating["requires_privilege_review"] = True
            gating["flagged_documents"] = [item.get("doc_id") for item in privileged_docs]
            gating["max_privilege_score"] = round(privilege_max, 4)
            telemetry["status"] = "needs_privilege_review"
        else:
            gating.setdefault("requires_privilege_review", False)
        return scores, notes, average
