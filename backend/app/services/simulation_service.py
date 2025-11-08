from __future__ import annotations
from typing import Any, Dict, List
from backend.app.services.llm_service import get_llm_service
import json

class SimulationService:
    """
    A service for running legal simulations, such as mock court, and checking procedural compliance.
    """

    def __init__(self):
        self.llm_service = get_llm_service()

    async def run_mock_court_simulation(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates a mock court scenario based on the provided scenario definition.

        :param scenario: A dictionary defining the simulation scenario (e.g., roles, facts, objectives).
        :return: A dictionary containing the simulation results and evaluation.
        """
        # Example scenario structure:
        # {
        #   "case_brief": "...",
        #   "roles": {"judge": "...", "opposing_counsel": "...", "witness": "..."},
        #   "agent_role": "prosecutor",
        #   "objectives": ["win the case", "prove X"],
        #   "initial_statement": "..."
        # }

        simulation_log = []
        current_state = {"turn": 0, "agent_statement": scenario.get("initial_statement", "")}

        # Simulate interaction turns
        for i in range(scenario.get("max_turns", 3)):
            current_state["turn"] = i + 1
            
            # Agent's turn (simulated by LLM based on objectives)
            agent_prompt = f"You are the {scenario['agent_role']}. The case brief is: {scenario['case_brief']}. Your objectives are: {', '.join(scenario['objectives'])}. Current simulation state: {json.dumps(current_state)}. What is your next statement or action?"
            agent_response = await self.llm_service.generate_text(agent_prompt)
            simulation_log.append({"role": scenario['agent_role'], "statement": agent_response})
            current_state["agent_statement"] = agent_response

            # Opposing counsel's turn
            opposing_counsel_prompt = f"You are the opposing counsel. The case brief is: {scenario['case_brief']}. The {scenario['agent_role']} just said: '{agent_response}'. How do you respond?"
            opposing_counsel_response = await self.llm_service.generate_text(opposing_counsel_prompt)
            simulation_log.append({"role": "opposing_counsel", "statement": opposing_counsel_response})
            current_state["opposing_counsel_statement"] = opposing_counsel_response

            # Judge's intervention (optional)
            if i % 2 == 0: # Every other turn, judge might intervene
                judge_prompt = f"You are the judge. The current exchange is: {agent_response} vs {opposing_counsel_response}. Do you have any questions or rulings?"
                judge_response = await self.llm_service.generate_text(judge_prompt)
                if "ruling" in judge_response.lower() or "question" in judge_response.lower():
                    simulation_log.append({"role": "judge", "statement": judge_response})
                    current_state["judge_statement"] = judge_response

        # Final evaluation by LLM
        evaluation_prompt = f"Based on the following mock court simulation log, evaluate if the {scenario['agent_role']} achieved its objectives: {', '.join(scenario['objectives'])}. Provide a detailed evaluation and a score out of 100.\n\nSimulation Log: {json.dumps(simulation_log, indent=2)}"
        final_evaluation = await self.llm_service.generate_text(evaluation_prompt)

        return {
            "simulation_log": simulation_log,
            "final_evaluation": final_evaluation,
            "status": "completed"
        }

    async def check_procedural_compliance(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Checks if a given legal action complies with established procedures.

        :param action: The legal action to check (e.g., "file motion to dismiss").
        :param context: Contextual information (e.g., "jurisdiction": "federal", "stage": "pre-trial").
        :return: A dictionary indicating compliance status and reasoning.
        """
        compliance_prompt = f"Evaluate if the legal action '{action}' is procedurally compliant given the following context: {json.dumps(context)}. Provide a 'compliant' status (true/false) and detailed reasoning."
        compliance_check = await self.llm_service.generate_text(compliance_prompt)
        
        # Attempt to parse LLM response for structured output
        try:
            parsed_response = json.loads(compliance_check)
            if "compliant" in parsed_response and "reasoning" in parsed_response:
                return parsed_response
        except json.JSONDecodeError:
            pass # LLM didn't return JSON, proceed with raw text

        return {"compliant": "unknown", "reasoning": compliance_check}
