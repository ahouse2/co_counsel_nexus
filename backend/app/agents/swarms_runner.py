import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

# Import existing definitions
from backend.app.agents.definitions.qa_agents import AgentDefinition
from backend.app.agents.teams.litigation_support import build_litigation_support_team
from backend.app.agents.teams.document_ingestion import build_document_ingestion_team
from backend.app.agents.teams.legal_research import build_legal_research_team
from backend.app.agents.teams.forensic_analysis import build_forensic_analysis_team
from backend.app.agents.teams.software_development import build_software_development_team
from backend.app.agents.teams.ai_qa_oversight import build_ai_qa_oversight_committee

# Import Swarms (or mock if missing)
try:
    from swarms import Agent, SequentialWorkflow
except ImportError:
    # Mock for development environment without swarms installed
    class Agent:
        def __init__(self, agent_name, system_prompt, llm, tools, **kwargs):
            self.agent_name = agent_name
            self.system_prompt = system_prompt
            self.llm = llm
            self.tools = tools
        def run(self, task: str):
            return f"[Mock Swarms] Agent {self.agent_name} processed: {task}"
            
    class SequentialWorkflow:
        def __init__(self, agents, max_loops, verbose):
            self.agents = agents
        def run(self, task: str):
            result = task
            for agent in self.agents:
                result = agent.run(result)
            return result

logger = logging.getLogger(__name__)

class SwarmsRunner:
    """
    Orchestrator that executes the agent teams using the Swarms framework.
    Replaces the legacy MicrosoftAgentsOrchestrator.
    """
    def __init__(self, llm_service):
        self.llm_service = llm_service
        # Initialize tools (reusing the logic from runner.py or instantiating fresh)
        # For simplicity, we'll instantiate fresh tools here or pass them in.
        self.tools_registry = self._initialize_tools()
        
        # Build Teams
        self.teams = {
            "litigation_support": build_litigation_support_team(list(self.tools_registry.values())),
            "document_ingestion": build_document_ingestion_team(list(self.tools_registry.values())),
            "legal_research": build_legal_research_team(list(self.tools_registry.values())),
            "forensics": build_forensic_analysis_team(list(self.tools_registry.values())),
            "software_development": build_software_development_team(list(self.tools_registry.values())),
            "ai_qa_oversight": build_ai_qa_oversight_committee(list(self.tools_registry.values())),
        }

    def _initialize_tools(self) -> Dict[str, Any]:
        """
        Instantiates all available tools.
        """
        from backend.app.agents.tools.presentation_tools import TimelineTool
        from backend.app.agents.tools.research_tools import LegalResearchTool
        from backend.app.agents.teams.litigation_support import KnowledgeGraphQueryTool, LLMDraftingTool, SimulationTool
        
        # ... Add all other tools ...
        
        return {
            "TimelineTool": TimelineTool(),
            "LegalResearchTool": LegalResearchTool(),
            "KnowledgeGraphQueryTool": KnowledgeGraphQueryTool(),
            "LLMDraftingTool": LLMDraftingTool(),
            "SimulationTool": SimulationTool(),
            # Add others as needed
        }

    def _convert_to_swarm_agent(self, agent_def: AgentDefinition) -> Agent:
        """
        Converts our internal AgentDefinition to a Swarms Agent.
        """
        # Wrap our AgentTool into whatever Swarms expects (usually a function or a class with run method)
        swarm_tools = []
        for tool in agent_def.tools:
            # Swarms expects a list of functions or tools. 
            # Our AgentTool has an 'invoke' method or 'func'.
            # We might need to wrap it.
            swarm_tools.append(tool) # Assuming Swarms can handle our tool object or we adapt it

        return Agent(
            agent_name=agent_def.name,
            system_prompt=f"You are {agent_def.name}. Role: {agent_def.role}. Description: {agent_def.description}",
            llm=self.llm_service, # Swarms expects an LLM object
            tools=swarm_tools,
            max_loops=1,
            verbose=True,
            autosave=True,
            dashboard=False,
            saved_state_path=f"{agent_def.name}.json",
        )

    def get_swarm(self, team_name: str) -> SequentialWorkflow:
        """
        Constructs a Swarms workflow for the specified team.
        """
        team_data = self.teams.get(team_name)
        if not team_data:
            raise ValueError(f"Team {team_name} not found.")

        # Convert all definitions to Swarms Agents
        swarm_agents = []
        
        # We need to determine the order. The 'workflow' dict in team_data has a 'tasks' list.
        # For a SequentialWorkflow, we just need the list of agents in order.
        # But our workflow is more complex (DAG).
        # For this MVP, let's extract the unique agents involved in the tasks in order.
        
        seen_agents = set()
        for task in team_data["workflow"]["tasks"]:
            agent_name = task["agent"]
            if agent_name not in seen_agents:
                agent_def = team_data["agents"][agent_name]
                swarm_agent = self._convert_to_swarm_agent(agent_def)
                swarm_agents.append(swarm_agent)
                seen_agents.add(agent_name)
                
        return SequentialWorkflow(
            agents=swarm_agents,
            max_loops=1,
            verbose=True
        )

    def route_and_run(self, question: str):
        """
        Routes the question to the appropriate team and runs the swarm.
        """
        team_name = self._determine_team(question)
        logger.info(f"Routing to team: {team_name}")
        
        swarm = self.get_swarm(team_name)
        return swarm.run(question)

    def _determine_team(self, question: str) -> str:
        """
        Simple keyword-based routing (can be upgraded to LLM router).
        """
        q = question.lower()
        if "mock trial" in q or "strategy" in q or "motion" in q:
            return "litigation_support"
        elif "ingest" in q or "upload" in q:
            return "document_ingestion"
        elif "research" in q or "case law" in q:
            return "legal_research"
        elif "forensic" in q or "tamper" in q:
            return "forensics"
        elif "code" in q or "develop" in q:
            return "software_development"
        elif "audit" in q or "qa" in q:
            return "ai_qa_oversight"
        else:
            return "litigation_support" # Default

def get_swarms_runner():
    """
    Dependency to get the SwarmsRunner instance.
    """
    from backend.app.services.llm_service import get_llm_service
    llm_service = get_llm_service()
    return SwarmsRunner(llm_service)
