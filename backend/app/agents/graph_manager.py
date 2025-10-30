"""Graph manager agent orchestrating text-to-Cypher insights for case threads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, Protocol
from uuid import uuid4

from ..services.errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowSeverity
from ..services.graph import GraphExecutionResult, GraphService, get_graph_service
from ..storage.timeline_store import TimelineEvent, TimelineStore
from .context import AgentContext


class TextToCypherChain(Protocol):
    """Protocol describing a minimal text-to-Cypher generation chain."""

    def generate(self, prompt: str, *, context: Dict[str, Any] | None = None) -> str:
        ...


@dataclass(slots=True)
class GraphInsight:
    """Container capturing the outcome of a graph insight turn."""

    question: str
    cypher: str
    prompt: str
    execution: GraphExecutionResult
    generated_at: str
    timeline_event_id: str | None = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "cypher": self.cypher,
            "prompt": self.prompt,
            "generated_at": self.generated_at,
            "timeline_event_id": self.timeline_event_id,
            "execution": self.execution.to_dict(),
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "GraphInsight":
        execution_payload = payload.get("execution", {})
        if isinstance(execution_payload, dict):
            execution = GraphExecutionResult.from_dict(execution_payload)
        else:  # pragma: no cover - defensive fallback
            execution = GraphExecutionResult(
                question=str(payload.get("question", "")),
                cypher=str(payload.get("cypher", "")),
                prompt=str(payload.get("prompt", "")),
                records=[],
                summary={},
                documents=[],
                evidence_nodes=[],
            )
        generated_at_raw = payload.get("generated_at")
        generated_at = (
            str(generated_at_raw)
            if isinstance(generated_at_raw, str)
            else datetime.now(timezone.utc).isoformat()
        )
        timeline_event_id = payload.get("timeline_event_id")
        if timeline_event_id is not None:
            timeline_event_id = str(timeline_event_id)
        return cls(
            question=str(payload.get("question", "")),
            cypher=str(payload.get("cypher", "")),
            prompt=str(payload.get("prompt", "")),
            execution=execution,
            generated_at=generated_at,
            timeline_event_id=timeline_event_id,
        )


class HeuristicTextToCypherChain:
    """Rule-based fallback when an external LLM is not configured."""

    def generate(self, prompt: str, *, context: Dict[str, Any] | None = None) -> str:
        question = (context or {}).get("question", "")
        lowered = question.lower()
        if any(keyword in lowered for keyword in ["timeline", "chronology", "sequence"]):
            return "MATCH (n) RETURN n"
        if any(keyword in lowered for keyword in ["document", "evidence", "record"]):
            return "MATCH (n) RETURN n"
        return "MATCH (n) RETURN n"


class GraphManagerAgent:
    """High-level coordinator generating and executing graph insights for a case."""

    def __init__(
        self,
        *,
        graph_service: GraphService | None = None,
        timeline_store: TimelineStore | None = None,
        chain: TextToCypherChain | None = None,
    ) -> None:
        self.graph_service = graph_service or get_graph_service()
        self.timeline_store = timeline_store
        self.chain = chain or HeuristicTextToCypherChain()

    def ensure_insight(
        self,
        context: AgentContext,
        question: str | None = None,
        *,
        reuse_existing: bool = True,
    ) -> GraphInsight:
        if reuse_existing:
            existing = context.memory.state.get("insights", {}).get("graph")
            if isinstance(existing, dict) and existing.get("cypher"):
                try:
                    return GraphInsight.from_payload(dict(existing))
                except Exception:  # pragma: no cover - defensive hydration guard
                    pass
        return self._generate_insight(context, question or context.question)

    # -- internals -----------------------------------------------------------------
    def _generate_insight(self, context: AgentContext, question: str) -> GraphInsight:
        prompt = self.graph_service.build_text_to_cypher_prompt(question)
        llm_output = self.chain.generate(
            prompt,
            context={
                "case_id": context.case_id,
                "question": question,
                "actor": dict(context.actor),
            },
        )
        cypher = self._extract_cypher(llm_output)
        execution = self.graph_service.execute_agent_cypher(
            question,
            cypher,
            prompt=prompt,
        )
        generated_at = datetime.now(timezone.utc).isoformat()
        event_id = self._record_timeline(context, execution)
        insight = GraphInsight(
            question=question,
            cypher=execution.cypher,
            prompt=prompt,
            execution=execution,
            generated_at=generated_at,
            timeline_event_id=event_id,
        )
        context.memory.update("insights", {"graph": insight.to_payload()})
        note = (
            "Graph manager executed sandboxed Cypher to surface evidence-linked nodes"
        )
        context.memory.append_note(note)
        telemetry = context.telemetry.setdefault("graph", {})
        telemetry.update(
            {
                "documents": len(execution.documents),
                "last_run": generated_at,
                "event_id": event_id,
            }
        )
        if execution.warnings:
            telemetry.setdefault("warnings", []).extend(execution.warnings)
        return insight

    def _extract_cypher(self, text: str) -> str:
        content = text.strip()
        fenced = re.search(r"```(?:cypher)?\s*(.*?)```", content, re.IGNORECASE | re.DOTALL)
        if fenced:
            content = fenced.group(1)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_NO_OUTPUT",
                    message="Text-to-Cypher chain did not return any content",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                ),
                status_code=400,
            )
        for index, line in enumerate(lines):
            if line.lower().startswith("match "):
                candidate = " ".join(lines[index:])
                break
        else:
            candidate = " ".join(lines)
        candidate = candidate.strip()
        if not candidate.lower().startswith("match"):
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.GRAPH,
                    code="GRAPH_INVALID_OUTPUT",
                    message="Text-to-Cypher chain must return a MATCH statement",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"output": content[:200]},
                ),
                status_code=400,
            )
        return candidate.rstrip(";")

    def _record_timeline(
        self, context: AgentContext, execution: GraphExecutionResult
    ) -> str | None:
        if self.timeline_store is None:
            return None
        summary = execution.summary.get("insight") or execution.summary.get("text")
        if not summary:
            summary = (
                f"Graph query for case {context.case_id} returned {execution.summary.get('record_count', 0)} record(s)."
            )
        event = TimelineEvent(
            id=f"graph::{context.case_id}::{uuid4().hex}",
            ts=datetime.now(timezone.utc),
            title=f"Graph insight for {context.case_id}",
            summary=summary,
            citations=list(execution.documents),
            entity_highlights=self._entity_highlights(execution),
            relation_tags=[],
            confidence=None,
        )
        self.timeline_store.append([event])
        return event.id

    @staticmethod
    def _entity_highlights(execution: GraphExecutionResult) -> list[dict[str, str]]:
        highlights: list[dict[str, str]] = []
        for node in execution.evidence_nodes:
            node_type = str(node.get("type", ""))
            if node_type.lower() == "document":
                continue
            highlight = {
                "id": str(node.get("id", "")),
                "label": str(node.get("label") or node.get("type") or node.get("id", "")),
            }
            if highlight["id"]:
                highlights.append(highlight)
            if len(highlights) >= 5:
                break
        return highlights


__all__ = ["GraphManagerAgent", "GraphInsight", "TextToCypherChain"]
