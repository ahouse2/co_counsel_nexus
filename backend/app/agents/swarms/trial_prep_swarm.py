"""
Trial Preparation Swarm - Autonomous trial prep with KG integration.

Agents:
1. MockTrialAgent - Simulates opposing arguments
2. JurySentimentAgent - Analyzes jury reactions
3. CrossExamAgent - Generates cross-examination questions
4. WitnessCredibilityAgent - Scores witness credibility
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
class TrialPrepResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]


class TrialPrepAgent:
    """Base class for trial prep agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> TrialPrepResult:
        raise NotImplementedError


class MockTrialAgent(TrialPrepAgent):
    """Agent 1: Simulates opposing counsel's arguments."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "MockTrialAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> TrialPrepResult:
        """Generate opposing counsel's likely arguments."""
        try:
            # Query KG for case weaknesses
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_WEAKNESS]->(w:Weakness)
            RETURN w.title as title, w.description as description, w.severity as severity
            LIMIT 10
            """
            weaknesses = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            
            case_theory = context.get("case_theory", "Not specified")
            weakness_text = "\n".join([
                f"- {w.get('title')}: {w.get('description')}"
                for w in (weaknesses or [])
            ]) or "No known weaknesses in graph"
            
            prompt = f"""You are opposing counsel. Build the strongest possible case against the plaintiff.

PLAINTIFF'S CASE THEORY:
{case_theory}

KNOWN WEAKNESSES:
{weakness_text}

Generate:
1. Opening statement attacks
2. Key arguments to undermine plaintiff's case
3. Cross-examination targets
4. Closing argument themes

Return JSON:
{{
    "opening_attacks": ["attack1", "attack2"],
    "key_arguments": [
        {{"argument": "...", "target": "which element this attacks", "strength": "high|medium|low"}}
    ],
    "cross_exam_targets": ["witness1", "witness2"],
    "closing_themes": ["theme1", "theme2"]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return TrialPrepResult(self.name, True, data)
            
            return TrialPrepResult(self.name, False, {"error": "Failed to parse mock trial"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return TrialPrepResult(self.name, False, {"error": str(e)})


class JurySentimentAgent(TrialPrepAgent):
    """Agent 2: Analyzes jury sentiment for arguments."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "JurySentimentAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> TrialPrepResult:
        """Predict jury reactions to key arguments."""
        try:
            arguments = context.get("arguments", [])
            jury_profile = context.get("jury_profile", {
                "demographics": "mixed",
                "education": "varied",
                "political_lean": "moderate"
            })
            
            if not arguments:
                arguments = ["The defendant's negligence directly caused the plaintiff's injuries."]
            
            prompt = f"""Predict jury reactions to these arguments.

JURY PROFILE:
{jury_profile}

ARGUMENTS:
{chr(10).join([f"{i+1}. {arg}" for i, arg in enumerate(arguments[:5])])}

For each argument, predict:
1. Receptiveness score (0.0-1.0)
2. Emotional reaction
3. Concerns
4. How to improve delivery

Return JSON:
{{
    "reactions": [
        {{
            "argument_index": 1,
            "receptiveness": 0.7,
            "reaction": "skeptical but interested",
            "concerns": ["concern1"],
            "improvements": ["improvement1"]
        }}
    ],
    "overall_strategy": "..."
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return TrialPrepResult(self.name, True, data)
            
            return TrialPrepResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return TrialPrepResult(self.name, False, {"error": str(e)})


class CrossExamAgent(TrialPrepAgent):
    """Agent 3: Generates cross-examination questions."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "CrossExamAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> TrialPrepResult:
        """Generate cross-exam questions from witness testimony."""
        try:
            # Query KG for witnesses
            query = """
            MATCH (w:Witness {case_id: $case_id})
            OPTIONAL MATCH (w)-[:GAVE_TESTIMONY]->(t:Testimony)
            RETURN w.name as name, w.role as role, 
                   collect(t.summary)[0] as testimony
            LIMIT 5
            """
            witnesses = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            
            all_questions = []
            for witness in (witnesses or []):
                if not witness.get("testimony"):
                    continue
                    
                prompt = f"""Generate cross-examination questions for this witness.

WITNESS: {witness.get('name')} ({witness.get('role')})
TESTIMONY: {witness.get('testimony', 'No recorded testimony')[:1000]}

Generate 5 tough questions to:
- Impeach credibility
- Highlight inconsistencies
- Expose bias

Return JSON:
{{
    "questions": [
        {{"question": "...", "objective": "...", "expected_answer": "..."}}
    ]
}}"""

                response = await self.llm_service.generate_text(prompt)
                import json, re
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    all_questions.append({
                        "witness": witness.get("name"),
                        "questions": data.get("questions", [])
                    })
            
            return TrialPrepResult(self.name, True, {"cross_exams": all_questions})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return TrialPrepResult(self.name, False, {"error": str(e)})


class WitnessCredibilityAgent(TrialPrepAgent):
    """Agent 4: Scores witness credibility from KG data."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "WitnessCredibilityAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> TrialPrepResult:
        """Score witness credibility."""
        try:
            query = """
            MATCH (w:Witness {case_id: $case_id})
            OPTIONAL MATCH (w)-[:GAVE_TESTIMONY]->(t:Testimony)
            OPTIONAL MATCH (w)-[:HAS_BIAS]->(b:Bias)
            RETURN w.name as name, w.role as role,
                   collect(t.summary) as testimonies,
                   collect(b.description) as biases
            """
            witnesses = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            
            scores = []
            for w in (witnesses or []):
                bias_count = len(w.get("biases", []))
                consistency = 1.0 - (bias_count * 0.1)
                scores.append({
                    "witness": w.get("name"),
                    "role": w.get("role"),
                    "credibility_score": max(0.0, min(1.0, consistency)),
                    "biases": w.get("biases", []),
                    "testimony_count": len(w.get("testimonies", []))
                })
            
            return TrialPrepResult(self.name, True, {"witness_scores": scores})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return TrialPrepResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TRIAL PREP SWARM
# ═══════════════════════════════════════════════════════════════════════════

class TrialPrepSwarm:
    """
    Swarm for autonomous trial preparation with KG integration.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.mock_trial = MockTrialAgent(self.llm_service, self.kg_service)
        self.jury_sentiment = JurySentimentAgent(self.llm_service, self.kg_service)
        self.cross_exam = CrossExamAgent(self.llm_service, self.kg_service)
        self.witness_cred = WitnessCredibilityAgent(self.llm_service, self.kg_service)
        
        logger.info("TrialPrepSwarm initialized with 4 agents")
    
    async def prepare_for_trial(self, case_id: str, case_theory: str = "") -> Dict[str, Any]:
        """Run complete trial preparation analysis."""
        context = {"case_id": case_id, "case_theory": case_theory}
        results = {}
        
        # Parallel execution of all agents
        logger.info(f"[TrialPrepSwarm] Starting parallel trial prep for case {case_id}")
        
        mock_task = self.mock_trial.process(case_id, context)
        jury_task = self.jury_sentiment.process(case_id, context)
        cross_task = self.cross_exam.process(case_id, context)
        cred_task = self.witness_cred.process(case_id, context)
        
        mock_result, jury_result, cross_result, cred_result = await asyncio.gather(
            mock_task, jury_task, cross_task, cred_task
        )
        
        results["mock_trial"] = mock_result.output
        results["jury_sentiment"] = jury_result.output
        results["cross_examination"] = cross_result.output
        results["witness_credibility"] = cred_result.output
        
        logger.info(f"[TrialPrepSwarm] Trial prep complete for case {case_id}")
        
        return {"case_id": case_id, "success": True, "results": results}


# Factory
_trial_prep_swarm: Optional[TrialPrepSwarm] = None

def get_trial_prep_swarm() -> TrialPrepSwarm:
    global _trial_prep_swarm
    if _trial_prep_swarm is None:
        _trial_prep_swarm = TrialPrepSwarm()
    return _trial_prep_swarm
