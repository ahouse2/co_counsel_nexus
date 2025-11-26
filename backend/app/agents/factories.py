from typing import Any
from backend.app.agents.graph_manager import GraphManagerAgent
from backend.app.agents.qa import QAAgent
from backend.ingestion.llama_index_factory import BaseLlmService

def build_graph_rag_agent(llm_service: BaseLlmService, document_store: Any) -> GraphManagerAgent:
    """
    Builds the GraphManagerAgent with the given LLM service.
    
    Args:
        llm_service: The LLM service to use for text-to-Cypher generation.
        document_store: The document store (currently unused by GraphManagerAgent but kept for signature compatibility).
        
    Returns:
        A configured GraphManagerAgent instance.
    """
    # document_store is currently unused by GraphManagerAgent but kept for signature compatibility
    return GraphManagerAgent(llm_service=llm_service)

def build_qa_agent(llm_service: BaseLlmService) -> QAAgent:
    """
    Builds the QAAgent.
    
    Args:
        llm_service: The LLM service to use for evaluation.
        
    Returns:
        A configured QAAgent instance.
    """
    return QAAgent(llm_service=llm_service)
