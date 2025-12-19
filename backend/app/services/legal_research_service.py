from typing import List, Optional, Dict
from pydantic import BaseModel
from backend.app.services.llm_service import get_llm_service
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService

class ShepardizeRequest(BaseModel):
    citation: str

class ShepardizeResult(BaseModel):
    citation: str
    status: str # "good_law", "overruled", "questioned", "distinguished"
    reasoning: str
    relevant_cases: List[str]

class JudgeProfileRequest(BaseModel):
    judge_name: str
    jurisdiction: str

class JudgeProfileResult(BaseModel):
    judge_name: str
    biography: str
    ruling_tendencies: Dict[str, float] # e.g., {"plaintiff_friendly": 0.6}
    key_opinions: List[str]

class LegalResearchService:
    """Enhanced with KG integration."""
    def __init__(self, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()

    async def shepardize(self, request: ShepardizeRequest) -> ShepardizeResult:
        """
        Simulates checking if a case is still good law.
        In a real system, this would query a citation API (e.g., Shepard's or KeyCite).
        Here, we use the LLM to infer based on its training data (cutoff applies).
        """
        prompt = f"""
        You are a legal research assistant. Check if the following case citation is still good law.
        
        CITATION: {request.citation}
        
        INSTRUCTIONS:
        1. Determine if the case has been overruled, questioned, or distinguished.
        2. Provide a status: "good_law", "overruled", "questioned", or "distinguished".
        3. Explain your reasoning.
        4. List relevant subsequent cases.
        
        OUTPUT JSON:
        {{
            "status": "...",
            "reasoning": "...",
            "relevant_cases": ["Case A", "Case B"]
        }}
        """
        
        response = await self.llm_service.generate_text(prompt)
        
        # Mock parsing for robustness
        import json
        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned)
            
            return ShepardizeResult(
                citation=request.citation,
                status=data.get("status", "unknown"),
                reasoning=data.get("reasoning", "Analysis failed."),
                relevant_cases=data.get("relevant_cases", [])
            )
        except:
            return ShepardizeResult(
                citation=request.citation,
                status="unknown",
                reasoning="Could not parse analysis.",
                relevant_cases=[]
            )

    async def profile_judge(self, request: JudgeProfileRequest) -> JudgeProfileResult:
        """
        Generates a profile for a specific judge.
        """
        prompt = f"""
        You are a legal strategist. Create a profile for Judge {request.judge_name} in {request.jurisdiction}.
        
        INSTRUCTIONS:
        1. Summarize their biography and judicial philosophy.
        2. Estimate their ruling tendencies (e.g., pro-plaintiff vs pro-defendant, strict vs loose constructionist).
        3. List key opinions they have authored.
        
        OUTPUT JSON:
        {{
            "biography": "...",
            "ruling_tendencies": {{"pro_plaintiff": 0.5, "strict_constructionist": 0.8}},
            "key_opinions": ["Opinion A", "Opinion B"]
        }}
        """
        
        response = await self.llm_service.generate_text(prompt)
        
        import json
        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned)
            
            return JudgeProfileResult(
                judge_name=request.judge_name,
                biography=data.get("biography", ""),
                ruling_tendencies=data.get("ruling_tendencies", {}),
                key_opinions=data.get("key_opinions", [])
            )
        except:
            return JudgeProfileResult(
                judge_name=request.judge_name,
                biography="Profile generation failed.",
                ruling_tendencies={},
                key_opinions=[]
            )

_service = None
def get_legal_research_service():
    global _service
    if _service is None:
        _service = LegalResearchService()
    return _service
