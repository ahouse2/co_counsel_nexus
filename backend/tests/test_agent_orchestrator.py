from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from backend.app.services.agents import MicrosoftAgentsOrchestrator
from backend.app.agents.definitions import AgentDefinition
from backend.app.agents.runner import SessionGraph
from backend.app.agents.tools import (
    ForensicsTool,
    IngestionTool,
    QATool,
    ResearchTool,
    StrategyTool,
)


def test_orchestrator_initialization():
    """Test that the orchestrator can be initialized."""
    strategy_tool = MagicMock(spec=StrategyTool)
    ingestion_tool = MagicMock(spec=IngestionTool)
    research_tool = MagicMock(spec=ResearchTool)
    forensics_tool = MagicMock(spec=ForensicsTool)
    qa_tool = MagicMock(spec=QATool)
    memory_store = MagicMock()
    graph_agent = MagicMock()

    orchestrator = MicrosoftAgentsOrchestrator(
        strategy_tool=strategy_tool,
        ingestion_tool=ingestion_tool,
        research_tool=research_tool,
        forensics_tool=forensics_tool,
        qa_tool=qa_tool,
        memory_store=memory_store,
    )
    assert orchestrator is not None


def test_session_graph_from_definitions():
    """Test that SessionGraph can be constructed from agent definitions."""
    # Mock tools
    strategy_tool = MagicMock(spec=StrategyTool, name="StrategyTool", component="strategy", role="strategy")
    ingestion_tool = MagicMock(spec=IngestionTool, name="IngestionTool", component="ingestion", role="ingestion")
    research_tool = MagicMock(spec=ResearchTool, name="ResearchTool", component="research", role="research")
    forensics_tool = MagicMock(spec=ForensicsTool, name="ForensicsTool", component="forensics", role="cocounsel")
    qa_tool = MagicMock(spec=QATool, name="QATool", component="qa", role="qa")

    # Create agent definitions
    strategy_def = AgentDefinition(
        name="Strategy", role="strategy", description="...", delegates=["Ingestion"], tool=strategy_tool
    )
    ingestion_def = AgentDefinition(
        name="Ingestion", role="ingestion", description="...", delegates=["Research"], tool=ingestion_tool
    )
    research_def = AgentDefinition(
        name="Research", role="research", description="...", delegates=["CoCounsel"], tool=research_tool
    )
    cocounsel_def = AgentDefinition(
        name="CoCounsel", role="cocounsel", description="...", delegates=["QA"], tool=forensics_tool
    )
    qa_def = AgentDefinition(name="QA", role="qa", description="...", delegates=[], tool=qa_tool)

    definitions = [
        strategy_def,
        ingestion_def,
        research_def,
        cocounsel_def,
        qa_def,
    ]

    session_graph = SessionGraph.from_definitions(definitions)

    assert session_graph.entry_role == "strategy"
    assert session_graph.order == ["strategy", "ingestion", "research", "cocounsel", "qa"]
    assert session_graph.nodes["strategy"].next_roles == ["ingestion"]
    assert session_graph.nodes["ingestion"].next_roles == ["research"]
    assert session_graph.nodes["research"].next_roles == ["cocounsel"]
    assert session_graph.nodes["cocounsel"].next_roles == ["qa"]
    assert session_graph.nodes["qa"].next_roles == []


    strategy_tool = MagicMock(spec=StrategyTool)
    ingestion_tool = MagicMock(spec=IngestionTool)
    research_tool = MagicMock(spec=ResearchTool)
    forensics_tool = MagicMock(spec=ForensicsTool)
    qa_tool = MagicMock(spec=QATool)
    memory_store = MagicMock()

    orchestrator = MicrosoftAgentsOrchestrator(
        strategy_tool=strategy_tool,
        ingestion_tool=ingestion_tool,
        research_tool=research_tool,
        forensics_tool=forensics_tool,
        qa_tool=qa_tool,
        memory_store=memory_store,
    )

    # Policy state with suppressed roles and graph overrides
    policy_state = {
        "enabled": True,
        "suppressed_roles": ["ingestion"],
        "graph_overrides": {"strategy": ["research"]},
    }

    session_graph = orchestrator._build_session_graph(policy_state)

    assert session_graph.entry_role == "strategy"
    assert "ingestion" not in session_graph.nodes
    assert session_graph.nodes["strategy"].next_roles == ["research"]
    assert session_graph.order == ["strategy", "research", "cocounsel", "qa"]

    # Policy state with no suppressed roles or overrides
    policy_state_no_change = {
        "enabled": True,
        "suppressed_roles": [],
        "graph_overrides": {},
    }
    session_graph_no_change = orchestrator._build_session_graph(policy_state_no_change)
    assert session_graph_no_change.entry_role == "strategy"
    assert session_graph_no_change.order == ["strategy", "ingestion", "research", "cocounsel", "qa"]


def test_orchestrator_build_session_graph_policy_disabled():
    """Test that the orchestrator builds the session graph correctly when the policy is disabled."""
    strategy_tool = MagicMock(spec=StrategyTool)
    ingestion_tool = MagicMock(spec=IngestionTool)
    research_tool = MagicMock(spec=ResearchTool)
    forensics_tool = MagicMock(spec=ForensicsTool)
    qa_tool = MagicMock(spec=QATool)
    memory_store = MagicMock()
    graph_agent = MagicMock()

    orchestrator = MicrosoftAgentsOrchestrator(
        strategy_tool=strategy_tool,
        ingestion_tool=ingestion_tool,
        research_tool=research_tool,
        forensics_tool=forensics_tool,
        qa_tool=qa_tool,
        memory_store=memory_store,
    )

    # Policy state with policy disabled
    policy_state_disabled = {
        "enabled": False,
        "suppressed_roles": ["ingestion"],
        "graph_overrides": {"strategy": ["research"]},
    }

    session_graph_disabled = orchestrator._build_session_graph(policy_state_disabled)

    # When policy is disabled, it should return the default graph without any changes
    assert session_graph_disabled.entry_role == "strategy"
    assert session_graph_disabled.order == ["strategy", "ingestion", "research", "cocounsel", "qa"]
    assert session_graph_disabled.nodes["strategy"].next_roles == ["ingestion"]
    assert session_graph_disabled.nodes["ingestion"].next_roles == ["research"]
    assert session_graph_disabled.nodes["research"].next_roles == ["cocounsel"]
    assert session_graph_disabled.nodes["cocounsel"].next_roles == ["qa"]
    assert session_graph_disabled.nodes["qa"].next_roles == []
