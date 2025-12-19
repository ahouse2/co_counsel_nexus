"""Jury sentiment analysis service for predicting jury reactions to arguments and evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..services.llm_service import LLMService, get_llm_service
from ..services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService


@dataclass
class SentimentAnalysis:
    """Sentiment analysis result for an argument."""
    text: str
    overall_score: float  # 0.0-1.0, higher = more persuasive
    emotional_tone: str  # "confident", "defensive", "aggressive", etc.
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


@dataclass
class JuryResponse:
    """Simulated jury response to an argument."""
    jury_profile: Dict[str, Any]
    receptiveness_score: float  # 0.0-1.0
    predicted_reactions: List[str]
    concerns: List[str]
    resonance_factors: Dict[str, float]


@dataclass
class CredibilityScore:
    """Witness credibility assessment."""
    witness_id: str
    testimony: str
    score: float  # 0.0-1.0
    credibility_factors: Dict[str, Any]
    red_flags: List[str]
    strengths: List[str]


@dataclass
class JurorPersona:
    id: str
    name: str
    demographics: str
    occupation: str
    bias: str
    temperament: str

@dataclass
class IndividualJurorReaction:
    juror_id: str
    sentiment_score: float # 0.0-1.0
    reaction: str # "nods", "frowns", "looks skeptical"
    internal_thought: str

class JurySentimentService:
    """
    Service for analyzing jury sentiment and predicting reactions.
    Enhanced with KG integration to query party/witness data and store analysis results.
    """

    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None) -> None:
        self.llm_service = llm_service or get_llm_service()
        # KG Integration: Query graph for parties, witnesses, and prior testimony
        self.kg_service = kg_service or get_knowledge_graph_service()

    async def simulate_individual_jurors(
        self, argument: str, jurors: List[JurorPersona]
    ) -> List[IndividualJurorReaction]:
        """Simulate reactions for specific individual jurors."""
        
        juror_descriptions = "\n".join([
            f"- ID: {j.id}, Name: {j.name}, {j.demographics}, {j.occupation}, Bias: {j.bias}, Temperament: {j.temperament}"
            for j in jurors
        ])

        prompt = f"""
        Simulate the individual reactions of the following jurors to the legal argument provided.

        ARGUMENT:
        {argument}

        JURORS:
        {juror_descriptions}

        For EACH juror, determine:
        1. Sentiment Score (0.0 = Hates it, 1.0 = Loves it)
        2. Visible Reaction (e.g., "nods in agreement", "crosses arms", "looks confused")
        3. Internal Thought (one short sentence)

        Return JSON:
        {{
            "reactions": [
                {{
                    "juror_id": "id",
                    "sentiment_score": 0.5,
                    "reaction": "description",
                    "internal_thought": "thought"
                }}
            ]
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                results = []
                for r in data.get("reactions", []):
                    results.append(IndividualJurorReaction(
                        juror_id=r.get("juror_id"),
                        sentiment_score=float(r.get("sentiment_score", 0.5)),
                        reaction=r.get("reaction", "neutral"),
                        internal_thought=r.get("internal_thought", "")
                    ))
                return results
        except Exception as e:
            print(f"Error simulating individual jurors: {e}")
            # Fallback
            return [
                IndividualJurorReaction(j.id, 0.5, "neutral", "listening") 
                for j in jurors
            ]

    async def analyze_argument_sentiment(self, text: str) -> SentimentAnalysis:
        """Analyze persuasiveness and emotional tone of an argument.
        
        Args:
            text: Argument text to analyze
            
        Returns:
            Sentiment analysis with scores and recommendations
        """
        prompt = f"""
        Analyze this legal argument for persuasiveness and emotional impact.
        
        ARGUMENT:
        {text}
        
        Evaluate:
        1. Overall persuasiveness (0.0-1.0)
        2. Emotional tone (confident, defensive, aggressive, empathetic, etc.)
        3. Strengths (what works well)
        4. Weaknesses (what could be improved)
        5. Specific recommendations for improvement
        
        Return JSON:
        {{
            "overall_score": 0.0-1.0,
            "emotional_tone": "description",
            "strengths": ["strength 1", "strength 2"],
            "weaknesses": ["weakness 1", "weakness 2"],
            "recommendations": ["recommendation 1", "recommendation 2"]
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return SentimentAnalysis(
                    text=text,
                    overall_score=float(data.get("overall_score", 0.5)),
                    emotional_tone=data.get("emotional_tone", "neutral"),
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    recommendations=data.get("recommendations", []),
                )
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")

        return SentimentAnalysis(
            text=text,
            overall_score=0.5,
            emotional_tone="neutral",
            strengths=[],
            weaknesses=["Analysis failed"],
            recommendations=["Retry analysis"],
        )

    async def simulate_jury_response(
        self,
        argument: str,
        jury_profile: Dict[str, Any],
    ) -> JuryResponse:
        """Simulate how a jury with specific demographics might respond.
        
        Args:
            argument: Argument text
            jury_profile: Demographics (age, education, political leanings, etc.)
            
        Returns:
            Predicted jury response
        """
        profile_str = "\n".join([f"- {k}: {v}" for k, v in jury_profile.items()])
        
        prompt = f"""
        Simulate how a jury with this profile would respond to the argument.
        
        JURY PROFILE:
        {profile_str}
        
        ARGUMENT:
        {argument}
        
        Predict:
        1. Receptiveness score (0.0-1.0, how well it resonates)
        2. Likely reactions (emotional and logical)
        3. Concerns they might have
        4. Factors that increase/decrease resonance
        
        Return JSON:
        {{
            "receptiveness_score": 0.0-1.0,
            "predicted_reactions": ["reaction 1", "reaction 2"],
            "concerns": ["concern 1", "concern 2"],
            "resonance_factors": {{
                "clarity": 0.0-1.0,
                "relatability": 0.0-1.0,
                "credibility": 0.0-1.0,
                "emotional_appeal": 0.0-1.0
            }}
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return JuryResponse(
                    jury_profile=jury_profile,
                    receptiveness_score=float(data.get("receptiveness_score", 0.5)),
                    predicted_reactions=data.get("predicted_reactions", []),
                    concerns=data.get("concerns", []),
                    resonance_factors=data.get("resonance_factors", {}),
                )
        except Exception as e:
            print(f"Error simulating jury response: {e}")

        return JuryResponse(
            jury_profile=jury_profile,
            receptiveness_score=0.5,
            predicted_reactions=["Analysis failed"],
            concerns=[],
            resonance_factors={},
        )

    async def score_witness_credibility(
        self,
        witness_id: str,
        testimony: str,
    ) -> CredibilityScore:
        """Assess witness credibility based on testimony patterns.
        
        Args:
            witness_id: Witness identifier
            testimony: Testimony text
            
        Returns:
            Credibility score and analysis
        """
        prompt = f"""
        Analyze this witness testimony for credibility markers.
        
        TESTIMONY:
        {testimony}
        
        Evaluate:
        1. Overall credibility score (0.0-1.0)
        2. Credibility factors (consistency, detail, certainty, etc.)
        3. Red flags (evasiveness, contradictions, vagueness)
        4. Strengths (specific details, consistency, confidence)
        
        Return JSON:
        {{
            "score": 0.0-1.0,
            "credibility_factors": {{
                "consistency": 0.0-1.0,
                "detail_level": 0.0-1.0,
                "certainty": 0.0-1.0,
                "coherence": 0.0-1.0
            }},
            "red_flags": ["flag 1", "flag 2"],
            "strengths": ["strength 1", "strength 2"]
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return CredibilityScore(
                    witness_id=witness_id,
                    testimony=testimony,
                    score=float(data.get("score", 0.5)),
                    credibility_factors=data.get("credibility_factors", {}),
                    red_flags=data.get("red_flags", []),
                    strengths=data.get("strengths", []),
                )
        except Exception as e:
            print(f"Error scoring credibility: {e}")

        return CredibilityScore(
            witness_id=witness_id,
            testimony=testimony,
            score=0.5,
            credibility_factors={},
            red_flags=["Analysis failed"],
            strengths=[],
        )

    async def get_case_parties(self, case_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query the Knowledge Graph for parties and witnesses involved in the case.
        Returns a dictionary with 'parties' and 'witnesses' lists.
        """
        query = """
        MATCH (c:Case {id: $case_id})-[:INVOLVES]->(p:Party)
        RETURN p, labels(p) as labels, 'party' as role
        UNION
        MATCH (c:Case {id: $case_id})-[:HAS_WITNESS]->(w:Witness)
        RETURN w as p, labels(w) as labels, 'witness' as role
        UNION
        MATCH (c:Case {id: $case_id})-[:MENTIONS]->(e:Entity)
        WHERE e.type IN ['PERSON', 'ORGANIZATION']
        RETURN e as p, labels(e) as labels, 'entity' as role
        """
        
        result_data = {"parties": [], "witnesses": [], "entities": []}
        
        try:
            results = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            if not results:
                return result_data
                
            for row in results:
                node = row.get("p", {})
                role = row.get("role")
                
                person_data = {
                    "id": node.get("elementId"),
                    "name": node.get("name") or node.get("label") or "Unknown",
                    "description": node.get("description", ""),
                    "type": node.get("type", "Unknown")
                }
                
                if role == 'party':
                    result_data["parties"].append(person_data)
                elif role == 'witness':
                    result_data["witnesses"].append(person_data)
                else:
                    result_data["entities"].append(person_data)
                    
            return result_data
            
        except Exception as e:
            print(f"Failed to get case parties from KG: {e}")
            return result_data


def get_jury_sentiment_service() -> JurySentimentService:
    """Get or create jury sentiment service instance."""
    return JurySentimentService()
