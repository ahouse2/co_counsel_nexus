from __future__ import annotations
from typing import List, Dict, Any

# Assuming AgentDefinition and AgentTool are defined elsewhere in the framework
# For now, we'll use the simple classes defined in qa_agents.py
from backend.app.agents.definitions.qa_agents import AgentDefinition, AgentTool
from backend.app.agents.definitions.qa_agents import validator_qa_agent, critic_qa_agent, refinement_qa_agent

from backend.app.services.document_processing_service import DocumentProcessingService

# Placeholder Tools for Document Ingestion
class DocumentPreprocessingTool(AgentTool):
    def __init__(self):
        super().__init__("DocumentPreprocessingTool", "Preprocesses raw documents for ingestion.", self.preprocess)
        self.service = DocumentProcessingService()
    async def preprocess(self, document_path: str) -> Dict[str, Any]:
        return await self.service.preprocess_document(document_path)

from backend.app.services.indexing_embedding_service import IndexingEmbeddingService

class ContentIndexingTool(AgentTool):
    def __init__(self):
        super().__init__("ContentIndexingTool", "Indexes document content and generates embeddings.", self.index_content)
        self.service = IndexingEmbeddingService()
    async def index_content(self, document_id: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return await self.service.index_document(document_id, content, metadata)

from backend.app.services.knowledge_graph_service import KnowledgeGraphService

class KnowledgeGraphBuilderTool(AgentTool):
    def __init__(self):
        super().__init__("KnowledgeGraphBuilderTool", "Builds and updates the knowledge graph with document entities and relationships.", self.build_kg)
        self.service = KnowledgeGraphService()
    async def build_kg(self, entity_type: str, properties: Dict[str, Any], relationships: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Add the main entity
        entity_result = await self.service.add_entity(entity_type, properties)
        
        # Add relationships if provided
        relationship_results = []
        if relationships:
            for rel in relationships:
                rel_result = await self.service.add_relationship(
                    from_entity_id=rel["from_entity_id"],
                    from_entity_type=rel["from_entity_type"],
                    to_entity_id=rel["to_entity_id"],
                    to_entity_type=rel["to_entity_type"],
                    relationship_type=rel["relationship_type"],
                    properties=rel.get("properties")
                )
                relationship_results.append(rel_result)
        
        return {"entity_result": entity_result, "relationship_results": relationship_results}

from backend.app.services.database_query_service import DatabaseQueryService

class DatabaseQueryTool(AgentTool):
    def __init__(self):
        super().__init__("DatabaseQueryTool", "Queries internal and external databases for relevant information.", self.query_db)
        self.service = DatabaseQueryService()
    async def query_db(self, query_string: str, db_type: str = "sql") -> List[Dict[str, Any]]:
        return await self.service.execute_query(query_string, db_type)

from backend.app.services.llm_service import get_llm_service

class DocumentSummaryTool(AgentTool):
    def __init__(self):
        super().__init__("DocumentSummaryTool", "Summarizes documents using advanced NLP models.", self.summarize_document)
        self.llm_service = get_llm_service()
    async def summarize_document(self, content: str) -> Dict[str, Any]:
        prompt = f"Please summarize the following document:\n\n{content[:8000]}..." # Truncate for LLM context
        summary = await self.llm_service.generate_text(prompt)
        return {"summary": summary}


# Agent Definitions for Document Ingestion Crew
# Primary Agents
document_ingestion_preprocessing_agent = AgentDefinition(
    name="DocumentIngestionPreprocessor",
    role="Document Preprocessor",
    description="Preprocesses raw documents, performing OCR, cleaning, and initial structuring.",
    tools=[DocumentPreprocessingTool()]
)

content_indexing_embedding_agent = AgentDefinition(
    name="ContentIndexingEmbedder",
    role="Content Indexer and Embedder",
    description="Indexes document content and generates vector embeddings for search and retrieval.",
    tools=[ContentIndexingTool()]
)

knowledge_graph_builder_agent = AgentDefinition(
    name="KnowledgeGraphBuilder",
    role="Knowledge Graph Builder",
    description="Extracts entities and relationships from documents to build and update the knowledge graph.",
    tools=[KnowledgeGraphBuilderTool()]
)

database_query_agent = AgentDefinition(
    name="DatabaseQueryAgent",
    role="Database Query Agent",
    description="Queries various databases to enrich document context or retrieve related information.",
    tools=[DatabaseQueryTool()]
)

document_summary_agent = AgentDefinition(
    name="DocumentSummarizer",
    role="Document Summarizer",
    description="Generates concise summaries of documents for quick review and understanding.",
    tools=[DocumentSummaryTool()]
)

# Backup Agents (for redundancy)
backup_document_ingestion_preprocessing_agent = AgentDefinition(
    name="BackupDocumentIngestionPreprocessor",
    role="Backup Document Preprocessor",
    description="Backup agent for preprocessing raw documents.",
    tools=[DocumentPreprocessingTool()]
)

backup_content_indexing_embedding_agent = AgentDefinition(
    name="BackupContentIndexingEmbedder",
    role="Backup Content Indexer and Embedder",
    description="Backup agent for indexing document content and generating vector embeddings.",
    tools=[ContentIndexingTool()]
)

backup_knowledge_graph_builder_agent = AgentDefinition(
    name="BackupKnowledgeGraphBuilder",
    role="Backup Knowledge Graph Builder",
    description="Backup agent for building and updating the knowledge graph.",
    tools=[KnowledgeGraphBuilderTool()]
)

backup_database_query_agent = AgentDefinition(
    name="BackupDatabaseQueryAgent",
    role="Backup Database Query Agent",
    description="Backup agent for querying internal and external databases.",
    tools=[DatabaseQueryTool()]
)

backup_document_summary_agent = AgentDefinition(
    name="BackupDocumentSummarizer",
    role="Backup Document Summarizer",
    description="Backup agent for generating concise summaries of documents.",
    tools=[DocumentSummaryTool()]
)

# Supervisor Agent for the crew
document_ingestion_supervisor_agent = AgentDefinition(
    name="DocumentIngestionSupervisor",
    role="Document Ingestion Crew Supervisor",
    description="Oversees the document ingestion process, delegates tasks, and manages redundancy.",
    delegates=[
        document_ingestion_preprocessing_agent.name,
        backup_document_ingestion_preprocessing_agent.name,
        content_indexing_embedding_agent.name,
        backup_content_indexing_embedding_agent.name,
        knowledge_graph_builder_agent.name,
        backup_knowledge_graph_builder_agent.name,
        database_query_agent.name,
        backup_database_query_agent.name,
        document_summary_agent.name,
        backup_document_summary_agent.name,
        validator_qa_agent.name,
        critic_qa_agent.name,
        refinement_qa_agent.name
    ]
)

# QA Lead for the crew
data_integrity_qa_ingestion_qa_agent = AgentDefinition(
    name="DataIntegrityQAIngestionQA",
    role="Data Integrity and Ingestion QA Lead",
    description="Leads the QA process for document ingestion, ensuring data integrity and quality.",
    delegates=[
        validator_qa_agent.name,
        critic_qa_agent.name,
        refinement_qa_agent.name
    ]
)


def build_document_ingestion_team(tools: List[AgentTool]) -> Dict[str, Any]:
    """
    Builds the Document Ingestion Team with redundancy and a 3-step QA process.
    """
    # This function would typically return a graph or a structured team object
    # that the Microsoft Agents Framework can execute.
    # For now, we return a dictionary representing the team structure.

    # All agents in this team
    all_agents = [
        document_ingestion_supervisor_agent,
        document_ingestion_preprocessing_agent,
        backup_document_ingestion_preprocessing_agent,
        content_indexing_embedding_agent,
        backup_content_indexing_embedding_agent,
        knowledge_graph_builder_agent,
        backup_knowledge_graph_builder_agent,
        database_query_agent,
        backup_database_query_agent,
        document_summary_agent,
        backup_document_summary_agent,
        data_integrity_qa_ingestion_qa_agent,
        validator_qa_agent,
        critic_qa_agent,
        refinement_qa_agent
    ]

    # Define the workflow (simplified representation)
    workflow = {
        "start": document_ingestion_supervisor_agent.name,
        "tasks": [
            {
                "agent": document_ingestion_supervisor_agent.name,
                "action": "delegate_preprocessing",
                "target": [document_ingestion_preprocessing_agent.name, backup_document_ingestion_preprocessing_agent.name]
            },
            {
                "agent": document_ingestion_preprocessing_agent.name,
                "action": "index_content",
                "target": [content_indexing_embedding_agent.name, backup_content_indexing_embedding_agent.name]
            },
            {
                "agent": content_indexing_embedding_agent.name,
                "action": "build_knowledge_graph",
                "target": [knowledge_graph_builder_agent.name, backup_knowledge_graph_builder_agent.name]
            },
            {
                "agent": knowledge_graph_builder_agent.name,
                "action": "summarize_document",
                "target": [document_summary_agent.name, backup_document_summary_agent.name]
            },
            {
                "agent": document_summary_agent.name,
                "action": "pass_to_qa_lead",
                "target": data_integrity_qa_ingestion_qa_agent.name
            },
            {
                "agent": data_integrity_qa_ingestion_qa_agent.name,
                "action": "run_qa_process",
                "target": [validator_qa_agent.name, critic_qa_agent.name, refinement_qa_agent.name]
            }
        ]
    }

    return {
        "name": "DocumentIngestionCrew",
        "agents": {agent.name: agent for agent in all_agents},
        "workflow": workflow,
        "tools": {tool.name: tool for tool in tools} # Pass relevant tools
    }