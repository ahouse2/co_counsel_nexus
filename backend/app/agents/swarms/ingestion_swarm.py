import logging
from typing import List
from backend.app.agents.swarms_adapter import SwarmsAdapter, AgentFactory
from backend.app.services.classification_service import ClassificationService
from backend.app.services.document_service import DocumentService

# Try importing Swarms classes
try:
    from swarms import Agent, SequentialWorkflow
except ImportError:
    class SequentialWorkflow:
        def __init__(self, *args, **kwargs): pass
        def run(self, *args, **kwargs): pass

logger = logging.getLogger(__name__)

class IngestionSwarm:
    """
    A swarm of agents responsible for the document ingestion lifecycle.
    """
    def __init__(self, llm, doc_service: DocumentService, classification_service: ClassificationService):
        self.llm = llm
        self.doc_service = doc_service
        self.classification_service = classification_service
        self.adapter = SwarmsAdapter()

    def create_swarm(self) -> SequentialWorkflow:
        """
        Creates a sequential workflow for ingestion:
        1. Classifier Agent: Classifies the doc.
        2. Reviewer Agent: Reviews the classification (optional, for demo).
        """
        
        # 1. Classifier Agent
        classifier_tool = self.adapter.create_tool(
            name="ClassifyDocument",
            func=self.classification_service.classify_document_sync,
            description="Classifies a document text into legal categories."
        )
        
        classifier_agent = self.adapter.create_agent(
            agent_name="DocClassifier",
            system_prompt="You are a Document Classifier. Receive text, classify it using the tool, and output the category.",
            llm=self.llm,
            tools=[classifier_tool]
        )
        
        # 2. Metadata Extractor Agent (using our existing extractors conceptually)
        # For now, let's just have a simple workflow.
        
        workflow = SequentialWorkflow(
            agents=[classifier_agent],
            max_loops=1,
            verbose=True
        )
        
        return workflow

    def run(self, document_text: str):
        """
        Runs the ingestion swarm on a document.
        """
        swarm = self.create_swarm()
        return swarm.run(document_text)
