from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class TrialPreparationCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.exhibit_manager_agent(),
                self.agents.presentation_designer_agent(),
                self.agents.trial_script_agent(),
                self.agents.trial_logistics_agent(),
                self.agents.final_qa_moot_court_agent()
            ],
            tasks=[
                self.tasks.trial_preparation_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.final_qa_moot_court_agent().llm,
            verbose=True
        )
