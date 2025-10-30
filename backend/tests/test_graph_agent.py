import pytest
from datetime import datetime, timezone

from backend.app import config
from backend.app.agents.context import AgentContext
from backend.app.agents.graph_manager import GraphManagerAgent
from backend.app.agents.memory import CaseThreadMemory
from backend.app.agents.types import AgentThread
from backend.app.services import graph as graph_module
from backend.app.services.errors import WorkflowAbort
from backend.app.storage.agent_memory_store import AgentMemoryStore
from backend.app.storage.timeline_store import TimelineStore


class _MockChain:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, dict | None]] = []

    def generate(self, prompt: str, *, context: dict | None = None) -> str:
        self.calls.append((prompt, context or {}))
        return self.response


@pytest.fixture()
def memory_graph(monkeypatch: pytest.MonkeyPatch) -> graph_module.GraphService:
    monkeypatch.setenv("NEO4J_URI", "memory://")
    config.reset_settings_cache()
    graph_module.reset_graph_service()
    service = graph_module.GraphService()
    return service


def _build_context(tmp_path, case_id: str = "case-alpha") -> tuple[AgentContext, CaseThreadMemory]:
    memory_store = AgentMemoryStore(tmp_path / "threads")
    now = datetime.now(timezone.utc)
    thread = AgentThread(
        thread_id="thread-1",
        case_id=case_id,
        question="List supporting documents",
        created_at=now,
        updated_at=now,
    )
    memory = CaseThreadMemory(thread, memory_store)
    context = AgentContext(
        case_id=case_id,
        question="List supporting documents",
        top_k=5,
        actor={"name": "Analyst"},
        memory=memory,
        telemetry={},
    )
    return context, memory


def test_graph_manager_generates_insight_and_updates_timeline(memory_graph, tmp_path):
    service = memory_graph
    service.upsert_document("doc-graph", "Graph Doc", {"case": "alpha"})
    timeline_store = TimelineStore(tmp_path / "timeline.jsonl")
    chain = _MockChain("MATCH (n) RETURN n")
    graph_agent = GraphManagerAgent(
        graph_service=service,
        timeline_store=timeline_store,
        chain=chain,
    )
    context, memory = _build_context(tmp_path)

    insight = graph_agent.ensure_insight(context)
    assert insight.execution.documents
    assert "doc-graph" in insight.execution.documents
    assert insight.timeline_event_id is not None
    events = timeline_store.read_all()
    assert len(events) == 1
    event = events[0]
    assert set(event.citations) == {"doc-graph"}
    stored = memory.state.get("insights", {}).get("graph")
    assert stored is not None
    assert stored.get("execution", {}).get("documents") == insight.execution.documents
    assert context.telemetry.get("graph", {}).get("documents") == len(insight.execution.documents)

    # Repeated invocation should reuse existing insight and avoid additional timeline events
    repeat = graph_agent.ensure_insight(context)
    assert repeat.timeline_event_id == insight.timeline_event_id
    assert len(timeline_store.read_all()) == 1
    assert len(chain.calls) == 1


def test_execute_agent_cypher_applies_sandbox(memory_graph):
    service = memory_graph
    result = service.execute_agent_cypher("Describe", "MATCH (n) RETURN n")
    assert "LIMIT" in result.cypher.upper()
    assert result.warnings


def test_execute_agent_cypher_rejects_unsafe(memory_graph):
    service = memory_graph
    with pytest.raises(WorkflowAbort):
        service.execute_agent_cypher("Describe", "DELETE n")
