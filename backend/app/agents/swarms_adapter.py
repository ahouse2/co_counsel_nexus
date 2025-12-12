import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

# Try importing Swarms, handle if missing
try:
    from swarms import Agent, Tool
except ImportError:
    # Mock classes for development if swarms is not installed
    class Agent:
        def __init__(self, *args, **kwargs): pass
        def run(self, *args, **kwargs): pass
    class Tool:
        def __init__(self, *args, **kwargs): pass

logger = logging.getLogger(__name__)

class SwarmsAdapter:
    """
    Adapter to create Swarms Agents and Tools from existing application services.
    """
    
    @staticmethod
    def create_tool(
        name: str,
        func: Callable,
        description: str
    ) -> Tool:
        """
        Wraps a function into a Swarms Tool.
        """
        return Tool(
            name=name,
            func=func,
            description=description
        )

    @staticmethod
    def create_agent(
        agent_name: str,
        system_prompt: str,
        llm: Any, # Expecting a Swarms-compatible LLM or generic
        tools: List[Tool] = None,
        max_loops: int = 1,
    ) -> Agent:
        """
        Creates a Swarms Agent.
        """
        return Agent(
            agent_name=agent_name,
            system_prompt=system_prompt,
            llm=llm,
            tools=tools or [],
            max_loops=max_loops,
            autosave=True,
            dashboard=False,
            verbose=True,
            dynamic_temperature_enabled=True,
            saved_state_path=f"{agent_name}.json",
            user_name="User",
            retry_attempts=1,
            context_length=200000,
            return_step_meta=False,
        )

# Example usage / Factory for specific agents
from backend.app.services.forensics_service import ForensicsService
from backend.app.services.knowledge_graph_service import KnowledgeGraphService
from backend.app.services.classification_service import ClassificationService

class AgentFactory:
    def __init__(self, llm):
        self.llm = llm

    def create_forensics_agent(self, forensics_service: ForensicsService) -> Agent:
        """
        Creates an agent capable of triggering deep forensics.
        """
        tools = [
            SwarmsAdapter.create_tool(
                name="RunDeepForensics",
                func=forensics_service.run_deep_forensics,
                description="Triggers deep forensic analysis for a document ID."
            )
        ]
        
        return SwarmsAdapter.create_agent(
            agent_name="ForensicAnalyst",
            system_prompt="You are a Forensic Analyst. Your job is to analyze suspicious documents. Use the RunDeepForensics tool when asked to analyze a document.",
            llm=self.llm,
            tools=tools
        )

    def create_graph_agent(self, kg_service: KnowledgeGraphService) -> Agent:
        """
        Creates an agent capable of querying the Knowledge Graph.
        """
        # We might need to wrap async methods to sync if Swarms expects sync tools
        # For now assuming we can handle it or using the sync wrappers we might create.
        
        def search_graph(query: str):
            # This needs to be sync for the tool? 
            # If Swarms supports async tools, great. If not, we need a sync wrapper.
            # Let's assume sync for safety in this adapter.
            import asyncio
            return asyncio.run(kg_service.search_legal_references(query))

        tools = [
            SwarmsAdapter.create_tool(
                name="SearchLegalGraph",
                func=search_graph,
                description="Searches the legal knowledge graph for theories and precedents."
            )
        ]
        
        return SwarmsAdapter.create_agent(
            agent_name="GraphAnalyst",
            system_prompt="You are a Knowledge Graph Analyst. Search the graph for legal context when asked.",
            llm=self.llm,
            tools=tools
        )
