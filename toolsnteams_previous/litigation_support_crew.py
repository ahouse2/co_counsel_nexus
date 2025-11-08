from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class LitigationSupportCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.lead_counsel_strategist_agent(),
                self.agents.motion_drafting_agent(),
                self.agents.litigation_training_coach_agent(),
                self.agents.legal_strategy_reviewer_senior_counsel_agent()
            ],
            tasks=[
                self.tasks.litigation_support_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.lead_counsel_strategist_agent().llm,
            verbose=True
        )
