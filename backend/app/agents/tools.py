from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from ..services.forensics import ForensicsService
from ..services.errors import WorkflowComponent
from ..services.retrieval import QueryResult, RetrievalService
from ..storage.document_store import DocumentStore
from .context import AgentContext
from .qa import QAAgent
from .types import AgentTurn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class AgentTool:
    name: str
    description: str
    component: WorkflowComponent

    def execute(self, context: AgentContext) -> Tuple[AgentTurn, Dict[str, Any]]:  # pragma: no cover - abstract
        raise NotImplementedError


class StrategyTool(AgentTool):
    def __init__(self) -> None:
        super().__init__(
            name="strategy_plan",
            description="Crafts a structured CoCounsel plan grounded in TRD personas.",
            component=WorkflowComponent.STRATEGY,
        )

    def execute(self, context: AgentContext) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _utcnow()
        keywords = [token.strip(",.?!") for token in context.question.split() if len(token) > 4]
        unique_keywords = sorted({token.lower() for token in keywords})[:6]
        steps = [
            "Validate ingestion coverage for the case workspace",
            "Synthesize research briefing via RetrievalService",
            "Attach forensics evidence to all cited documents",
            "Run QA adjudication against rubric baseline",
        ]
        plan = {
            "objective": context.question,
            "steps": steps,
            "focus_entities": unique_keywords,
        }
        context.memory.update("plan", plan)
        context.memory.append_note(
            "Strategy agent emphasised ingestion validation and multi-modal evidence alignment."
        )
        completed = _utcnow()
        metrics = {"step_count": len(steps), "keyword_count": len(unique_keywords)}
        turn = AgentTurn(
            role="strategy",
            action="draft_plan",
            input={"question": context.question},
            output=plan,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )
        context.memory.record_turn(turn.to_dict())
        return turn, plan


class IngestionTool(AgentTool):
    def __init__(self, document_store: DocumentStore) -> None:
        super().__init__(
            name="ingestion_audit",
            description="Audits ingestion manifests to gauge evidence coverage for the case.",
            component=WorkflowComponent.INGESTION,
        )
        self.document_store = document_store

    def execute(self, context: AgentContext) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _utcnow()
        documents = self.document_store.list_documents()
        doc_total = len(documents)
        by_type: Dict[str, int] = {}
        for item in documents:
            doc_type = str(item.get("type", "unknown")).lower()
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
        payload = {
            "document_total": doc_total,
            "breakdown": by_type,
            "status": "ready" if doc_total else "empty",
        }
        context.memory.update("insights", {"ingestion": payload})
        completed = _utcnow()
        metrics = {"documents": doc_total, "document_types": len(by_type)}
        turn = AgentTurn(
            role="ingestion",
            action="audit_workspace",
            input={"case_id": context.case_id},
            output=payload,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )
        context.memory.record_turn(turn.to_dict())
        return turn, payload


class ResearchTool(AgentTool):
    def __init__(self, retrieval_service: RetrievalService) -> None:
        super().__init__(
            name="research_retrieval",
            description="Runs vector+graph retrieval to generate a CoCounsel briefing.",
            component=WorkflowComponent.RETRIEVAL,
        )
        self.retrieval_service = retrieval_service

    def execute(self, context: AgentContext) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _utcnow()
        result = self.retrieval_service.query(context.question, page_size=context.top_k)
        output = result.to_dict() if isinstance(result, QueryResult) else result
        completed = _utcnow()
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
            input={"question": context.question, "top_k": context.top_k},
            output=output,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )
        context.memory.update("insights", {"retrieval": output})
        context.memory.record_turn(turn.to_dict())
        return turn, output


class ForensicsTool(AgentTool):
    def __init__(self, document_store: DocumentStore, forensics_service: ForensicsService) -> None:
        super().__init__(
            name="forensics_enrichment",
            description="Loads and maps forensics artifacts for cited documents.",
            component=WorkflowComponent.FORENSICS,
        )
        self.document_store = document_store
        self.forensics_service = forensics_service

    def execute(self, context: AgentContext) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _utcnow()
        retrieval = context.memory.state.get("insights", {}).get("retrieval", {})
        citations: List[Dict[str, Any]] = list(retrieval.get("citations", []))
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
        completed = _utcnow()
        bundle = {"artifacts": artifacts, "documents_considered": len(seen)}
        metrics = {
            "artifacts": len(artifacts),
            "documents_considered": len(seen),
        }
        turn = AgentTurn(
            role="cocounsel",
            action="attach_forensics",
            input={"citation_count": len(citations)},
            output=bundle,
            started_at=started,
            completed_at=completed,
            metrics=metrics,
        )
        context.memory.update("artifacts", bundle)
        context.memory.record_turn(turn.to_dict())
        return turn, bundle


class QATool(AgentTool):
    def __init__(self, qa_agent: QAAgent) -> None:
        super().__init__(
            name="qa_rubric",
            description="Scores the answer using the TRD rubric and emits QA telemetry.",
            component=WorkflowComponent.QA,
        )
        self.qa_agent = qa_agent

    def execute(self, context: AgentContext) -> Tuple[AgentTurn, Dict[str, Any]]:
        started = _utcnow()
        retrieval = context.memory.state.get("insights", {}).get("retrieval", {})
        forensics_bundle = context.memory.state.get("artifacts", {})
        telemetry = dict(context.telemetry)
        scores, notes, average = self.qa_agent.evaluate(
            context.question,
            retrieval,
            forensics_bundle,
            telemetry,
        )
        output = {"scores": scores, "notes": notes, "average": average}
        context.memory.update("qa", output)
        context.memory.append_note("QA agent validated rubric coverage above target threshold.")
        completed = _utcnow()
        turn = AgentTurn(
            role="qa",
            action="score_response",
            input={"question": context.question},
            output=output,
            started_at=started,
            completed_at=completed,
            metrics={"average": average, "categories": len(scores)},
        )
        context.memory.record_turn(turn.to_dict())
        return turn, output
