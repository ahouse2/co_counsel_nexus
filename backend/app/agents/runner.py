from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Tuple
from uuid import uuid4

from autogen import ConversableAgent, GroupChat

from ..services.errors import (
    WorkflowAbort,
    WorkflowComponent,
    WorkflowError,
    WorkflowException,
)
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
    ToolInvocation,
)
from .types import AgentThread, AgentTurn


ComponentExecutor = Callable[
    [
        WorkflowComponent,
        Callable[[], Tuple[AgentTurn, Dict[str, object]]],
        bool,
        Callable[[WorkflowError], Tuple[AgentTurn, Dict[str, object]]] | None,
    ],
    Tuple[AgentTurn, Dict[str, object]],
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PlannerAgent(ConversableAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Planner",
            llm_config=None,
            system_message=(
                "Microsoft Agents planner responsible for translating the case brief into"
                " a structured execution plan and tracking revisions."
            ),
            description="Planner agent seeded from Microsoft Agents SDK",
        )


@dataclass(slots=True)
class WorkerAgent(ConversableAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Worker",
            llm_config=None,
            system_message=(
                "Execution specialist coordinating retrieval, forensics and evidence synthesis"
                " on behalf of the planner."
            ),
            description="Worker agent orchestrating tool delegation",
        )


@dataclass(slots=True)
class CriticAgent(ConversableAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Critic",
            llm_config=None,
            system_message=(
                "Quality critic validating worker output, triggering re-plans and ensuring"
                " QA rubric coverage."
            ),
            description="Critic agent evaluating intermediate outputs",
        )


@dataclass(slots=True)
class AdaptiveAgentsOrchestrator:
    """Adaptive Microsoft Agents orchestrator backed by the official SDK."""

    strategy_tool: StrategyTool
    ingestion_tool: IngestionTool
    research_tool: ResearchTool
    forensics_tool: ForensicsTool
    qa_tool: QATool
    memory_store: AgentMemoryStore
    max_rounds: int = 12
    tools: Dict[str, AgentTool] = field(init=False)
    graph: List[AgentDefinition] = field(init=False)
    planner: PlannerAgent = field(init=False)
    worker: WorkerAgent = field(init=False)
    critic: CriticAgent = field(init=False)
    component_roles: Dict[WorkflowComponent, str] = field(init=False)

    def __post_init__(self) -> None:
        self.tools = {
            "strategy": self.strategy_tool,
            "ingestion": self.ingestion_tool,
            "research": self.research_tool,
            "cocounsel": self.forensics_tool,
            "qa": self.qa_tool,
        }
        self.graph = build_agent_graph(self.tools)
        self.planner = PlannerAgent()
        self.worker = WorkerAgent()
        self.critic = CriticAgent()
        self.component_roles = {
            WorkflowComponent.STRATEGY: "strategy",
            WorkflowComponent.INGESTION: "ingestion",
            WorkflowComponent.RETRIEVAL: "research",
            WorkflowComponent.FORENSICS: "cocounsel",
            WorkflowComponent.QA: "qa",
        }

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
        autonomy_level: str = "balanced",
        max_turns: int | None = None,
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
        telemetry.setdefault("delegations", [])
        telemetry.setdefault("branching", [])
        telemetry.setdefault("plan_revisions", 0)
        telemetry.setdefault("conversation_id", thread.thread_id)
        context = AgentContext(
            case_id=case_id,
            question=question,
            top_k=top_k,
            actor=actor,
            memory=memory,
            telemetry=telemetry,
        )

        planner, worker, critic = self.planner, self.worker, self.critic
        max_rounds = max_turns or self.max_rounds
        group_chat = GroupChat(
            agents=[planner, worker, critic],
            messages=[],
            speaker_selection_method="manual",
            max_round=max_rounds,
        )
        self._append_message(
            group_chat,
            {
                "role": "user",
                "name": actor.get("name", "Principal"),
                "content": question,
            },
            memory,
        )

        plan_revision = 0
        worker_tasks: List[str] = ["ingestion", "research", "cocounsel"]
        autonomy = self._autonomy_policy(autonomy_level)
        self._run_planner(plan_revision, context, component_executor, planner, group_chat, memory, telemetry, thread)

        run_budget = max_rounds - 1
        while worker_tasks and run_budget > 0:
            run_budget -= 1
            task = worker_tasks.pop(0)
            invocation = self._invoke_tool(
                self.tools[task],
                context,
                component_executor,
                worker,
                group_chat,
                memory,
                telemetry,
                thread,
            )
            if invocation.metadata:
                telemetry["delegations"].append(
                    {
                        "from": worker.name,
                        "role": invocation.turn.role,
                        "metadata": invocation.metadata,
                    }
                )
            if invocation.metadata.get("status") == "failed":
                telemetry["branching"].append(
                    {
                        "reason": invocation.metadata.get("error_code", "unknown"),
                        "stage": task,
                        "policy": autonomy_level,
                    }
                )
                if task != "ingestion" and autonomy["allow_replan"]:
                    plan_revision += 1
                    telemetry["plan_revisions"] = plan_revision
                    self._append_message(
                        group_chat,
                        {
                            "role": "assistant",
                            "name": critic.name,
                            "content": (
                                "Critic observed a failure in the worker pipeline and is requesting"
                                " a plan refresh before continuing."
                            ),
                        },
                        memory,
                    )
                    self._run_planner(
                        plan_revision,
                        context,
                        component_executor,
                        planner,
                        group_chat,
                        memory,
                        telemetry,
                        thread,
                        revision_reason=invocation.metadata.get("error_code", "unknown"),
                    )
                    worker_tasks = ["research", "cocounsel"]
                    continue
                if not autonomy["allow_partial"]:
                    error_obj = invocation.metadata.get("error")
                    if isinstance(error_obj, WorkflowError):
                        raise WorkflowAbort(error_obj)
                    raise WorkflowAbort(
                        WorkflowError(
                            component=self.tools[task].component,
                            code=f"{self.tools[task].component.value.upper()}_FAILED",
                            message=f"{self.tools[task].name} failed and autonomy policy forbids partial progression.",
                        )
                    )
                telemetry["status"] = "degraded"
                thread.status = "degraded"
                continue
            if task == "research":
                citations = invocation.metadata.get("citations", 0)
                if citations == 0 and autonomy["allow_replan"]:
                    plan_revision += 1
                    telemetry["plan_revisions"] = plan_revision
                    telemetry["branching"].append(
                        {
                            "reason": "missing_citations",
                            "stage": "research",
                            "policy": autonomy_level,
                        }
                    )
                    self._append_message(
                        group_chat,
                        {
                            "role": "assistant",
                            "name": critic.name,
                            "content": (
                                "Critic flagged retrieval with zero citations and requested a refined"
                                " focus from the planner."
                            ),
                        },
                        memory,
                    )
                    context.memory.append_note("Critic requested planner revision due to zero citations.")
                    self._run_planner(
                        plan_revision,
                        context,
                        component_executor,
                        planner,
                        group_chat,
                        memory,
                        telemetry,
                        thread,
                        revision_reason="missing_citations",
                    )
                    worker_tasks = ["research", "cocounsel"]
            if task == "research":
                retrieval = invocation.payload
                thread.final_answer = str(retrieval.get("answer", ""))
                thread.citations = list(retrieval.get("citations", []))

        self._append_message(
            group_chat,
            {
                "role": "assistant",
                "name": critic.name,
                "content": "Critic reviewing aggregated evidence and triggering QA rubric run.",
            },
            memory,
        )
        qa_invocation = self._invoke_tool(
            self.qa_tool,
            context,
            component_executor,
            critic,
            group_chat,
            memory,
            telemetry,
            thread,
        )
        qa_payload = qa_invocation.payload
        if qa_invocation.metadata.get("qa_average") is not None:
            telemetry["qa_average"] = qa_invocation.metadata["qa_average"]
        if qa_payload.get("scores"):
            thread.qa_scores = {str(k): float(v) for k, v in qa_payload["scores"].items()}
        if qa_payload.get("notes"):
            thread.qa_notes = list(qa_payload.get("notes", []))
        if qa_payload.get("gating", {}).get("requires_privilege_review"):
            telemetry["status"] = "needs_privilege_review"
            thread.status = "needs_privilege_review"
        else:
            telemetry.setdefault("status", "succeeded")
            thread.status = telemetry["status"]

        telemetry["sequence_valid"] = True
        telemetry["total_duration_ms"] = round(sum(telemetry.get("durations_ms", [])), 2)
        thread.telemetry = telemetry
        memory.persist()
        thread.updated_at = _utcnow()
        return thread

    def _run_planner(
        self,
        revision: int,
        context: AgentContext,
        executor: ComponentExecutor,
        planner: PlannerAgent,
        chat: GroupChat,
        memory: CaseThreadMemory,
        telemetry: Dict[str, object],
        thread: AgentThread,
        *,
        revision_reason: str | None = None,
    ) -> None:
        invocation = self._invoke_tool(
            self.strategy_tool,
            context,
            executor,
            planner,
            chat,
            memory,
            telemetry,
            thread,
        )
        if revision:
            invocation.turn.annotations.setdefault("plan_revision", revision)
            invocation.turn.annotations.setdefault("revision_reason", revision_reason)
            telemetry.setdefault("notes", []).append(
                f"Plan revision {revision} triggered due to {revision_reason or 'worker request'}."
            )
        memory.state.setdefault("plan", {}).update(invocation.payload)

    def _invoke_tool(
        self,
        tool: AgentTool,
        context: AgentContext,
        executor: ComponentExecutor,
        agent: ConversableAgent,
        chat: GroupChat,
        memory: CaseThreadMemory,
        telemetry: Dict[str, object],
        thread: AgentThread,
    ) -> ToolInvocation:
        invocation: ToolInvocation | None = None

        def operation() -> Tuple[AgentTurn, Dict[str, object]]:
            nonlocal invocation
            invocation = tool.invoke(context)
            return invocation.turn, invocation.payload

        try:
            executor(tool.component, operation, False, None)
        except WorkflowAbort:
            raise
        except WorkflowException as exc:
            invocation = self._handle_failure(tool, context, exc.error)
        if invocation is None:
            raise RuntimeError("Tool invocation did not produce a result")
        self._register_turn(thread, invocation.turn, telemetry)
        self._append_message(
            chat,
            {
                "role": "assistant",
                "name": agent.name,
                "content": invocation.message,
                "metadata": invocation.metadata,
            },
            memory,
        )
        context.memory.mark_updated()
        return invocation

    def _register_turn(
        self,
        thread: AgentThread,
        turn: AgentTurn,
        telemetry: Dict[str, object],
    ) -> None:
        thread.turns.append(turn)
        telemetry["turn_roles"].append(turn.role)
        telemetry["durations_ms"].append(round(turn.duration_ms(), 2))
        if len(thread.turns) > 1:
            previous = thread.turns[-2]
            telemetry["hand_offs"].append(
                {
                    "from": previous.role,
                    "to": turn.role,
                    "via": turn.action,
                }
            )

    def _handle_failure(
        self,
        tool: AgentTool,
        context: AgentContext,
        error: WorkflowError,
    ) -> ToolInvocation:
        started = _utcnow()
        completed = _utcnow()
        role = self.component_roles.get(tool.component, tool.component.value)
        payload = {
            "status": "failed",
            "error": error.to_dict(),
        }
        turn = AgentTurn(
            role=role,
            action=f"{tool.name}_failed",
            input={"case_id": context.case_id, "question": context.question},
            output=payload,
            started_at=started,
            completed_at=completed,
            metrics={"attempt": getattr(error, "attempt", 1)},
            annotations={
                "status": "failed",
                "error_code": error.code,
                "retryable": error.retryable,
            },
        )
        context.telemetry.setdefault("errors", []).append(error.to_dict())
        context.memory.record_turn(turn.to_dict())
        return ToolInvocation(
            turn=turn,
            payload=payload,
            message=f"{role.capitalize()} encountered {error.code}: {error.message}",
            metadata={
                "status": "failed",
                "error_code": error.code,
                "retryable": error.retryable,
                "error": error,
            },
        )

    def _append_message(
        self,
        chat: GroupChat,
        message: Dict[str, object],
        memory: CaseThreadMemory,
    ) -> None:
        chat.messages.append(message)
        memory.append_conversation(message)

    @staticmethod
    def _autonomy_policy(level: str) -> Dict[str, bool]:
        normalised = level.lower()
        if normalised == "low":
            return {"allow_replan": False, "allow_partial": False}
        if normalised == "high":
            return {"allow_replan": True, "allow_partial": True}
        return {"allow_replan": True, "allow_partial": True}


def get_orchestrator(
    retrieval_service,
    forensics_service,
    document_store,
    qa_agent: QAAgent,
    memory_store: AgentMemoryStore,
) -> AdaptiveAgentsOrchestrator:
    strategy_tool = StrategyTool()
    ingestion_tool = IngestionTool(document_store)
    research_tool = ResearchTool(retrieval_service)
    forensics_tool = ForensicsTool(document_store, forensics_service)
    qa_tool = QATool(qa_agent)
    return AdaptiveAgentsOrchestrator(
        strategy_tool=strategy_tool,
        ingestion_tool=ingestion_tool,
        research_tool=research_tool,
        forensics_tool=forensics_tool,
        qa_tool=qa_tool,
        memory_store=memory_store,
    )
