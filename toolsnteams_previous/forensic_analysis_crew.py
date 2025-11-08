from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class ForensicAnalysisCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.document_authenticity_analyst_agent(),
                self.agents.evidence_integrity_agent(),
                self.agents.forensic_media_analyst_agent(),
                self.agents.forensic_documents_qa_coordinator_agent(),
                self.agents.forensic_accountant_agent(),
                self.agents.data_analyst_agent(),
                self.agents.forensic_finance_qa_reviewer_agent()
            ],
            tasks=[
                self.tasks.forensic_analysis_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.forensic_documents_qa_coordinator_agent().llm,
            verbose=True
        )
