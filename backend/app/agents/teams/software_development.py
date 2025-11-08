from __future__ import annotations
from typing import List, Dict, Any

# Assuming AgentDefinition and AgentTool are defined elsewhere in the framework
# For now, we'll use the simple classes defined in qa_agents.py
from backend.app.agents.definitions.qa_agents import AgentDefinition, AgentTool
from backend.app.agents.definitions.qa_agents import validator_qa_agent, critic_qa_agent, refinement_qa_agent

# Import the TestingHarnessService
from backend.app.testing_harness.harness import TestingHarnessService

# Instantiate the TestingHarnessService
testing_harness_service = TestingHarnessService()

# Placeholder Tools for Software Development
from backend.app.services.llm_service import get_llm_service

class CodeGenerationTool(AgentTool):
    def __init__(self):
        super().__init__("CodeGenerationTool", "Generates code based on specifications.", self.generate_code)
        self.llm_service = get_llm_service()
    async def generate_code(self, requirements: str) -> Dict[str, Any]:
        prompt = f"Generate code based on the following requirements:\n\nRequirements: {requirements}"
        generated_code = await self.llm_service.generate_text(prompt)
        return {"generated_code": generated_code}

class CodeModificationTool(AgentTool):
    def __init__(self):
        super().__init__("CodeModificationTool", "Modifies existing code to fix bugs or add features.", self.modify_code)
        self.llm_service = get_llm_service()
    async def modify_code(self, code: str, instructions: str) -> Dict[str, Any]:
        prompt = f"Modify the following code based on these instructions:\n\nInstructions: {instructions}\n\nCode:\n{code}"
        modified_code = await self.llm_service.generate_text(prompt)
        return {"modified_code": modified_code}

class TestExecutionTool(AgentTool):
    def __init__(self):
        super().__init__("TestExecutionTool", "Executes test scenarios using the Agentic Testing Harness.", self.execute_tests)
    async def execute_tests(self, scenario_name: str) -> Dict[str, Any]:
        # This tool directly uses the TestingHarnessService
        scenario = testing_harness_service.load_scenario(scenario_name)
        agent_result = await testing_harness_service.run_test(scenario)
        evaluation_result = testing_harness_service.evaluate_output(agent_result, scenario.get("expected_output", {}))
        return {"agent_result": agent_result, "evaluation_result": evaluation_result}


# Agent Definitions for Software Development Crew
# Primary Agents
dev_team_lead_agent = AgentDefinition(
    name="DevTeamLead",
    role="Development Team Lead Agent",
    description="Coordinates and supervises the software development team.",
    tools=[] # Primarily delegates
)

software_architect_agent = AgentDefinition(
    name="SoftwareArchitect",
    role="Software Architect",
    description="Designs the overall software architecture and technical solutions.",
    tools=[] # Primarily designs
)

front_end_dev_ui_agent = AgentDefinition(
    name="FrontEndDevUIAgent",
    role="Front-End Developer (UI)",
    description="Develops user interfaces and fixes front-end related issues.",
    tools=[CodeGenerationTool(), CodeModificationTool()]
)

back_end_dev_toolsmith_agent = AgentDefinition(
    name="BackEndDevToolsmithAgent",
    role="Back-End Developer (Toolsmith)",
    description="Develops backend tools, APIs, and fixes backend related issues.",
    tools=[CodeGenerationTool(), CodeModificationTool()]
)

qa_test_engineer_agent = AgentDefinition(
    name="QATestEngineer",
    role="QA Test Engineer Agent",
    description="Performs quality assurance, testing, and logging for software features.",
    tools=[TestExecutionTool()]
)

# Backup Agents (for redundancy)
backup_front_end_dev_ui_agent = AgentDefinition(
    name="BackupFrontEndDevUIAgent",
    role="Backup Front-End Developer (UI)",
    description="Backup agent for developing user interfaces and fixing front-end related issues.",
    tools=[CodeGenerationTool(), CodeModificationTool()]
)

backup_back_end_dev_toolsmith_agent = AgentDefinition(
    name="BackupBackEndDevToolsmithAgent",
    role="Backup Back-End Developer (Toolsmith)",
    description="Backup agent for developing backend tools, APIs, and fixing backend related issues.",
    tools=[CodeGenerationTool(), CodeModificationTool()]
)

backup_qa_test_engineer_agent = AgentDefinition(
    name="BackupQATestEngineer",
    role="Backup QA Test Engineer Agent",
    description="Backup agent for performing quality assurance, testing, and logging.",
    tools=[TestExecutionTool()]
)


def build_software_development_team(tools: List[AgentTool]) -> Dict[str, Any]:
    """
    Builds the Software Development Team with redundancy and a 3-step QA process.
    """
    all_agents = [
        dev_team_lead_agent,
        software_architect_agent,
        front_end_dev_ui_agent,
        backup_front_end_dev_ui_agent,
        back_end_dev_toolsmith_agent,
        backup_back_end_dev_toolsmith_agent,
        qa_test_engineer_agent,
        backup_qa_test_engineer_agent,
        validator_qa_agent,
        critic_qa_agent,
        refinement_qa_agent
    ]

    # Define the workflow (simplified representation)
    workflow = {
        "start": dev_team_lead_agent.name,
        "tasks": [
            {
                "agent": dev_team_lead_agent.name,
                "action": "delegate_development_tasks",
                "target": [
                    front_end_dev_ui_agent.name,
                    back_end_dev_toolsmith_agent.name
                ]
            },
            {
                "agent": front_end_dev_ui_agent.name,
                "action": "develop_feature",
                "target": qa_test_engineer_agent.name
            },
            {
                "agent": back_end_dev_toolsmith_agent.name,
                "action": "develop_tool",
                "target": qa_test_engineer_agent.name
            },
            {
                "agent": qa_test_engineer_agent.name,
                "action": "run_tests_and_qa",
                "target": [validator_qa_agent.name, critic_qa_agent.name, refinement_qa_agent.name]
            }
        ]
    }

    return {
        "name": "SoftwareDevelopmentCrew",
        "agents": {agent.name: agent for agent in all_agents},
        "workflow": workflow,
        "tools": {tool.name: tool for tool in tools} # Pass relevant tools
    }