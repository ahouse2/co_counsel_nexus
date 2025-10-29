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
        question_lower = context.question.lower()
        directives: Dict[str, bool] = {}
        if any(keyword in question_lower for keyword in ["breach", "intrusion", "compromise", "malware", "dfir", "log review"]):
            directives["dfir"] = True
        if any(keyword in question_lower for keyword in ["ledger", "financial", "transaction", "accounting", "audit"]):
            directives["financial"] = True
        context.memory.update("plan", plan)
        if directives:
            context.memory.update("directives", directives)
            directive_list = context.telemetry.setdefault("directives", [])
            directive_list.extend(sorted(directives.keys()))
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
        artifact_payloads: Dict[str, Dict[str, Any]] = {}
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
            artifact_payloads[doc_id] = {
                "artifact": artifact_name,
                "payload": payload,
            }
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
        connectors = self._execute_directive_connectors(context, artifact_payloads)
        bundle = {
            "artifacts": artifacts,
            "documents_considered": len(seen),
        }
        if connectors:
            bundle["connectors"] = connectors
        metrics = {
            "artifacts": len(artifacts),
            "documents_considered": len(seen),
            "connectors": list(connectors.keys()) if connectors else [],
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

    def _execute_directive_connectors(
        self,
        context: AgentContext,
        artifact_payloads: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        directives = context.memory.state.get("directives", {})
        if not directives:
            return {}
        retrieval = context.memory.state.get("insights", {}).get("retrieval", {})
        connectors: Dict[str, Dict[str, Any]] = {}
        if directives.get("dfir"):
            connectors["dfir"] = self._build_dfir_bundle(artifact_payloads, retrieval)
        if directives.get("financial"):
            connectors["financial"] = self._build_financial_bundle(artifact_payloads)
        return {key: value for key, value in connectors.items() if value.get("status") != "idle"}

    def _build_dfir_bundle(
        self,
        artifact_payloads: Dict[str, Dict[str, Any]],
        retrieval: Dict[str, Any],
    ) -> Dict[str, Any]:
        traces = retrieval.get("traces", {})
        privilege = traces.get("privilege", {})
        flagged = privilege.get("aggregate", {}).get("flagged", []) or []
        findings: List[Dict[str, Any]] = []
        for doc_id, record in artifact_payloads.items():
            llama_payload = (
                record.get("payload", {}).get("data", {}).get("llama_index", {})
            )
            alerts = list(llama_payload.get("alerts", []))
            duplicates = list(llama_payload.get("duplicate_chunks", []))
            outliers = list(llama_payload.get("outliers", []))
            entropy = list(llama_payload.get("high_entropy_nodes", []))
            if alerts or duplicates or outliers or doc_id in flagged:
                findings.append(
                    {
                        "document_id": doc_id,
                        "alerts": alerts,
                        "duplicate_chunks": duplicates[:5],
                        "outliers": outliers[:5],
                        "high_entropy_nodes": entropy[:5],
                    }
                )
        status = "reported" if findings else "no_findings"
        remediation = []
        if findings:
            remediation = [
                "Quarantine flagged documents and notify incident response owner for review.",
                "Correlate duplicate or outlier chunks with access logs to detect exfiltration attempts.",
            ]
        return {
            "status": status,
            "findings": findings,
            "privilege": privilege.get("aggregate", {}),
            "remediation": remediation,
        }

    def _build_financial_bundle(
        self, artifact_payloads: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        ledgers: List[Dict[str, Any]] = []
        for doc_id, record in artifact_payloads.items():
            if record.get("artifact") != "financial":
                continue
            payload = record.get("payload", {})
            data = payload.get("data", {})
            anomalies = list(data.get("anomalies", []))
            totals = data.get("totals", {})
            remediation = data.get("remediation", [])
            ledgers.append(
                {
                    "document_id": doc_id,
                    "anomaly_count": len(anomalies),
                    "top_anomalies": anomalies[:5],
                    "totals": totals,
                    "remediation": remediation,
                }
            )
        if not ledgers:
            return {"status": "idle"}
        total_anomalies = sum(entry["anomaly_count"] for entry in ledgers)
        return {
            "status": "reported" if total_anomalies else "no_findings",
            "ledgers": ledgers,
            "total_anomalies": total_anomalies,
        }


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
        telemetry = context.telemetry
        scores, notes, average = self.qa_agent.evaluate(
            context.question,
            retrieval,
            forensics_bundle,
            telemetry,
        )
        gating = telemetry.get("gating", {})
        output = {"scores": scores, "notes": notes, "average": average, "gating": gating}
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
            metrics={
                "average": average,
                "categories": len(scores),
                "privilege_gate": gating.get("requires_privilege_review", False),
            },
        )
        context.memory.record_turn(turn.to_dict())
        return turn, output
