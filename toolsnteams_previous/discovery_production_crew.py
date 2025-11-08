from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class DiscoveryProductionCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.discovery_request_analyzer_agent(),
                self.agents.document_retrieval_agent(),
                self.agents.redaction_privilege_agent(),
                self.agents.response_drafting_agent(),
                self.agents.production_assembly_agent(),
                self.agents.discovery_compliance_qa_agent()
            ],
            tasks=[
                self.tasks.discovery_production_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.discovery_compliance_qa_agent().llm,
            verbose=True
        )
