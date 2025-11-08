from __future__ import annotations
from typing import List, Dict, Any

# Assuming AgentDefinition and AgentTool are defined elsewhere in the framework
# For now, we'll use the simple classes defined in qa_agents.py
from backend.app.agents.definitions.qa_agents import AgentDefinition, AgentTool
from backend.app.agents.definitions.qa_agents import validator_qa_agent, critic_qa_agent, refinement_qa_agent

# Import the actual research tools implemented in Phase 1
from backend.app.agents.tools.research_tools import (
    LegalResearchTool,
    WebScraperTool,
    ResearchSummarizerTool
)

# Instantiate the tools
legal_research_tool = LegalResearchTool()
web_scraper_tool = WebScraperTool()
research_summarizer_tool = ResearchSummarizerTool()

# Agent Definitions for Legal Research Crew
# Primary Agents
case_law_research_agent = AgentDefinition(
    name="CaseLawResearcher",
    role="Case Law Research Agent",
    description="Researches relevant case law using specialized databases and APIs.",
    tools=[legal_research_tool]
)

statute_regulation_research_agent = AgentDefinition(
    name="StatuteRegulationResearcher",
    role="Statute and Regulation Research Agent",
    description="Researches statutes and regulations from federal and state sources.",
    tools=[legal_research_tool]
)

procedure_court_rules_agent = AgentDefinition(
    name="ProcedureCourtRulesAgent",
    role="Procedure and Court Rules Agent",
    description="Researches court rules and procedural guidelines.",
    tools=[web_scraper_tool]
)

evidence_law_expert_agent = AgentDefinition(
    name="EvidenceLawExpert",
    role="Evidence Law Expert Agent",
    description="Provides expertise on evidence law and admissibility.",
    tools=[web_scraper_tool]
)

legal_history_context_agent = AgentDefinition(
    name="LegalHistoryContextAgent",
    role="Legal History and Context Agent",
    description="Provides historical context and background for legal issues.",
    tools=[web_scraper_tool]
)

# Backup Agents (for redundancy)
backup_case_law_research_agent = AgentDefinition(
    name="BackupCaseLawResearcher",
    role="Backup Case Law Research Agent",
    description="Backup agent for researching relevant case law.",
    tools=[legal_research_tool]
)

backup_statute_regulation_research_agent = AgentDefinition(
    name="BackupStatuteRegulationResearcher",
    role="Backup Statute and Regulation Research Agent",
    description="Backup agent for researching statutes and regulations.",
    tools=[legal_research_tool]
)

backup_procedure_court_rules_agent = AgentDefinition(
    name="BackupProcedureCourtRulesAgent",
    role="Backup Procedure and Court Rules Agent",
    description="Backup agent for researching court rules and procedural guidelines.",
    tools=[web_scraper_tool]
)

backup_evidence_law_expert_agent = AgentDefinition(
    name="BackupEvidenceLawExpert",
    role="Backup Evidence Law Expert Agent",
    description="Backup agent for providing expertise on evidence law.",
    tools=[web_scraper_tool]
)

backup_legal_history_context_agent = AgentDefinition(
    name="BackupLegalHistoryContextAgent",
    role="Backup Legal History and Context Agent",
    description="Backup agent for providing historical context for legal issues.",
    tools=[web_scraper_tool]
)

# Supervisor Agent for the crew
research_coordinator_integrator_agent = AgentDefinition(
    name="ResearchCoordinatorIntegrator",
    role="Research Coordinator and Integrator",
    description="Coordinates legal research tasks, integrates findings, and oversees the research process.",
    tools=[research_summarizer_tool],
    delegates=[
        case_law_research_agent.name,
        backup_case_law_research_agent.name,
        statute_regulation_research_agent.name,
        backup_statute_regulation_research_agent.name,
        procedure_court_rules_agent.name,
        backup_procedure_court_rules_agent.name,
        evidence_law_expert_agent.name,
        backup_evidence_law_expert_agent.name,
        legal_history_context_agent.name,
        backup_legal_history_context_agent.name,
        validator_qa_agent.name,
        critic_qa_agent.name,
        refinement_qa_agent.name
    ]
)


def build_legal_research_team(tools: List[AgentTool]) -> Dict[str, Any]:
    """
    Builds the Legal Research Team with redundancy and a 3-step QA process.
    """
    all_agents = [
        research_coordinator_integrator_agent,
        case_law_research_agent,
        backup_case_law_research_agent,
        statute_regulation_research_agent,
        backup_statute_regulation_research_agent,
        procedure_court_rules_agent,
        backup_procedure_court_rules_agent,
        evidence_law_expert_agent,
        backup_evidence_law_expert_agent,
        legal_history_context_agent,
        backup_legal_history_context_agent,
        validator_qa_agent,
        critic_qa_agent,
        refinement_qa_agent
    ]

    # Define the workflow (simplified representation)
    workflow = {
        "start": research_coordinator_integrator_agent.name,
        "tasks": [
            {
                "agent": research_coordinator_integrator_agent.name,
                "action": "delegate_research_tasks",
                "target": [
                    case_law_research_agent.name,
                    statute_regulation_research_agent.name,
                    procedure_court_rules_agent.name,
                    evidence_law_expert_agent.name,
                    legal_history_context_agent.name
                ]
            },
            {
                "agent": research_coordinator_integrator_agent.name,
                "action": "integrate_and_summarize_findings",
                "target": research_summarizer_tool.name
            },
            {
                "agent": research_coordinator_integrator_agent.name,
                "action": "run_qa_process",
                "target": [validator_qa_agent.name, critic_qa_agent.name, refinement_qa_agent.name]
            }
        ]
    }

    return {
        "name": "LegalResearchCrew",
        "agents": {agent.name: agent for agent in all_agents},
        "workflow": workflow,
        "tools": {tool.name: tool for tool in tools} # Pass relevant tools
    }