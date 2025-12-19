from __future__ import annotations
from typing import Any, Dict, List, Optional
from backend.app.services.llm_service import get_llm_service
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService
import json

class SimulationService:
    """
    A service for running legal simulations, such as mock court, and checking procedural compliance.
    Enhanced with KG integration.
    """
    def __init__(self, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()

    async def run_mock_court_simulation(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates a mock court scenario based on the provided scenario definition.
        """
        from backend.app.agents.opposing_counsel import OpposingCounselAgent
        from backend.app.agents.context import AgentContext
        from backend.app.services.jury_sentiment import get_jury_sentiment_service, JurorPersona
        
        opposing_counsel = OpposingCounselAgent(self.llm_service)
        jury_service = get_jury_sentiment_service()
        
        # Default Jurors if not provided
        jurors = [
            JurorPersona("j1", "Juror 1", "College Educated, 30s", "Teacher", "Liberal", "Empathetic"),
            JurorPersona("j2", "Juror 2", "High School, 50s", "Mechanic", "Conservative", "Skeptical"),
            JurorPersona("j3", "Juror 3", "Post-Grad, 40s", "Accountant", "Moderate", "Logical"),
        ]
        
        simulation_log = []
        current_state = {"turn": 0, "agent_statement": scenario.get("initial_statement", "")}
        
        # Simulate interaction turns
        for i in range(scenario.get("max_turns", 3)):
            current_state["turn"] = i + 1
            
            # Agent's turn (simulated by LLM based on objectives)
            agent_prompt = f"You are the {scenario['agent_role']}. The case brief is: {scenario['case_brief']}. Your objectives are: {', '.join(scenario['objectives'])}. Current simulation state: {json.dumps(current_state)}. What is your next statement or action?"
            agent_response = await self.llm_service.generate_text(agent_prompt)
            
            # Analyze Agent Statement with Jury
            agent_jury_reactions = await jury_service.simulate_individual_jurors(agent_response, jurors)
            
            simulation_log.append({
                "role": scenario['agent_role'], 
                "statement": agent_response,
                "jury_reactions": [r.__dict__ for r in agent_jury_reactions]
            })
            current_state["agent_statement"] = agent_response
            
            # Check for Objection
            # We create a dummy context for now
            context = AgentContext(
                case_id="simulation",
                question=agent_response,
                top_k=5,
                actor={"id": "simulation", "roles": ["user"]},
                memory=None, # type: ignore
                telemetry={}
            )
            
            objection = opposing_counsel.check_objection(agent_response, context)
            
            if objection.is_objection and objection.likelihood_of_success > 0.6:
                simulation_log.append({
                    "role": "opposing_counsel",
                    "type": "objection",
                    "content": f"Objection! {objection.basis}. {objection.explanation}",
                    "data": objection.__dict__
                })
                
                # Simulate Judge Ruling
                judge_prompt = f"You are the judge. Opposing counsel objected: '{objection.basis}: {objection.explanation}'. The statement was: '{agent_response}'. Rule on the objection (Sustained/Overruled) and briefly explain."
                judge_ruling = await self.llm_service.generate_text(judge_prompt)
                
                simulation_log.append({
                    "role": "judge",
                    "type": "ruling",
                    "content": judge_ruling
                })
                
                if "sustained" in judge_ruling.lower():
                    # If sustained, maybe agent needs to rephrase? For now, we just continue but note it.
                    current_state["last_ruling"] = "Sustained"
                    continue # Skip opposing counsel's normal response if objection sustained (simplified flow)
            
            # Opposing counsel's turn using the specialized agent
            # Use generate_counter_arguments to formulate a response strategy
            counter_args = opposing_counsel.generate_counter_arguments(
                argument=agent_response,
                context=context,
                evidence_context=scenario.get("case_brief", "")
            )
            
            # Synthesize the counter-arguments into a spoken response
            strategy = "\n".join([f"- {ca.counter_point} (Risk: {ca.risk_score})" for ca in counter_args])
            opposing_counsel_prompt = f"""
            You are the opposing counsel. 
            Based on the following counter-argument strategy, formulate your response to the court.
            
            STRATEGY:
            {strategy}
            
            PREVIOUS STATEMENT:
            "{agent_response}"
            
            Respond as if you are speaking in court.
            """
            opposing_counsel_response = await self.llm_service.generate_text(opposing_counsel_prompt)
            
            # Analyze Opposing Counsel Statement with Jury
            oc_jury_reactions = await jury_service.simulate_individual_jurors(opposing_counsel_response, jurors)
            
            simulation_log.append({
                "role": "opposing_counsel", 
                "statement": opposing_counsel_response,
                "internal_strategy": [ca.__dict__ for ca in counter_args],
                "jury_reactions": [r.__dict__ for r in oc_jury_reactions]
            })
            current_state["opposing_counsel_statement"] = opposing_counsel_response
            
            # Judge's intervention (optional)
            if i % 2 == 0: # Every other turn, judge might intervene
                judge_prompt = f"You are the judge. The current exchange is: {agent_response} vs {opposing_counsel_response}. Do you have any questions or rulings?"
                judge_response = await self.llm_service.generate_text(judge_prompt)
                if "ruling" in judge_response.lower() or "question" in judge_response.lower():
                    simulation_log.append({"role": "judge", "statement": judge_response})
                    current_state["judge_statement"] = judge_response
                    
        # Final evaluation by LLM
        evaluation_prompt = f"Based on the following mock court simulation log, evaluate if the {scenario['agent_role']} achieved its objectives: {', '.join(scenario['objectives'])}. Provide a detailed evaluation and a score out of 100.\n\nSimulation Log: {json.dumps(simulation_log, indent=2, default=str)}"
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

    async def chat_with_juror(self, juror_profile: Dict[str, Any], chat_history: List[Dict[str, str]], user_message: str, case_context: str) -> str:
        """
        Simulates a chat with a specific juror persona.
        """
        system_prompt = f"""
You are a virtual juror in a mock trial.
Your profile is:
- Education: {juror_profile.get('education', 'Unknown')}
- Age: {juror_profile.get('age', 'Unknown')}
- Bias/Leanings: {juror_profile.get('bias', 'Neutral')}
- Occupation: {juror_profile.get('occupation', 'Unknown')}

CASE CONTEXT:
{case_context}

INSTRUCTIONS:
1. Adopt the persona described above completely. Use appropriate vocabulary and tone.
2. React to the user's arguments based on your profile and bias.
3. Be honest about your impressions. If an argument is confusing or unconvincing, say so.
4. Keep responses relatively concise (1-3 sentences) unless asked to elaborate.
5. Do NOT break character. You are the juror.

CHAT HISTORY:
"""
        for msg in chat_history[-5:]: # Keep last 5 turns for context
            system_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
            
        system_prompt += f"USER (Attorney): {user_message}\nJUROR:"
        
        response = await self.llm_service.generate_text(system_prompt)
        return response.strip()
