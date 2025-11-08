from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class TimelineConstructionCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.timeline_builder_agent(),
                self.agents.timeline_analyst_agent(),
                self.agents.timeline_visualization_agent(),
                self.agents.timeline_qa_agent()
            ],
            tasks=[
                self.tasks.timeline_construction_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.timeline_analyst_agent().llm,
            verbose=True
        )
