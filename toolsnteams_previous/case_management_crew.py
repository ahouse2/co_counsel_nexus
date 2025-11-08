from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class CaseManagementCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.case_calendar_agent(),
                self.agents.task_tracking_agent(),
                self.agents.reminder_notification_agent(),
                self.agents.docket_monitor_agent(),
                self.agents.case_manager_agent()
            ],
            tasks=[
                self.tasks.case_management_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.case_manager_agent().llm,
            verbose=True
        )
