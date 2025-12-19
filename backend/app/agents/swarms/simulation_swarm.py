"""
Simulation Swarm - Scenario simulation and outcome prediction with KG integration.

Agents:
1. ScenarioBuilderAgent - Creates simulation scenarios from case facts
2. OutcomePredictor - Predicts likely outcomes
3. SettlementAnalyzer - Analyzes settlement values
4. RiskAssessorAgent - Assesses litigation risks
5. StrategyRecommenderAgent - Recommends strategies based on simulations
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.services.llm_service import get_llm_service, LLMService
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService

logger = logging.getLogger(__name__)


@dataclass
class SimulationAgentResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]


class SimulationAgent:
    """Base class for simulation agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def simulate(self, case_id: str, context: Dict[str, Any]) -> SimulationAgentResult:
        raise NotImplementedError


class ScenarioBuilderAgent(SimulationAgent):
    """Agent 1: Creates simulation scenarios from case facts."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ScenarioBuilderAgent")
    
    async def simulate(self, case_id: str, context: Dict[str, Any]) -> SimulationAgentResult:
        try:
            # Get case facts from KG
            facts_query = """
            MATCH (c:Case {id: $case_id})-[:HAS_FACT]->(f:Fact)
            RETURN f.description as fact, f.category as category
            LIMIT 15
            """
            facts = await self.kg_service.run_cypher_query(facts_query, {"case_id": case_id})
            
            # Get causes of action
            causes_query = """
            MATCH (c:Case {id: $case_id})-[:HAS_CAUSE]->(coa:CauseOfAction)
            RETURN coa.name as cause, coa.support_score as support
            """
            causes = await self.kg_service.run_cypher_query(causes_query, {"case_id": case_id})
            
            prompt = f"""Build simulation scenarios for this case.

FACTS:
{chr(10).join([f"- {f.get('fact', '')}" for f in (facts or [])[:10]])}

CAUSES OF ACTION:
{chr(10).join([f"- {c.get('cause', '')} (support: {c.get('support', 0):.0%})" for c in (causes or [])[:5]])}

Create 3 scenarios:
1. Best case (plaintiff wins on all claims)
2. Most likely (mixed outcome)
3. Worst case (defendant prevails)

Return JSON:
{{
    "scenarios": [
        {{
            "name": "Best Case",
            "probability": 0.0-1.0,
            "outcome_description": "...",
            "damages_range": {{"low": 0, "high": 0}},
            "key_assumptions": ["..."]
        }}
    ]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return SimulationAgentResult(self.name, True, data)
            
            return SimulationAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return SimulationAgentResult(self.name, False, {"error": str(e)})


class OutcomePredictorAgent(SimulationAgent):
    """Agent 2: Predicts likely outcomes using case data."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "OutcomePredictorAgent")
    
    async def simulate(self, case_id: str, context: Dict[str, Any]) -> SimulationAgentResult:
        try:
            scenarios = context.get("scenarios", [])
            
            # Query similar cases from KG
            similar_query = """
            MATCH (c:Case {id: $case_id})-[:SIMILAR_TO]->(similar:Case)
            RETURN similar.outcome as outcome, similar.damages as damages
            LIMIT 5
            """
            similar = await self.kg_service.run_cypher_query(similar_query, {"case_id": case_id})
            
            prompt = f"""Predict case outcomes based on scenarios and similar cases.

SCENARIOS:
{chr(10).join([f"- {s.get('name', '')}: {s.get('probability', 0):.0%}" for s in scenarios[:3]])}

SIMILAR CASE OUTCOMES:
{chr(10).join([f"- {s.get('outcome', '')}: ${s.get('damages', 0):,.0f}" for s in (similar or [])[:5]]) or 'No similar cases in database'}

Return JSON:
{{
    "predicted_outcome": "plaintiff_win|defendant_win|settlement|mixed",
    "confidence": 0.0-1.0,
    "expected_damages": 0,
    "key_factors": ["factor1", "factor2"],
    "verdict_probability": {{"plaintiff": 0.5, "defendant": 0.5}}
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return SimulationAgentResult(self.name, True, data)
            
            return SimulationAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return SimulationAgentResult(self.name, False, {"error": str(e)})


class SettlementAnalyzerAgent(SimulationAgent):
    """Agent 3: Analyzes optimal settlement values."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "SettlementAnalyzerAgent")
    
    async def simulate(self, case_id: str, context: Dict[str, Any]) -> SimulationAgentResult:
        try:
            prediction = context.get("prediction", {})
            scenarios = context.get("scenarios", [])
            
            expected_damages = prediction.get("expected_damages", 0)
            plaintiff_prob = prediction.get("verdict_probability", {}).get("plaintiff", 0.5)
            
            # Calculate settlement range
            # Expected value = probability * damages
            expected_value = expected_damages * plaintiff_prob
            
            # Settlement range (typically 60-80% of expected value for plaintiff)
            settlement_low = expected_value * 0.5
            settlement_high = expected_value * 0.9
            
            return SimulationAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "expected_value": expected_value,
                    "settlement_range": {"low": settlement_low, "high": settlement_high},
                    "optimal_settlement": expected_value * 0.7,
                    "walk_away_point": settlement_low,
                    "recommendation": "settle" if expected_value < 100000 else "litigate"
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return SimulationAgentResult(self.name, False, {"error": str(e)})


class RiskAssessorAgent(SimulationAgent):
    """Agent 4: Assesses litigation risks."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "RiskAssessorAgent")
    
    async def simulate(self, case_id: str, context: Dict[str, Any]) -> SimulationAgentResult:
        try:
            # Query weaknesses from KG
            weakness_query = """
            MATCH (c:Case {id: $case_id})-[:HAS_WEAKNESS]->(w:Weakness)
            RETURN w.title as title, w.severity as severity
            """
            weaknesses = await self.kg_service.run_cypher_query(weakness_query, {"case_id": case_id})
            
            # Calculate risk score
            risk_weights = {"critical": 0.4, "high": 0.25, "medium": 0.15, "low": 0.05}
            total_risk = sum([
                risk_weights.get(w.get("severity", "low"), 0.05)
                for w in (weaknesses or [])
            ])
            risk_score = min(1.0, total_risk)
            
            return SimulationAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "risk_score": risk_score,
                    "risk_level": "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low",
                    "weakness_count": len(weaknesses or []),
                    "top_risks": [w.get("title") for w in (weaknesses or [])[:3]]
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return SimulationAgentResult(self.name, False, {"error": str(e)})


class StrategyRecommenderAgent(SimulationAgent):
    """Agent 5: Recommends strategies based on simulations."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "StrategyRecommenderAgent")
    
    async def simulate(self, case_id: str, context: Dict[str, Any]) -> SimulationAgentResult:
        try:
            prediction = context.get("prediction", {})
            settlement = context.get("settlement", {})
            risk = context.get("risk", {})
            
            prompt = f"""Recommend litigation strategy based on simulation results.

OUTCOME PREDICTION: {prediction.get('predicted_outcome', 'unknown')} ({prediction.get('confidence', 0):.0%} confidence)
EXPECTED DAMAGES: ${prediction.get('expected_damages', 0):,.0f}
RISK LEVEL: {risk.get('risk_level', 'unknown')} ({risk.get('risk_score', 0):.0%})
OPTIMAL SETTLEMENT: ${settlement.get('optimal_settlement', 0):,.0f}

Return JSON:
{{
    "recommended_strategy": "aggressive_litigation|measured_litigation|early_settlement|mediation",
    "rationale": "...",
    "action_items": ["action1", "action2"],
    "timeline_recommendation": "...",
    "resource_allocation": {{"discovery": 0.3, "motions": 0.2, "trial_prep": 0.5}}
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return SimulationAgentResult(self.name, True, data)
            
            return SimulationAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return SimulationAgentResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# SIMULATION SWARM
# ═══════════════════════════════════════════════════════════════════════════

class SimulationSwarm:
    """
    Full simulation swarm with 5 agents.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.scenario_builder = ScenarioBuilderAgent(self.llm_service, self.kg_service)
        self.outcome_predictor = OutcomePredictorAgent(self.llm_service, self.kg_service)
        self.settlement_analyzer = SettlementAnalyzerAgent(self.llm_service, self.kg_service)
        self.risk_assessor = RiskAssessorAgent(self.llm_service, self.kg_service)
        self.strategy_recommender = StrategyRecommenderAgent(self.llm_service, self.kg_service)
        
        logger.info("SimulationSwarm initialized with 5 agents")
    
    async def run_simulation(self, case_id: str) -> Dict[str, Any]:
        """Run full case simulation."""
        context = {"case_id": case_id}
        
        # Stage 1: Build scenarios
        logger.info(f"[SimulationSwarm] Building scenarios for case {case_id}")
        scenario_result = await self.scenario_builder.simulate(case_id, context)
        context["scenarios"] = scenario_result.output.get("scenarios", [])
        
        # Stage 2: Parallel predictions and risk assessment
        logger.info(f"[SimulationSwarm] Running predictions and risk assessment")
        predict_task = self.outcome_predictor.simulate(case_id, context)
        risk_task = self.risk_assessor.simulate(case_id, context)
        
        predict_result, risk_result = await asyncio.gather(predict_task, risk_task)
        context["prediction"] = predict_result.output
        context["risk"] = risk_result.output
        
        # Stage 3: Settlement analysis
        logger.info(f"[SimulationSwarm] Analyzing settlement options")
        settlement_result = await self.settlement_analyzer.simulate(case_id, context)
        context["settlement"] = settlement_result.output
        
        # Stage 4: Strategy recommendation
        logger.info(f"[SimulationSwarm] Generating strategy recommendations")
        strategy_result = await self.strategy_recommender.simulate(case_id, context)
        
        # Store simulation in KG
        store_query = """
        MERGE (s:Simulation {case_id: $case_id})
        SET s.outcome = $outcome,
            s.damages = $damages,
            s.strategy = $strategy,
            s.run_at = datetime()
        """
        await self.kg_service.run_cypher_query(store_query, {
            "case_id": case_id,
            "outcome": predict_result.output.get("predicted_outcome", "unknown"),
            "damages": predict_result.output.get("expected_damages", 0),
            "strategy": strategy_result.output.get("recommended_strategy", "unknown")
        })
        
        return {
            "case_id": case_id,
            "scenarios": scenario_result.output,
            "prediction": predict_result.output,
            "risk": risk_result.output,
            "settlement": settlement_result.output,
            "strategy": strategy_result.output
        }


# Factory
_simulation_swarm: Optional[SimulationSwarm] = None

def get_simulation_swarm() -> SimulationSwarm:
    global _simulation_swarm
    if _simulation_swarm is None:
        _simulation_swarm = SimulationSwarm()
    return _simulation_swarm
