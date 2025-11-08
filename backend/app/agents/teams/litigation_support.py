from __future__ import annotations
from typing import List, Dict, Any

# Assuming AgentDefinition and AgentTool are defined elsewhere in the framework
# For now, we'll use the simple classes defined in qa_agents.py
from backend.app.agents.definitions.qa_agents import AgentDefinition, AgentTool
from backend.app.agents.definitions.qa_agents import validator_qa_agent, critic_qa_agent, refinement_qa_agent

# Import relevant tools
from backend.app.agents.tools.presentation_tools import TimelineTool
from backend.app.agents.tools.research_tools import LegalResearchTool

# Instantiate the tools
timeline_tool = TimelineTool()
legal_research_tool = LegalResearchTool()

# Placeholder Tools for Litigation Support
from backend.app.services.knowledge_graph_service import KnowledgeGraphService

class KnowledgeGraphQueryTool(AgentTool):
    def __init__(self):
        super().__init__("KnowledgeGraphQueryTool", "Queries the Knowledge Graph for factual elements and relationships.", self.query_kg)
        self.service = KnowledgeGraphService()
    async def query_kg(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return await self.service.query_graph(cypher_query, parameters)

from backend.app.services.llm_service import get_llm_service

class LLMDraftingTool(AgentTool):
    def __init__(self):
        super().__init__("LLMDraftingTool", "Drafts legal documents and motions using an LLM.", self.draft_document)
        self.llm_service = get_llm_service()
    async def draft_document(self, prompt: str, context: str = "") -> Dict[str, Any]:
        full_prompt = f"Draft a legal document based on the following prompt and context:\n\nPrompt: {prompt}\n\nContext: {context}"
        drafted_document = await self.llm_service.generate_text(full_prompt)
        return {"drafted_document": drafted_document}

from backend.app.services.simulation_service import SimulationService

class SimulationTool(AgentTool):
    def __init__(self):
        super().__init__("SimulationTool", "Runs legal training simulations and checks procedural requirements.", self.run_simulation)
        self.service = SimulationService()
    async def run_simulation(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        return await self.service.run_mock_court_simulation(scenario)
    async def check_compliance(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return await self.service.check_procedural_compliance(action, context)


# Agent Definitions for Litigation Support Crew
# Primary Agents
lead_Counsel_Strategist_Agent = AgentDefinition(
    name="LeadCounselStrategist",
    role="Lead Counsel Strategist Agent",
    description="The lead strategist. Cross-references all available resources to formulate a theory of the case.",
    tools=[] # This agent primarily delegates and synthesizes
)

strategist_finder_of_fact_agent = AgentDefinition(
    name="StrategistFinderOfFact",
    role="Strategist Team Member - Finder of Fact",
    description="Assists the strategy team by identifying factual elements using the graphing database.",
    tools=[KnowledgeGraphQueryTool()]
)

strategist_devils_advocate_agent = AgentDefinition(
    name="StrategistDevilsAdvocate",
    role="Strategist Team Member - Devil's Advocate",
    description="Double checks facts and critiques factual conclusions to prevent hallucinations.",
    tools=[] # This agent primarily uses reasoning and critique
)

strategist_timeline_event_coordinator_agent = AgentDefinition(
    name="StrategistTimelineEventCoordinator",
    role="Strategist Team Member - Timeline Event Coordinator",
    description="Ensures chronological correctness of facts and events in the case timeline.",
    tools=[timeline_tool]
)

strategist_finder_of_law_agent = AgentDefinition(
    name="StrategistFinderOfLaw",
    role="Strategist Team Member - Finder of Law",
    description="Works with the legal research team to validate and integrate legal doctrine.",
    tools=[legal_research_tool]
)

motion_drafting_agent = AgentDefinition(
    name="MotionDraftingAgent",
    role="Motion Drafting Agent",
    description="Drafts legal motions and responses.",
    tools=[LLMDraftingTool()]
)

litigation_training_coach_agent = AgentDefinition(
    name="LitigationTrainingCoach",
    role="Litigation Training Coach Agent",
    description="Provides training simulations for Mock Court and ensures procedural compliance.",
    tools=[SimulationTool()]
)

# Backup Agents (for redundancy)
backup_strategist_finder_of_fact_agent = AgentDefinition(
    name="BackupStrategistFinderOfFact",
    role="Backup Strategist Team Member - Finder of Fact",
    description="Backup agent for identifying factual elements using the graphing database.",
    tools=[KnowledgeGraphQueryTool()]
)

backup_strategist_devils_advocate_agent = AgentDefinition(
    name="BackupStrategistDevilsAdvocate",
    role="Backup Strategist Team Member - Devil's Advocate",
    description="Backup agent for double checking facts and critiquing factual conclusions.",
    tools=[]
)

backup_strategist_timeline_event_coordinator_agent = AgentDefinition(
    name="BackupStrategistTimelineEventCoordinator",
    role="Backup Strategist Team Member - Timeline Event Coordinator",
    description="Backup agent for ensuring chronological correctness of facts and events.",
    tools=[timeline_tool]
)

backup_strategist_finder_of_law_agent = AgentDefinition(
    name="BackupStrategistFinderOfLaw",
    role="Backup Strategist Team Member - Finder of Law",
    description="Backup agent for validating and integrating legal doctrine.",
    tools=[legal_research_tool]
)

backup_motion_drafting_agent = AgentDefinition(
    name="BackupMotionDraftingAgent",
    role="Backup Motion Drafting Agent",
    description="Backup agent for drafting legal motions and responses.",
    tools=[LLMDraftingTool()]
)

backup_litigation_training_coach_agent = AgentDefinition(
    name="BackupLitigationTrainingCoach",
    role="Backup Litigation Training Coach Agent",
    description="Backup agent for providing training simulations and ensuring procedural compliance.",
    tools=[SimulationTool()]
)

# QA Lead for the crew
legal_strategy_reviewer_senior_counsel_agent = AgentDefinition(
    name="LegalStrategyReviewerSeniorCounsel",
    role="Legal Strategy Reviewer - Senior Counsel Agent",
    description="Reviews legal strategy and the theory of the case as a whole.",
    delegates=[
        validator_qa_agent.name,
        critic_qa_agent.name,
        refinement_qa_agent.name
    ]
)


def build_litigation_support_team(tools: List[AgentTool]) -> Dict[str, Any]:
    """
    Builds the Litigation Support Team with redundancy and a 3-step QA process.
    """
    all_agents = [
        lead_Counsel_Strategist_Agent,
        strategist_finder_of_fact_agent,
        backup_strategist_finder_of_fact_agent,
        strategist_devils_advocate_agent,
        backup_strategist_devils_advocate_agent,
        strategist_timeline_event_coordinator_agent,
        backup_strategist_timeline_event_coordinator_agent,
        strategist_finder_of_law_agent,
        backup_strategist_finder_of_law_agent,
        motion_drafting_agent,
        backup_motion_drafting_agent,
        litigation_training_coach_agent,
        backup_litigation_training_coach_agent,
        legal_strategy_reviewer_senior_counsel_agent,
        validator_qa_agent,
        critic_qa_agent,
        refinement_qa_agent
    ]

    # Define the workflow (simplified representation)
    workflow = {
        "start": lead_Counsel_Strategist_Agent.name,
        "tasks": [
            {
                "agent": lead_Counsel_Strategist_Agent.name,
                "action": "formulate_case_theory",
                "target": [
                    strategist_finder_of_fact_agent.name,
                    strategist_finder_of_law_agent.name,
                    strategist_timeline_event_coordinator_agent.name
                ]
            },
            {
                "agent": strategist_finder_of_fact_agent.name,
                "action": "critique_facts",
                "target": strategist_devils_advocate_agent.name
            },
            {
                "agent": lead_Counsel_Strategist_Agent.name,
                "action": "draft_motion",
                "target": motion_drafting_agent.name
            },
            {
                "agent": lead_Counsel_Strategist_Agent.name,
                "action": "review_strategy",
                "target": legal_strategy_reviewer_senior_counsel_agent.name
            },
            {
                "agent": legal_strategy_reviewer_senior_counsel_agent.name,
                "action": "run_qa_process",
                "target": [validator_qa_agent.name, critic_qa_agent.name, refinement_qa_agent.name]
            }
        ]
    }

    return {
        "name": "LitigationSupportCrew",
        "agents": {agent.name: agent for agent in all_agents},
        "workflow": workflow,
        "tools": {tool.name: tool for tool in tools} # Pass relevant tools
    }