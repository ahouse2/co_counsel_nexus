from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class SubpoenaCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.subpoena_planning_agent(),
                self.agents.subpoena_drafting_agent(),
                self.agents.service_follow_up_agent(),
                self.agents.third_party_data_ingestion_agent(),
                self.agents.subpoena_compliance_objection_handler_agent(),
                self.agents.qa_logging_agent()
            ],
            tasks=[
                self.tasks.subpoena_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.qa_logging_agent().llm,
            verbose=True
        )
