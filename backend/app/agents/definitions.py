from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .tools import AgentTool


@dataclass(slots=True)
class AgentDefinition:
    name: str
    role: str
    description: str
    tool: AgentTool
    delegates: List[str]


def build_agent_graph(tools: Dict[str, AgentTool]) -> List[AgentDefinition]:
    """Translate TRD personas into Microsoft Agents SDK definitions."""

    return [
        AgentDefinition(
            name="Strategy",
            role="strategy",
            description=(
                "TRD Strategy Planner – analyses the prompt, derives scope, and seeds the"
                " case memory with a stepwise plan."
            ),
            tool=tools["strategy"],
            delegates=["Ingestion"],
        ),
        AgentDefinition(
            name="Ingestion",
            role="ingestion",
            description=(
                "Ingestion Steward – inspects manifests and ensures evidence availability"
                " before research begins."
            ),
            tool=tools["ingestion"],
            delegates=["Research"],
        ),
        AgentDefinition(
            name="Research",
            role="research",
            description=(
                "Research Analyst – performs retrieval against the knowledge graph and"
                " vector indices to assemble a briefing."
            ),
            tool=tools["research"],
            delegates=["CoCounsel"],
        ),
        AgentDefinition(
            name="CoCounsel",
            role="cocounsel",
            description=(
                "Lead CoCounsel – stitches research results with forensics evidence,"
                " preparing the answer package."
            ),
            tool=tools["cocounsel"],
            delegates=["QA"],
        ),
        AgentDefinition(
            name="QA",
            role="qa",
            description=(
                "QA Adjudicator – evaluates the combined response using the rubric and"
                " records telemetry."
            ),
            tool=tools["qa"],
            delegates=[],
        ),
        AgentDefinition(
            name="Echo",
            role="echo",
            description="A simple agent that echoes back the input using an LLM.",
            tool=tools["echo"],
            delegates=[],
        ),
    ]
