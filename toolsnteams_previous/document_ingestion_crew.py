from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class DocumentIngestionCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.document_ingestion_preprocessing_agent(),
                self.agents.content_indexing_embedding_agent(),
                self.agents.knowledge_graph_builder_agent(),
                self.agents.database_query_agent(),
                self.agents.document_summary_agent(),
                self.agents.data_integrity_qa_ingestion_qa_agent()
            ],
            tasks=[
                self.tasks.ingest_and_preprocess_document_task(),
                self.tasks.index_and_embed_content_task(),
                self.tasks.build_knowledge_graph_task(),
                self.tasks.query_database_task(),
                self.tasks.summarize_document_task(),
                self.tasks.verify_data_integrity_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.data_integrity_qa_ingestion_qa_agent().llm,
            verbose=True
        )
