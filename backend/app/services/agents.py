from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from ..config import get_settings
from ..security.authz import Principal
from ..storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord
from ..storage.document_store import DocumentStore
from ..utils.audit import AuditEvent, get_audit_trail
from .forensics import ForensicsService, get_forensics_service
from .retrieval import QueryResult, RetrievalService, get_retrieval_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentTurn:
    role: str
    action: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    started_at: datetime
    completed_at: datetime
    metrics: Dict[str, Any] = field(default_factory=dict)

    def duration_ms(self) -> float:
        return (self.completed_at - self.started_at).total_seconds() * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        metrics = dict(self.metrics)
        metrics.setdefault("duration_ms", round(self.duration_ms(), 2))
        return {
            "role": self.role,
            "action": self.action,
            "input": self.input,
            "output": self.output,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "metrics": metrics,
        }


@dataclass
class AgentThread:
    thread_id: str
    case_id: str
    question: str
    created_at: datetime
    updated_at: datetime
    turns: List[AgentTurn] = field(default_factory=list)
    final_answer: str = ""
    citations: List[Dict[str, Any]] = field(default_factory=list)
    qa_scores: Dict[str, float] = field(default_factory=dict)
    qa_notes: List[str] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> AgentThreadRecord:
        return AgentThreadRecord(
            thread_id=self.thread_id,
            payload={
                "thread_id": self.thread_id,
                "case_id": self.case_id,
                "question": self.question,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "turns": [turn.to_dict() for turn in self.turns],
                "final_answer": self.final_answer,
                "citations": self.citations,
                "qa_scores": self.qa_scores,
                "qa_notes": self.qa_notes,
                "telemetry": self.telemetry,
            },
        )


class QAAgent:
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
        privilege_max = max((float(item.get("score", 0.0)) for item in privilege.get("decisions", [])), default=0.0)
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
        if privileged_docs:
            doc_list = ", ".join(item.get("doc_id", "?") for item in privileged_docs)
            notes.append(f"Privilege alerts: {len(privileged_docs)} document(s) flagged ({doc_list}).")
        return scores, notes, average


class AgentsService:
    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        forensics_service: ForensicsService | None = None,
        memory_store: AgentMemoryStore | None = None,
        document_store: DocumentStore | None = None,
        qa_agent: QAAgent | None = None,
    ) -> None:
        self.settings = get_settings()
        self.retrieval_service = retrieval_service or get_retrieval_service()
        self.forensics_service = forensics_service or get_forensics_service()
        self.document_store = document_store or DocumentStore(self.settings.document_store_dir)
        self.memory_store = memory_store or AgentMemoryStore(self.settings.agent_threads_dir)
        self.qa_agent = qa_agent or QAAgent()
        self.audit = get_audit_trail()

    def run_case(
        self,
        case_id: str,
        question: str,
        *,
        top_k: int = 5,
        principal: Principal | None = None,
    ) -> Dict[str, Any]:
        actor = self._actor_from_principal(principal)
        thread = AgentThread(
            thread_id=str(uuid4()),
            case_id=case_id,
            question=question,
            created_at=_now(),
            updated_at=_now(),
        )
        self._audit_agents_event(
            action="agents.thread.created",
            outcome="accepted",
            subject={"thread_id": thread.thread_id, "case_id": case_id},
            metadata={"question_length": len(question), "top_k": top_k},
            actor=actor,
            correlation_id=thread.thread_id,
        )

        research_turn, retrieval_output = self._execute_research(question, top_k)
        thread.turns.append(research_turn)
        thread.final_answer = retrieval_output.get("answer", "")
        thread.citations = retrieval_output.get("citations", [])
        self._audit_turn(thread, research_turn, actor)

        forensics_turn, forensics_bundle = self._collect_forensics(thread.citations)
        thread.turns.append(forensics_turn)
        self._audit_turn(thread, forensics_turn, actor)

        telemetry_context = self._base_telemetry(retrieval_output, forensics_bundle, thread.turns)

        qa_turn = self._qa_scoring(question, retrieval_output, forensics_bundle, telemetry_context)
        thread.turns.append(qa_turn)
        thread.qa_scores = qa_turn.output.get("scores", {})
        thread.qa_notes = qa_turn.output.get("notes", [])
        self._audit_turn(thread, qa_turn, actor)

        thread.telemetry = self._finalise_telemetry(telemetry_context, thread.turns, qa_turn.output)
        thread.updated_at = _now()
        self._audit_agents_event(
            action="agents.thread.completed",
            outcome="success",
            subject={"thread_id": thread.thread_id, "case_id": case_id},
            metadata={
                "final_answer_length": len(thread.final_answer),
                "qa_average": qa_turn.output.get("average"),
                "turn_count": len(thread.turns),
            },
            actor=actor,
            correlation_id=thread.thread_id,
        )

        record = thread.to_record()
        self.memory_store.write(record)
        return record.to_json()

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        return self.memory_store.read(thread_id)

    def list_threads(self) -> List[str]:
        return self.memory_store.list_threads()

    def _execute_research(self, question: str, top_k: int) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _now()
        result = self.retrieval_service.query(question, page_size=top_k)
        output = result.to_dict() if isinstance(result, QueryResult) else result
        completed = _now()
        metrics = {
            "vector_hits": len(output.get("traces", {}).get("vector", [])),
            "graph_nodes": len(output.get("traces", {}).get("graph", {}).get("nodes", [])),
            "graph_edges": len(output.get("traces", {}).get("graph", {}).get("edges", [])),
            "citations": len(output.get("citations", [])),
        }
        privilege = output.get("traces", {}).get("privilege", {})
        metrics["privileged_docs"] = sum(
            1 for item in privilege.get("decisions", []) if item.get("label") == "privileged"
        )
        metrics["privilege_label"] = privilege.get("aggregate", {}).get("label", "unknown")
        turn = AgentTurn(
            role="research",
            action="retrieve_context",
            input={"question": question, "top_k": top_k},
            output=output,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )
        return turn, output

    def _collect_forensics(self, citations: List[Dict[str, Any]]) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _now()
        artifacts: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for citation in citations:
            doc_id = citation.get("docId")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            try:
                document = self.document_store.read_document(doc_id)
            except FileNotFoundError:
                document = {}
            doc_type = document.get("type")
            artifact_name = RetrievalService._artifact_name_for_type(doc_type)  # type: ignore[attr-defined]
            if artifact_name is None:
                continue
            if not self.forensics_service.report_exists(doc_id, artifact_name):
                continue
            try:
                payload = self.forensics_service.load_artifact(doc_id, artifact_name)
            except FileNotFoundError:
                continue
            artifacts.append(
                {
                    "document_id": doc_id,
                    "artifact": artifact_name,
                    "summary": payload.get("summary", ""),
                    "signals": payload.get("signals", []),
                    "schema_version": payload.get("schema_version", "unknown"),
                    "stages": payload.get("stages", []),
                }
            )
        completed = _now()
        bundle = {"artifacts": artifacts}
        metrics = {
            "artifacts": len(artifacts),
            "documents_considered": len(seen),
        }
        turn = AgentTurn(
            role="forensics",
            action="collect_artifacts",
            input={"citation_count": len(citations)},
            output=bundle,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )
        return turn, bundle

    def _qa_scoring(
        self,
        question: str,
        retrieval: Dict[str, Any],
        forensics_bundle: Dict[str, Any],
        telemetry_context: Dict[str, Any],
    ) -> AgentTurn:
        started = _now()
        scores, notes, average = self.qa_agent.evaluate(question, retrieval, forensics_bundle, telemetry_context)
        completed = _now()
        output = {"scores": scores, "notes": notes, "average": average}
        metrics = {
            "average": average,
            "min_score": min(scores.values()) if scores else None,
            "max_score": max(scores.values()) if scores else None,
        }
        telemetry_context.setdefault("notes", []).extend(notes)
        return AgentTurn(
            role="qa",
            action="score_rubric",
            input={"question": question},
            output=output,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )

    def _base_telemetry(
        self,
        retrieval: Dict[str, Any],
        forensics_bundle: Dict[str, Any],
        turns: List[AgentTurn],
    ) -> Dict[str, Any]:
        traces = retrieval.get("traces", {})
        graph = traces.get("graph", {})
        telemetry = {
            "vector_hits": len(traces.get("vector", [])),
            "graph_nodes": len(graph.get("nodes", [])),
            "graph_edges": len(graph.get("edges", [])),
            "forensics_artifacts": len(forensics_bundle.get("artifacts", [])),
            "forensics_signals": sum(len(item.get("signals", [])) for item in forensics_bundle.get("artifacts", [])),
            "turn_roles": [turn.role for turn in turns],
            "durations_ms": [round(turn.duration_ms(), 2) for turn in turns],
        }
        privilege = traces.get("privilege", {})
        telemetry["privileged_docs"] = sum(
            1 for item in privilege.get("decisions", []) if item.get("label") == "privileged"
        )
        telemetry["privilege_label"] = privilege.get("aggregate", {}).get("label", "unknown")
        telemetry["privilege_score"] = privilege.get("aggregate", {}).get("score", 0.0)
        telemetry["total_duration_ms"] = round(sum(telemetry["durations_ms"]), 2)
        telemetry["sequence_valid"] = telemetry["turn_roles"] == ["research", "forensics"]
        return telemetry

    def _finalise_telemetry(
        self,
        base: Dict[str, Any],
        turns: List[AgentTurn],
        qa_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        telemetry = dict(base)
        telemetry["turn_roles"] = [turn.role for turn in turns]
        telemetry["durations_ms"] = [round(turn.duration_ms(), 2) for turn in turns]
        telemetry["total_duration_ms"] = round(sum(telemetry["durations_ms"]), 2)
        telemetry["max_duration_ms"] = max(telemetry["durations_ms"], default=0.0)
        telemetry["sequence_valid"] = telemetry["turn_roles"] == ["research", "forensics", "qa"]
        telemetry["qa_average"] = qa_output.get("average")
        return telemetry

    def _system_actor(self) -> Dict[str, Any]:
        return {"id": "agents-orchestrator", "type": "system", "roles": ["System"]}

    def _actor_from_principal(self, principal: Principal | None) -> Dict[str, Any]:
        if principal is None:
            return self._system_actor()
        actor = {
            "id": principal.client_id,
            "subject": principal.subject,
            "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles),
            "scopes": sorted(principal.scopes),
            "case_admin": principal.case_admin,
            "token_roles": sorted(principal.token_roles),
            "certificate_roles": sorted(principal.certificate_roles),
        }
        fingerprint = principal.attributes.get("fingerprint") or principal.attributes.get("certificate_fingerprint")
        if fingerprint:
            actor["fingerprint"] = fingerprint
        return actor

    def _audit_agents_event(
        self,
        *,
        action: str,
        outcome: str,
        subject: Dict[str, Any],
        metadata: Dict[str, Any] | None,
        actor: Dict[str, Any],
        correlation_id: str,
        severity: str = "info",
    ) -> None:
        event = AuditEvent(
            category="agents",
            action=action,
            actor=actor,
            subject=subject,
            outcome=outcome,
            severity=severity,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._safe_audit(event)

    def _audit_turn(self, thread: AgentThread, turn: AgentTurn, actor: Dict[str, Any]) -> None:
        metadata = {
            "role": turn.role,
            "action": turn.action,
            "duration_ms": round(turn.duration_ms(), 2),
            "metrics": dict(turn.metrics),
        }
        subject = {"thread_id": thread.thread_id, "case_id": thread.case_id, "turn_role": turn.role}
        self._audit_agents_event(
            action=f"agents.turn.{turn.role}",
            outcome="success",
            subject=subject,
            metadata=metadata,
            actor=actor,
            correlation_id=thread.thread_id,
        )

    def _safe_audit(self, event: AuditEvent) -> None:
        try:
            self.audit.append(event)
        except Exception:  # pragma: no cover - guard rail for audit persistence
            logging.getLogger("backend.services.agents").exception(
                "Failed to append agents audit event",
                extra={"category": event.category, "action": event.action},
            )


_AGENTS_SERVICE: AgentsService | None = None


def get_agents_service() -> AgentsService:
    global _AGENTS_SERVICE  # noqa: PLW0603
    if _AGENTS_SERVICE is None:
        _AGENTS_SERVICE = AgentsService()
    return _AGENTS_SERVICE


def reset_agents_service() -> None:
    global _AGENTS_SERVICE  # noqa: PLW0603
    _AGENTS_SERVICE = None
