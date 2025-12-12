"""Jury analysis agent with specialized sentiment and persuasiveness tools."""

from __future__ import annotations

from typing import Any, Dict, List

from .context import AgentContext
from ..services.llm_service import LLMService, get_llm_service


class JuryAnalysisAgent:
    """Agent for analyzing jury sentiment and providing recommendations."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or get_llm_service()

    async def analyze_persuasiveness(
        self,
        context: AgentContext,
        text: str,
    ) -> Dict[str, Any]:
        """Detailed persuasiveness analysis of argument text.
        
        Args:
            context: Agent context
            text: Text to analyze
            
        Returns:
            Analysis with scores, weak points, and suggestions
        """
        prompt = f"""
        Perform a detailed persuasiveness analysis of this legal argument.
        
        TEXT:
        {text}
        
        Analyze:
        1. Logical structure and coherence
        2. Emotional appeal and tone
        3. Credibility markers
        4. Weak points that could be challenged
        5. Specific suggestions for improvement
        
        Return JSON with detailed scores and recommendations.
        """

        response = await self.llm_service.generate_text(prompt)
        # Parse and return structured analysis
        import json
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"error": "Analysis failed"}

    async def detect_bias(
        self,
        context: AgentContext,
        text: str,
    ) -> List[Dict[str, Any]]:
        """Identify potentially problematic language or implicit biases.
        
        Args:
            context: Agent context
            text: Text to analyze
            
        Returns:
            List of bias instances with alternatives
        """
        prompt = f"""
        Identify any potentially problematic language or implicit biases in this text.
        
        TEXT:
        {text}
        
        Look for:
        - Gender bias
        - Racial or ethnic bias
        - Socioeconomic bias
        - Age bias
        - Inflammatory language
        - Assumptions that could alienate jurors
        
        For each issue found, provide:
        - The problematic phrase
        - Why it's problematic
        - A suggested alternative
        
        Return JSON array of bias instances.
        """

        response = await self.llm_service.generate_text(prompt)
        import json
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return []


def get_jury_analysis_agent() -> JuryAnalysisAgent:
    """Get or create jury analysis agent instance."""
    return JuryAnalysisAgent()
