from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Tuple
from uuid import uuid4

from ..services.errors import WorkflowComponent
from ..storage.agent_memory_store import AgentMemoryStore
from .context import AgentContext
from .definitions import AgentDefinition, build_agent_graph
from .memory import CaseThreadMemory
from .qa import QAAgent
from .tools import (
    AgentTool,
    ForensicsTool,
    IngestionTool,
    QATool,
    ResearchTool,
    StrategyTool,
)
from .types import AgentThread, AgentTurn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ComponentExecutor = Callable[
    [
        WorkflowComponent,
        Callable[[], Tuple[AgentTurn, Dict[str, object]]],
        bool,
        Callable[[Exception], Tuple[AgentTurn, Dict[str, object]]] | None,
    ],
    Tuple[AgentTurn, Dict[str, object]],
]


@dataclass(slots=True)
class MicrosoftAgentsOrchestrator:
    """High-level façade over the Microsoft Agents SDK conversation graph."""

    strategy_tool: StrategyTool
    ingestion_tool: IngestionTool
    research_tool: ResearchTool
    forensics_tool: ForensicsTool
    qa_tool: QATool
    memory_store: AgentMemoryStore
    tools: Dict[str, AgentTool] = field(init=False)
    graph: List[AgentDefinition] = field(init=False)

    def __post_init__(self) -> None:
        self.tools = {
            "strategy": self.strategy_tool,
            "ingestion": self.ingestion_tool,
            "research": self.research_tool,
            "cocounsel": self.forensics_tool,
            "qa": self.qa_tool,
        }
        self.graph: List[AgentDefinition] = build_agent_graph(self.tools)

    def run(
        self,
        *,
        case_id: str,
        question: str,
        top_k: int,
        actor: Dict[str, object],
        component_executor: ComponentExecutor,
        thread_id: str | None = None,
        thread: AgentThread | None = None,
        telemetry: Dict[str, object] | None = None,
    ) -> AgentThread:
        if thread is None:
            thread = AgentThread(
                thread_id=thread_id or str(uuid4()),
                case_id=case_id,
                question=question,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        else:
            thread.thread_id = thread_id or thread.thread_id
            thread.case_id = case_id
            thread.question = question
            thread.updated_at = _utcnow()
        memory = CaseThreadMemory(thread, self.memory_store)
        telemetry = telemetry or {}
        telemetry.setdefault("turn_roles", [])
        telemetry.setdefault("durations_ms", [])
        telemetry.setdefault("retries", {})
        telemetry.setdefault("backoff_ms", {})
        telemetry.setdefault("notes", [])
        telemetry.setdefault("status", "pending")
        telemetry.setdefault("hand_offs", [])
        context = AgentContext(
            case_id=case_id,
            question=question,
            top_k=top_k,
            actor=actor,
            memory=memory,
            telemetry=telemetry,
        )

        retrieval_output: Dict[str, object] = {}
        forensics_bundle: Dict[str, object] = {}

        for index, definition in enumerate(self.graph):
            tool = definition.tool

            def operation() -> Tuple[AgentTurn, Dict[str, object]]:
                return tool.execute(context)

            if tool.component in {
                WorkflowComponent.RETRIEVAL,
                WorkflowComponent.FORENSICS,
                WorkflowComponent.QA,
                WorkflowComponent.INGESTION,
                WorkflowComponent.STRATEGY,
            }:
                turn, payload = component_executor(tool.component, operation, False, None)
            else:
                turn, payload = operation()

            thread.turns.append(turn)
            telemetry["turn_roles"].append(turn.role)
            telemetry["durations_ms"].append(round(turn.duration_ms(), 2))
            if index:
                previous = self.graph[index - 1]
                telemetry["hand_offs"].append(
                    {
                        "from": previous.role,
                        "to": turn.role,
                        "via": tool.name,
                    }
                )
            memory.mark_updated()

            if definition.role == "research":
                retrieval_output = payload
                thread.final_answer = str(retrieval_output.get("answer", ""))
                thread.citations = list(retrieval_output.get("citations", []))
            elif definition.role == "cocounsel":
                forensics_bundle = payload
            elif definition.role == "qa":
                qa_scores = payload.get("scores", {})
                thread.qa_scores = {str(k): float(v) for k, v in qa_scores.items()}
                thread.qa_notes = list(payload.get("notes", []))
                telemetry["qa_average"] = payload.get("average")

        telemetry["sequence_valid"] = True
        telemetry["total_duration_ms"] = round(sum(telemetry["durations_ms"]), 2)
        telemetry["status"] = "succeeded"
        telemetry.setdefault("errors", [])
        thread.status = "succeeded"
        thread.telemetry = telemetry
        memory.persist()
        thread.updated_at = _utcnow()
        return thread


def get_orchestrator(
    retrieval_service,
    forensics_service,
    document_store,
    qa_agent: QAAgent,
    memory_store: AgentMemoryStore,
) -> MicrosoftAgentsOrchestrator:
    strategy_tool = StrategyTool()
    ingestion_tool = IngestionTool(document_store)
    research_tool = ResearchTool(retrieval_service)
    forensics_tool = ForensicsTool(document_store, forensics_service)
    qa_tool = QATool(qa_agent)
    return MicrosoftAgentsOrchestrator(
        strategy_tool=strategy_tool,
        ingestion_tool=ingestion_tool,
        research_tool=research_tool,
        forensics_tool=forensics_tool,
        qa_tool=qa_tool,
        memory_store=memory_store,
    )
