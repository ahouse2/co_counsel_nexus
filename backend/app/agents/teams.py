from __future__ import annotations
from typing import Dict, List
from .definitions import AgentDefinition
from .tools import AgentTool

def build_forensics_team(tools: Dict[str, AgentTool]) -> List[AgentDefinition]:
    """Defines the Forensics Agent Team."""
    return [
        AgentDefinition(
            name="ForensicsLead",
            role="forensics_lead",
            description="Manages the forensics team, delegates tasks, and synthesizes findings.",
            tool=tools["strategy"],  # Using strategy tool for planning
            delegates=["CryptoTracer", "EvidenceAnalyzer"],
        ),
        AgentDefinition(
            name="CryptoTracer",
            role="crypto_tracer",
            description="Traces cryptocurrency transactions and analyzes blockchain data.",
            tool=tools["forensics"], # Using forensics tool for crypto tracing
            delegates=[],
        ),
        AgentDefinition(
            name="EvidenceAnalyzer",
            role="evidence_analyzer",
            description="Analyzes digital evidence, extracts artifacts, and generates reports.",
            tool=tools["ingestion"], # Using ingestion tool for evidence analysis
            delegates=[],
        ),
    ]

def build_dev_team(tools: Dict[str, AgentTool]) -> List[AgentDefinition]:
    """Defines the Dev Agent Team."""
    return [
        AgentDefinition(
            name="DevLead",
            role="dev_lead",
            description="Manages the dev team, assigns tasks, and reviews code.",
            tool=tools["strategy"], # Using strategy tool for planning
            delegates=["CodeGenerator", "CodeTester"],
        ),
        AgentDefinition(
            name="CodeGenerator",
            role="code_generator",
            description="Generates code based on specifications.",
            tool=tools["echo"], # Using echo tool as a stand-in for a code generation tool
            delegates=[],
        ),
        AgentDefinition(
            name="CodeTester",
            role="code_tester",
            description="Generates and runs tests for code.",
            tool=tools["qa"], # Using qa tool for testing
            delegates=[],
        ),
    ]
