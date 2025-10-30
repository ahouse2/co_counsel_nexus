from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Tuple
from uuid import uuid4

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
class SessionNode:
    definition: AgentDefinition
    next_roles: List[str]


@dataclass(slots=True)
class SessionGraph:
    """Directed conversation graph for Microsoft Agents sessions."""

    nodes: Dict[str, SessionNode]
    entry_role: str
    order: List[str]

    @classmethod
    def from_definitions(cls, definitions: Iterable[AgentDefinition]) -> "SessionGraph":
        definitions_list = list(definitions)
        if not definitions_list:
            raise ValueError("Agent graph requires at least one definition")
        name_to_role = {definition.name: definition.role for definition in definitions_list}
        nodes: Dict[str, SessionNode] = {}
        adjacency: Dict[str, List[str]] = {}
        for definition in definitions_list:
            downstream: List[str] = []
            for delegate in definition.delegates:
                role = name_to_role.get(delegate, delegate.lower())
                downstream.append(role)
            adjacency[definition.role] = downstream
            nodes[definition.role] = SessionNode(definition=definition, next_roles=downstream)
        entry = definitions_list[0].role
        order: List[str] = []
        visited = set()
        queue: List[str] = [entry]
        while queue:
            role = queue.pop(0)
            if role in visited:
                continue
            visited.add(role)
            order.append(role)
            queue.extend(adjacency.get(role, []))
        return cls(nodes=nodes, entry_role=entry, order=order)


@dataclass(slots=True)
class MicrosoftAgentsSession:
    """Session runner that executes the Microsoft Agents SDK graph."""

    graph: SessionGraph
    memory: CaseThreadMemory
    telemetry: Dict[str, object]
    component_executor: ComponentExecutor
    actor: Dict[str, object]
    autonomy_policy: Dict[str, bool]
    max_turns: int

    def execute(self, context: AgentContext, thread: AgentThread) -> AgentThread:
        # Seed the conversation transcript with the user brief.
        self.memory.append_conversation(
            {
                "role": "user",
                "name": self.actor.get("name", "Principal"),
                "content": context.question,
            }
        )
        self.memory.persist()
        self.telemetry.setdefault("conversation_id", thread.thread_id)
        self.telemetry.setdefault("delegations", [])
        self.telemetry.setdefault("branching", [])
        self.telemetry.setdefault("plan_revisions", 0)
        self.telemetry.setdefault("hand_offs", [])
        self.telemetry.setdefault("notes", [])

        turns_budget = max(1, self.max_turns)
        plan_revision = 0
        executed_roles: List[str] = []
        revision_limit = max(1, self.max_turns // max(1, len(self.graph.order)))

        queue: List[Dict[str, object]] = [
            {"role": role, "revision": None, "reason": None}
            for role in self.graph.order
        ]

        while queue and turns_budget > 0:
            item = queue.pop(0)
            role = str(item["role"])
            revision = item.get("revision")
            reason = item.get("reason")
            node = self.graph.nodes[role]

            turns_budget -= 1
            invocation = self._invoke(
                node,
                context,
                thread,
                revision=revision if isinstance(revision, int) else None,
                revision_reason=str(reason) if reason else None,
            )
            executed_roles.append(role)

            if invocation.metadata:
                self.telemetry["delegations"].append(
                    {
                        "from": node.definition.name,
                        "role": node.definition.role,
                        "metadata": invocation.metadata,
                    }
                )

            if role == "strategy":
                context.memory.plan.update(invocation.payload)
            elif role == "research":
                metadata = invocation.metadata or {}
                citations = int(metadata.get("citations", 0))
                status = metadata.get("status")
                if status == "failed":
                    policy = context.telemetry.get("autonomy_level", "balanced")
                    reason_code = metadata.get("error_code", "retrieval_failure")
                    self.telemetry["branching"].append(
                        {
                            "reason": reason_code,
                            "stage": role,
                            "policy": policy,
                            "status": "partial"
                            if self.autonomy_policy.get("allow_partial", False)
                            else "aborted",
                        }
                    )
                    note = (
                        "Research turn encountered "
                        f"{reason_code.replace('_', ' ').title()}. Planner triggered revision run."
                    )
                    if (
                        self.autonomy_policy.get("allow_replan", True)
                        and plan_revision < revision_limit
                        and turns_budget > 0
                    ):
                        plan_revision += 1
                        self.telemetry["plan_revisions"] = plan_revision
                        context.memory.append_note(note)
                        self.telemetry["notes"].append(note)
                        queue.insert(0, {"role": "research", "revision": None, "reason": None})
                        queue.insert(
                            0,
                            {
                                "role": "strategy",
                                "revision": plan_revision,
                                "reason": reason_code,
                            },
                        )
                        continue
                    degraded_note = (
                        "Research agent emitted partial findings after failure; proceeding with remaining agents."
                    )
                    context.memory.append_note(degraded_note)
                    self.telemetry["notes"].append(degraded_note)
                elif (
                    citations == 0
                    and self.autonomy_policy.get("allow_replan", True)
                    and plan_revision < revision_limit
                    and turns_budget > 0
                ):
                    plan_revision += 1
                    self.telemetry["plan_revisions"] = plan_revision
                    self.telemetry["branching"].append(
                        {
                            "reason": metadata.get("error_code", "missing_citations"),
                            "stage": role,
                            "policy": context.telemetry.get("autonomy_level", "balanced"),
                        }
                    )
                    note = "Research turn returned zero citations. Planner triggered revision run."
                    context.memory.append_note(note)
                    self.telemetry["notes"].append(note)
                    # Insert a planner revision followed by another research turn.
                    queue.insert(
                        0,
                        {
                            "role": "research",
                            "revision": None,
                            "reason": None,
                        },
                    )
                    queue.insert(
                        0,
                        {
                            "role": "strategy",
                            "revision": plan_revision,
                            "reason": "missing_citations",
                        },
                    )
                    continue
                thread.final_answer = str(invocation.payload.get("answer", thread.final_answer))
                thread.citations = list(invocation.payload.get("citations", thread.citations))
            elif role == "cocounsel":
                context.memory.update("artifacts", invocation.payload)
            elif role == "qa":
                qa_payload = invocation.payload
                if qa_payload.get("scores"):
                    thread.qa_scores = {str(k): float(v) for k, v in qa_payload["scores"].items()}
                if qa_payload.get("notes"):
                    thread.qa_notes = list(qa_payload.get("notes", []))
                if qa_payload.get("gating", {}).get("requires_privilege_review"):
                    thread.status = "needs_privilege_review"
                    self.telemetry["status"] = "needs_privilege_review"
                average = invocation.metadata.get("qa_average") if invocation.metadata else None
                if average is not None:
                    self.telemetry["qa_average"] = average

        if not thread.status or thread.status == "pending":
            if thread.errors:
                thread.status = "degraded"
            else:
                thread.status = "succeeded"
        self.telemetry["status"] = thread.status
        self.telemetry["sequence_valid"] = True
        self.telemetry["turn_roles"] = executed_roles
        durations = [round(turn.duration_ms(), 2) for turn in thread.turns]
        self.telemetry["durations_ms"] = durations
        self.telemetry["total_duration_ms"] = round(sum(durations), 2)
        thread.telemetry = dict(self.telemetry)
        thread.memory = self.memory.snapshot()
        thread.updated_at = _utcnow()
        return thread

    def _invoke(
        self,
        node: SessionNode,
        context: AgentContext,
        thread: AgentThread,
        *,
        revision: int | None,
        revision_reason: str | None = None,
    ) -> ToolInvocation:
        invocation: ToolInvocation | None = None
        partial_invocation: ToolInvocation | None = None

        def operation() -> Tuple[AgentTurn, Dict[str, object]]:
            nonlocal invocation
            invocation = node.definition.tool.invoke(context)
            turn = invocation.turn
            if revision:
                turn.annotations.setdefault("plan_revision", revision)
                if revision_reason:
                    turn.annotations.setdefault("revision_reason", revision_reason)
            return turn, invocation.payload

        allow_partial = (
            self.autonomy_policy.get("allow_partial", False)
            and node.definition.role in {"research", "cocounsel"}
        )

        def partial_factory(error: WorkflowError) -> Tuple[AgentTurn, Dict[str, object]]:
            nonlocal partial_invocation
            partial_invocation = self._handle_failure(node.definition.tool, context, thread, error)
            return partial_invocation.turn, partial_invocation.payload

        abort_exc: WorkflowAbort | None = None
        try:
            turn, _ = self.component_executor(
                node.definition.tool.component,
                operation,
                allow_partial,
                partial_factory if allow_partial else None,
            )
        except WorkflowAbort as exc:
            abort_exc = exc
            invocation = self._handle_failure(node.definition.tool, context, thread, exc.error)
        except WorkflowException as exc:
            invocation = self._handle_failure(node.definition.tool, context, thread, exc.error)
        if invocation is None:
            invocation = partial_invocation
        if invocation is None:
            raise RuntimeError(f"Tool invocation for role '{node.definition.role}' did not produce a result")
        invocation.turn.annotations.setdefault("tool_name", node.definition.tool.name)
        self._register_turn(thread, invocation.turn)
        self.memory.append_conversation(
            {
                "role": "agent",
                "name": node.definition.name,
                "content": invocation.message,
                "metadata": invocation.metadata,
            }
        )
        context.telemetry.setdefault("notes", [])
        self.memory.mark_updated()
        if abort_exc is not None:
            raise abort_exc
        return invocation

    def _register_turn(self, thread: AgentThread, turn: AgentTurn) -> None:
        thread.turns.append(turn)
        if len(thread.turns) > 1:
            previous = thread.turns[-2]
            self.telemetry.setdefault("hand_offs", []).append(
                {
                    "from": previous.role,
                    "to": turn.role,
                    "via": turn.annotations.get("tool_name", turn.action),
                }
            )

    def _handle_failure(
        self,
        tool: AgentTool,
        context: AgentContext,
        thread: AgentThread,
        error: WorkflowError,
    ) -> ToolInvocation:
        started = _utcnow()
        completed = _utcnow()
        role = tool.component.value
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
                "tool_name": tool.name,
            },
        )
        context.telemetry.setdefault("errors", []).append(error.to_dict())
        if error not in thread.errors:
            thread.errors.append(error)
        context.memory.record_turn(turn.to_dict())
        return ToolInvocation(
            turn=turn,
            payload=payload,
            message=f"{role.capitalize()} encountered {error.code}: {error.message}",
            metadata={
                "status": "failed",
                "error_code": error.code,
                "retryable": error.retryable,
                "error": error.to_dict(),
            },
        )


@dataclass(slots=True)
class MicrosoftAgentsOrchestrator:
    """Adaptive orchestrator implemented with the Microsoft Agents SDK graph."""

    strategy_tool: StrategyTool
    ingestion_tool: IngestionTool
    research_tool: ResearchTool
    forensics_tool: ForensicsTool
    qa_tool: QATool
    memory_store: AgentMemoryStore
    qa_agent: QAAgent | None = None
    max_rounds: int = 12
    tools: Dict[str, AgentTool] = field(init=False)
    graph: SessionGraph = field(init=False)

    def __post_init__(self) -> None:
        self.tools = {
            "strategy": self.strategy_tool,
            "ingestion": self.ingestion_tool,
            "research": self.research_tool,
            "cocounsel": self.forensics_tool,
            "qa": self.qa_tool,
        }
        definitions = build_agent_graph(self.tools)
        self.graph = SessionGraph.from_definitions(definitions)

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
        memory = CaseThreadMemory(thread, self.memory_store, state=dict(thread.memory))
        telemetry = telemetry or {}
        telemetry.setdefault("autonomy_level", autonomy_level)
        context = AgentContext(
            case_id=case_id,
            question=question,
            top_k=top_k,
            actor=actor,
            memory=memory,
            telemetry=telemetry,
        )
        session = MicrosoftAgentsSession(
            graph=self.graph,
            memory=memory,
            telemetry=telemetry,
            component_executor=component_executor,
            actor=actor,
            autonomy_policy=self._autonomy_policy(autonomy_level),
            max_turns=max_turns or self.max_rounds,
        )
        return session.execute(context, thread)

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
    graph_agent: "GraphManagerAgent",
) -> MicrosoftAgentsOrchestrator:
    strategy_tool = StrategyTool(graph_agent)
    ingestion_tool = IngestionTool(document_store)
    research_tool = ResearchTool(retrieval_service, graph_agent)
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
