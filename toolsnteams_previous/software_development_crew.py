from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class SoftwareDevelopmentCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.software_architect_team_lead_agent(),
                self.agents.front_end_developer_ui_agent(),
                self.agents.back_end_developer_toolsmith_agent(),
                self.agents.qa_test_engineer_agent()
            ],
            tasks=[
                self.tasks.design_new_feature_task(),
                self.tasks.implement_ui_improvement_task(),
                self.tasks.build_backend_tool_task(),
                self.tasks.test_new_feature_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.software_architect_team_lead_agent().llm,
            verbose=True
        )
