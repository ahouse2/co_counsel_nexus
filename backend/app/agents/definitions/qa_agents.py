
from __future__ import annotations
from typing import List, Dict, Any
import jsonschema

# Assuming AgentDefinition and AgentTool are defined elsewhere in the framework
# For now, we'll use a simple class to represent them.
class AgentTool:
    def __init__(self, name: str, description: str, func: Any):
        self.name = name
        self.description = description
        self.func = func

class AgentDefinition:
    def __init__(self, name: str, role: str, description: str, tools: List[AgentTool] = None, delegates: List[str] = None):
        self.name = name
        self.role = role
        self.description = description
        self.tools = tools if tools is not None else []
        self.delegates = delegates if delegates is not None else []

# Import LLM service
from backend.app.services.llm_service import get_llm_service

class ValidatorQATool(AgentTool):
    def __init__(self):
        super().__init__("ValidatorQATool", "Validates output against predefined schemas or rules.", self.validate)
    async def validate(self, output: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        try:
            jsonschema.validate(instance=output, schema=schema)
            return {"validation_status": "pass", "details": "Output conforms to schema."}
        except jsonschema.exceptions.ValidationError as e:
            return {"validation_status": "fail", "details": str(e)}

class CriticQATool(AgentTool):
    def __init__(self):
        super().__init__("CriticQATool", "Critiques output for quality, accuracy, and completeness.", self.critique)
        self.llm_service = get_llm_service()
    async def critique(self, output: Dict[str, Any], criteria: List[str]) -> Dict[str, Any]:
        prompt = f"Critique the following output based on these criteria: {', '.join(criteria)}.\n\nOutput: {json.dumps(output, indent=2)}"
        feedback = await self.llm_service.generate_text(prompt)
        return {"critique_status": "complete", "feedback": feedback}

class RefinementQATool(AgentTool):
    def __init__(self):
        super().__init__("RefinementQATool", "Suggests specific improvements and refines output.", self.refine)
        self.llm_service = get_llm_service()
    async def refine(self, output: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        prompt = f"Refine the following output based on the provided feedback.\n\nOriginal Output: {json.dumps(output, indent=2)}\n\nFeedback: {feedback}"
        refined_output = await self.llm_service.generate_text(prompt)
        return {"refinement_status": "complete", "refined_output": refined_output}


# Define the common QA agents
validator_qa_agent = AgentDefinition(
    name="ValidatorQA",
    role="Output Validator",
    description="Validates agent output against predefined schemas, formats, and compliance rules.",
    tools=[ValidatorQATool()]
)

critic_qa_agent = AgentDefinition(
    name="CriticQA",
    role="Output Critic",
    description="Critically evaluates the quality, accuracy, and completeness of agent-generated content.",
    tools=[CriticQATool()]
)

refinement_qa_agent = AgentDefinition(
    name="RefinementQA",
    role="Output Refiner",
    description="Suggests specific improvements and refines agent output based on feedback from the CriticQA.",
    tools=[RefinementQATool()]
)
