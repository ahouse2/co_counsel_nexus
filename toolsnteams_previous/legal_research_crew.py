from crewai import Crew, Process
from agents import LegalDiscoveryAgents
from tasks import LegalDiscoveryTasks

class LegalResearchCrew:
    def __init__(self):
        self.agents = LegalDiscoveryAgents()
        self.tasks = LegalDiscoveryTasks()

    def crew(self):
        return Crew(
            agents=[
                self.agents.case_law_research_agent(),
                self.agents.statute_regulation_research_agent(),
                self.agents.procedure_court_rules_agent(),
                self.agents.evidence_law_expert_agent(),
                self.agents.legal_history_context_agent(),
                self.agents.research_coordinator_integrator_agent()
            ],
            tasks=[
                self.tasks.case_law_research_task(),
                self.tasks.statute_regulation_research_task(),
                self.tasks.procedure_rules_research_task(),
                self.tasks.evidence_law_research_task(),
                self.tasks.legal_history_research_task(),
                self.tasks.compile_research_report_task()
            ],
            process=Process.hierarchical,
            manager_llm=self.agents.research_coordinator_integrator_agent().llm,
            verbose=True
        )
