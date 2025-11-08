from crewai import Crew, Process

class LegalAnalysisCrew:
    def __init__(self):
        pass

    def crew(self):
        return Crew(
            agents=[],
            tasks=[],
            process=Process.sequential,
            verbose=True
        )
