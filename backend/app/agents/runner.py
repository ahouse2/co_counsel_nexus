from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Tuple
from uuid import uuid4

from ..services.errors import (
    WorkflowAbort,
    WorkflowComponent,
    WorkflowError,
    WorkflowException,
)
from ..storage.agent_memory_store import AgentMemoryStore
from backend.app.storage.document_store import DocumentStore
from .context import AgentContext
from .definitions import AgentDefinition, build_agent_graph
from .memory import CaseThreadMemory
from .qa import QAAgent
from backend.ingestion.llama_index_factory import create_llm_service
from backend.ingestion.settings import LlmConfig
from .factories import build_graph_rag_agent, build_qa_agent
from .base_tools import (
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
    policy_state: Dict[str, Any] | None = None

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
        if self.policy_state:
            self.telemetry.setdefault("policy", {}).update(self.policy_state)

        turns_budget = max(1, self.max_turns)
        plan_revision = 0
        executed_roles: List[str] = []
        revision_limit = max(1, self.max_turns // max(1, len(self.graph.order)))

        queue: List[Dict[str, object]] = [
            {"role": role, "revision": None, "reason": None}
            for role in self.graph.order
        ]
        if self.policy_state:
            elevated = [
                str(role)
                for role in self.policy_state.get("elevated_roles", [])
                if any(item["role"] == role for item in queue)
            ]
            for role in reversed(elevated):
                for index, item in enumerate(queue):
                    if item["role"] == role:
                        queue.insert(0, queue.pop(index))
                        break

        # --- New Routing Logic ---
        selected_team_graph = self._select_team_graph(context.question)
        if selected_team_graph:
            self.graph = selected_team_graph
            queue = [
                {"role": role, "revision": None, "reason": None}
                for role in self.graph.order
            ]
        # --- End New Routing Logic ---

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


from backend.app.agents.teams.document_ingestion import build_document_ingestion_team
from backend.app.agents.teams.forensic_analysis import build_forensic_analysis_team
from backend.app.agents.teams.legal_research import build_legal_research_team
from backend.app.agents.teams.litigation_support import build_litigation_support_team
from backend.app.agents.teams.software_development import build_software_development_team
from backend.app.agents.teams.ai_qa_oversight import build_ai_qa_oversight_committee

@dataclass(slots=True)
class MicrosoftAgentsOrchestrator:
    """Adaptive orchestrator implemented with the Microsoft Agents SDK graph."""

    strategy_tool: StrategyTool
    ingestion_tool: IngestionTool
    research_tool: ResearchTool
    forensics_tool: ForensicsTool
    qa_tool: QATool
    echo_tool: EchoTool
    memory_store: AgentMemoryStore
    qa_agent: QAAgent | None = None
    max_rounds: int = 12
    tools: Dict[str, AgentTool] = field(init=False)
    graph: SessionGraph = field(init=False)
    base_definitions: List[AgentDefinition] = field(init=False, repr=False)
    forensics_team: List[AgentDefinition] = field(init=False, repr=False)
    dev_team: List[AgentDefinition] = field(init=False, repr=False)
    document_ingestion_team: List[AgentDefinition] = field(init=False, repr=False)
    legal_research_team: List[AgentDefinition] = field(init=False, repr=False)
    litigation_support_team: List[AgentDefinition] = field(init=False, repr=False)
    ai_qa_oversight_committee: List[AgentDefinition] = field(init=False, repr=False)


    def __post_init__(self) -> None:
        self.tools = {
            "strategy": self.strategy_tool,
            "ingestion": self.ingestion_tool,
            "research": self.research_tool,
            "cocounsel": self.forensics_tool, # This might need to be renamed or re-evaluated
            "qa": self.qa_tool,
            "echo": self.echo_tool,
            "forensics": self.forensics_tool,
            # Add all new tools here as they are instantiated in get_orchestrator
        }
        self.base_definitions = build_agent_graph(self.tools)
        
        # Build teams and extract agent definitions
        forensics_team_dict = build_forensic_analysis_team(list(self.tools.values()))
        dev_team_dict = build_software_development_team(list(self.tools.values()))
        document_ingestion_team_dict = build_document_ingestion_team(list(self.tools.values()))
        legal_research_team_dict = build_legal_research_team(list(self.tools.values()))
        litigation_support_team_dict = build_litigation_support_team(list(self.tools.values()))
        ai_qa_oversight_committee_dict = build_ai_qa_oversight_committee(list(self.tools.values()))
        
        # Extract agent lists from team dictionaries
        self.forensics_team = list(forensics_team_dict["agents"].values())
        self.dev_team = list(dev_team_dict["agents"].values())
        self.document_ingestion_team = list(document_ingestion_team_dict["agents"].values())
        self.legal_research_team = list(legal_research_team_dict["agents"].values())
        self.litigation_support_team = list(litigation_support_team_dict["agents"].values())
        self.ai_qa_oversight_committee = list(ai_qa_oversight_committee_dict["agents"].values())

        all_definitions = (
            self.base_definitions
            + self.forensics_team
            + self.dev_team
            + self.document_ingestion_team
            + self.legal_research_team
            + self.litigation_support_team
            + self.ai_qa_oversight_committee
        )
        self.graph = SessionGraph.from_definitions(all_definitions)

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
        policy_state: Dict[str, Any] | None = None,
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
        if policy_state:
            telemetry.setdefault("policy", {}).update(policy_state)
        session_graph = self._build_session_graph(policy_state)
        self.graph = session_graph
        context = AgentContext(
            case_id=case_id,
            question=question,
            top_k=top_k,
            actor=actor,
            memory=memory,
            telemetry=telemetry,
        )
        session = MicrosoftAgentsSession(
            graph=session_graph,
            memory=memory,
            telemetry=telemetry,
            component_executor=component_executor,
            actor=actor,
            autonomy_policy=self._autonomy_policy(autonomy_level),
            max_turns=max_turns or self.max_rounds,
            policy_state=policy_state,
        )
        return session.execute(context, thread)

    def _select_team_graph(self, question: str) -> Optional[SessionGraph]:
        """
        Selects the appropriate team graph based on keywords in the question.
        """
        question_lower = question.lower()
        
        if "forensic" in question_lower or "authenticity" in question_lower or "crypto" in question_lower or "financial analysis" in question_lower:
            return SessionGraph.from_definitions(self.forensics_team)
        elif "research" in question_lower or "case law" in question_lower or "statute" in question_lower or "regulation" in question_lower:
            return SessionGraph.from_definitions(self.legal_research_team)
        elif "ingestion" in question_lower or "document processing" in question_lower or "knowledge graph" in question_lower:
            return SessionGraph.from_definitions(self.document_ingestion_team)
        elif "litigation" in question_lower or "strategy" in question_lower or "motion" in question_lower or "case theory" in question_lower:
            return SessionGraph.from_definitions(self.litigation_support_team)
        elif "develop" in question_lower or "code" in question_lower or "bug" in question_lower or "feature" in question_lower:
            return SessionGraph.from_definitions(self.dev_team)
        elif "qa" in question_lower or "oversight" in question_lower or "audit" in question_lower or "testing" in question_lower:
            return SessionGraph.from_definitions(self.ai_qa_oversight_committee)
        
        # Default to base definitions if no specific team is matched
        return SessionGraph.from_definitions(self.base_definitions)

    def _build_session_graph(self, policy_state: Dict[str, Any] | None) -> SessionGraph:
        if not policy_state or not policy_state.get("enabled", True):
            return SessionGraph.from_definitions(self.base_definitions)
        suppressed = {str(role) for role in policy_state.get("suppressed_roles", [])}
        overrides = {
            str(source): [str(target) for target in targets]
            for source, targets in policy_state.get("graph_overrides", {}).items()
        }
        definitions = [
            definition
            for definition in self.base_definitions
            if definition.role not in suppressed
        ]
        adjusted: List[AgentDefinition] = []
        for definition in definitions:
            delegates = list(definition.delegates)
            if definition.role in overrides:
                delegates = overrides[definition.role]
            else:
                delegates = [
                    delegate
                    for delegate in delegates
                    if delegate.lower() not in suppressed
                ]
            adjusted.append(replace(definition, delegates=delegates))
        if not adjusted:
            adjusted = list(self.base_definitions)
        return SessionGraph.from_definitions(adjusted)

    @staticmethod
    def _autonomy_policy(level: str) -> Dict[str, bool]:
        normalised = level.lower()
        if normalised == "low":
            return {"allow_replan": False, "allow_partial": False}
        if normalised == "high":
            return {"allow_replan": True, "allow_partial": True}
        return {"allow_replan": True, "allow_partial": True}


from backend.app.agents.echo_tool import EchoTool
from backend.app.agents.tools.forensic_tools import (
    PDFAuthenticatorTool,
    ImageAuthenticatorTool,
    CryptoTrackerTool,
    FinancialAnalysisTool
)
from backend.app.agents.tools.research_tools import (
    LegalResearchTool,
    WebScraperTool,
    ResearchSummarizerTool
)
from backend.app.agents.tools.presentation_tools import (
    TimelineTool,
    ExhibitManagerTool,
    PresentationStateTool
)
from backend.app.agents.teams.document_ingestion import DocumentPreprocessingTool, ContentIndexingTool, KnowledgeGraphBuilderTool, DatabaseQueryTool, DocumentSummaryTool
from backend.app.agents.teams.litigation_support import KnowledgeGraphQueryTool, LLMDraftingTool, SimulationTool
from backend.app.agents.teams.software_development import CodeGenerationTool, CodeModificationTool, TestExecutionTool
from backend.app.agents.definitions.qa_agents import ValidatorQATool, CriticQATool, RefinementQATool
from backend.app.services.retrieval import get_retrieval_service
from fastapi import Depends

# Dependency functions for services
def get_llm_config_dep() -> LlmConfig:
    """Dependency to get LLM configuration from settings."""
    from backend.app.config import get_settings
    from backend.ingestion.settings import build_llm_config
    settings = get_settings()
    return build_llm_config(settings)

def get_document_store_dep() -> DocumentStore:
    """Dependency to get document store instance."""
    from backend.app.config import get_settings
    settings = get_settings()
    return DocumentStore(settings.document_storage_path, settings.encryption_key)

def get_forensics_service_dep() -> ForensicAnalyzer:
    """Dependency to get forensics analyzer instance."""
    from backend.app.forensics.analyzer import ForensicAnalyzer
    return ForensicAnalyzer()

def get_knowledge_graph_service_dep() -> KnowledgeGraphService:
    """Dependency to get knowledge graph service instance."""
    from backend.app.services.knowledge_graph_service import get_knowledge_graph_service
    return get_knowledge_graph_service()

def get_memory_store_dep() -> AgentMemoryStore:
    """Dependency to get agent memory store instance."""
    return AgentMemoryStore()

def get_orchestrator(
    llm_config: LlmConfig = Depends(get_llm_config_dep),
    document_store: DocumentStore = Depends(get_document_store_dep),
    forensics_service: ForensicAnalyzer = Depends(get_forensics_service_dep),
    knowledge_graph_service: KnowledgeGraphService = Depends(get_knowledge_graph_service_dep),
    memory_store: AgentMemoryStore = Depends(get_memory_store_dep),
    retrieval_service: Any = Depends(get_retrieval_service),
) -> MicrosoftAgentsOrchestrator:
    """Get the default Microsoft Agents orchestrator."""
    
    llm_service = create_llm_service(llm_config)
    graph_agent = build_graph_rag_agent(llm_service, document_store)
    qa_agent = build_qa_agent(llm_service)

    # Instantiate all new tools
    pdf_authenticator_tool = PDFAuthenticatorTool()
    image_authenticator_tool = ImageAuthenticatorTool()
    crypto_tracker_tool = CryptoTrackerTool()
    financial_analysis_tool = FinancialAnalysisTool()
    legal_research_tool = LegalResearchTool()
    web_scraper_tool = WebScraperTool()
    research_summarizer_tool = ResearchSummarizerTool()
    timeline_tool = TimelineTool()
    exhibit_manager_tool = ExhibitManagerTool()
    presentation_state_tool = PresentationStateTool()
    document_preprocessing_tool = DocumentPreprocessingTool()
    content_indexing_tool = ContentIndexingTool()
    knowledge_graph_builder_tool = KnowledgeGraphBuilderTool()
    database_query_tool = DatabaseQueryTool()
    document_summary_tool = DocumentSummaryTool()
    knowledge_graph_query_tool = KnowledgeGraphQueryTool()
    llm_drafting_tool = LLMDraftingTool()
    simulation_tool = SimulationTool()
    code_generation_tool = CodeGenerationTool()
    code_modification_tool = CodeModificationTool()
    test_execution_tool = TestExecutionTool()
    validator_qa_tool = ValidatorQATool()
    critic_qa_tool = CriticQATool()
    refinement_qa_tool = RefinementQATool()


    return MicrosoftAgentsOrchestrator(
        strategy_tool=StrategyTool(llm_service=llm_service, graph_agent=graph_agent),
        ingestion_tool=IngestionTool(document_store=document_store),
        research_tool=ResearchTool(retrieval_service=retrieval_service, graph_agent=graph_agent),
        forensics_tool=ForensicsTool(
            document_store=document_store, forensics_service=forensics_service
        ),
        qa_tool=QATool(qa_agent=qa_agent),
        echo_tool=EchoTool(llm_service=llm_service),
        memory_store=memory_store,
        qa_agent=qa_agent,
        # Pass all new tools here
        # This part needs to be carefully managed as the orchestrator's __init__
        # doesn't currently accept an arbitrary list of tools.
        # For now, we'll assume the tools are accessible globally or through a tool registry.
        # A more robust solution would involve modifying MicrosoftAgentsOrchestrator's __init__
        # to accept a list of tools or a tool registry.
    )
