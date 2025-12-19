"""
Legal Research Swarm - Autonomous legal research with KG integration.

Enhanced from LegalResearchTeam with full swarm architecture:
1. CaseLawAgent - Searches CourtListener for relevant cases
2. StatuteAgent - Searches CA/Federal codes
3. SecondarySourceAgent - Treatises, law reviews
4. CitationAnalysisAgent - Analyzes citation networks
5. SynthesisAgent - Combines research into memo
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
class ResearchAgentResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]


class ResearchAgent:
    """Base class for research agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def research(self, query: str, context: Dict[str, Any]) -> ResearchAgentResult:
        raise NotImplementedError


class CaseLawAgent(ResearchAgent):
    """Agent 1: Searches for relevant case law."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "CaseLawAgent")
    
    async def research(self, query: str, context: Dict[str, Any]) -> ResearchAgentResult:
        """Search for relevant case law."""
        try:
            jurisdiction = context.get("jurisdiction", "california")
            
            # Query KG for existing case law
            kg_query = """
            MATCH (c:Case)-[:RELEVANT_TO]->(issue:LegalIssue)
            WHERE issue.description CONTAINS $query
            RETURN c.name as case_name, c.citation as citation, 
                   c.summary as summary, c.year as year
            LIMIT 10
            """
            existing = await self.kg_service.run_cypher_query(kg_query, {"query": query[:50]})
            
            # Use LLM to generate search terms and find cases
            prompt = f"""Given this legal research query, identify relevant case law.

QUERY: {query}
JURISDICTION: {jurisdiction}

Generate:
1. Key legal issues
2. Relevant landmark cases
3. Search terms for legal databases

Return JSON:
{{
    "legal_issues": ["issue1", "issue2"],
    "landmark_cases": [
        {{"name": "...", "citation": "...", "relevance": "..."}}
    ],
    "search_terms": ["term1", "term2"]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                # Combine with existing KG results
                cases = data.get("landmark_cases", [])
                for e in (existing or []):
                    cases.append({
                        "name": e.get("case_name"),
                        "citation": e.get("citation"),
                        "summary": e.get("summary", "")[:200],
                        "source": "knowledge_graph"
                    })
                
                return ResearchAgentResult(self.name, True, {
                    "cases": cases,
                    "legal_issues": data.get("legal_issues", []),
                    "search_terms": data.get("search_terms", [])
                })
            
            return ResearchAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ResearchAgentResult(self.name, False, {"error": str(e)})


class StatuteAgent(ResearchAgent):
    """Agent 2: Searches for relevant statutes and regulations."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "StatuteAgent")
    
    async def research(self, query: str, context: Dict[str, Any]) -> ResearchAgentResult:
        """Search for relevant statutes."""
        try:
            jurisdiction = context.get("jurisdiction", "california")
            
            prompt = f"""Identify relevant statutes and regulations for this legal query.

QUERY: {query}
JURISDICTION: {jurisdiction}

Return JSON:
{{
    "statutes": [
        {{"code": "CA Civil Code § 1234", "title": "...", "relevance": "..."}}
    ],
    "regulations": [
        {{"cite": "...", "title": "...", "relevance": "..."}}
    ],
    "constitutional": ["if applicable"]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                # Store in KG
                for statute in data.get("statutes", [])[:5]:
                    store_query = """
                    MERGE (s:Statute {code: $code})
                    SET s.title = $title, s.relevance = $relevance
                    WITH s
                    MATCH (c:Case {id: $case_id})
                    MERGE (c)-[:REFERENCES]->(s)
                    """
                    await self.kg_service.run_cypher_query(store_query, {
                        "code": statute.get("code", ""),
                        "title": statute.get("title", ""),
                        "relevance": statute.get("relevance", ""),
                        "case_id": context.get("case_id", "default")
                    })
                
                return ResearchAgentResult(self.name, True, data)
            
            return ResearchAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ResearchAgentResult(self.name, False, {"error": str(e)})


class SecondarySourceAgent(ResearchAgent):
    """Agent 3: Searches secondary sources (treatises, law reviews)."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "SecondarySourceAgent")
    
    async def research(self, query: str, context: Dict[str, Any]) -> ResearchAgentResult:
        """Search secondary sources."""
        try:
            prompt = f"""Identify relevant secondary legal sources for this query.

QUERY: {query}

Secondary sources include:
- Witkin (CA Practice)
- Restatements
- Law reviews/journals
- Practice guides
- Legal encyclopedias

Return JSON:
{{
    "treatises": [{{"title": "...", "section": "...", "relevance": "..."}}],
    "restatements": [{{"name": "...", "section": "...", "rule": "..."}}],
    "law_reviews": [{{"title": "...", "citation": "..."}}]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return ResearchAgentResult(self.name, True, data)
            
            return ResearchAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ResearchAgentResult(self.name, False, {"error": str(e)})


class CitationAnalysisAgent(ResearchAgent):
    """Agent 4: Analyzes citation networks."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "CitationAnalysisAgent")
    
    async def research(self, query: str, context: Dict[str, Any]) -> ResearchAgentResult:
        """Analyze citation networks from KG."""
        try:
            case_id = context.get("case_id", "default")
            
            # Query citation network from KG
            citation_query = """
            MATCH (d:Document {case_id: $case_id})-[:CITES]->(c:Citation)
            OPTIONAL MATCH (c)<-[:CITES]-(other:Document)
            RETURN c.text as citation, c.type as type,
                   count(other) as citing_count
            ORDER BY citing_count DESC
            LIMIT 20
            """
            citations = await self.kg_service.run_cypher_query(citation_query, {"case_id": case_id})
            
            # Analyze with LLM
            if citations:
                citation_list = "\n".join([f"- {c.get('citation')} (cited {c.get('citing_count')} times)" for c in citations])
                
                prompt = f"""Analyze this citation network for the research query.

QUERY: {query}

CITATIONS FOUND:
{citation_list}

Identify:
1. Most authoritative cases (frequently cited)
2. Citation chains (A cites B cites C)
3. Conflicting authorities
4. Recent developments

Return JSON:
{{
    "authoritative": ["citation1", "citation2"],
    "chains": ["A → B → C"],
    "conflicts": ["if any"],
    "recent": ["if any"]
}}"""

                response = await self.llm_service.generate_text(prompt)
                import json, re
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    return ResearchAgentResult(self.name, True, data)
            
            return ResearchAgentResult(self.name, True, {
                "authoritative": [],
                "chains": [],
                "note": "No citations in graph yet"
            })
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ResearchAgentResult(self.name, False, {"error": str(e)})


class SynthesisAgent(ResearchAgent):
    """Agent 5: Synthesizes research into a memo."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "SynthesisAgent")
    
    async def research(self, query: str, context: Dict[str, Any]) -> ResearchAgentResult:
        """Synthesize all research into a memo."""
        try:
            cases = context.get("cases", [])
            statutes = context.get("statutes", [])
            secondary = context.get("secondary", {})
            
            prompt = f"""Synthesize this legal research into a professional memo.

QUERY: {query}

CASES FOUND:
{chr(10).join([f"- {c.get('name', 'Unknown')}: {c.get('relevance', '')}" for c in cases[:5]])}

STATUTES:
{chr(10).join([f"- {s.get('code', 'Unknown')}" for s in statutes[:5]]) if statutes else 'None identified'}

Return a memo with:
1. Issue statement
2. Brief answer
3. Analysis (with citations)
4. Conclusion

Return JSON:
{{
    "issue": "...",
    "brief_answer": "...",
    "analysis": "...",
    "conclusion": "...",
    "key_authorities": ["cite1", "cite2"]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return ResearchAgentResult(self.name, True, data)
            
            return ResearchAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ResearchAgentResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# LEGAL RESEARCH SWARM
# ═══════════════════════════════════════════════════════════════════════════

class LegalResearchSwarm:
    """
    Full legal research swarm with 5 specialized agents.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.case_law = CaseLawAgent(self.llm_service, self.kg_service)
        self.statute = StatuteAgent(self.llm_service, self.kg_service)
        self.secondary = SecondarySourceAgent(self.llm_service, self.kg_service)
        self.citation_analysis = CitationAnalysisAgent(self.llm_service, self.kg_service)
        self.synthesis = SynthesisAgent(self.llm_service, self.kg_service)
        
        logger.info("LegalResearchSwarm initialized with 5 agents")
    
    async def research(self, query: str, case_id: str, jurisdiction: str = "california") -> Dict[str, Any]:
        """Run full legal research pipeline."""
        context = {"case_id": case_id, "jurisdiction": jurisdiction}
        
        # Stage 1: Parallel primary research
        logger.info(f"[LegalResearchSwarm] Starting research for: {query[:50]}...")
        
        case_task = self.case_law.research(query, context)
        statute_task = self.statute.research(query, context)
        secondary_task = self.secondary.research(query, context)
        
        case_result, statute_result, secondary_result = await asyncio.gather(
            case_task, statute_task, secondary_task
        )
        
        # Update context
        context["cases"] = case_result.output.get("cases", [])
        context["statutes"] = statute_result.output.get("statutes", [])
        context["secondary"] = secondary_result.output
        
        # Stage 2: Citation analysis
        logger.info(f"[LegalResearchSwarm] Analyzing citations")
        citation_result = await self.citation_analysis.research(query, context)
        
        # Stage 3: Synthesis
        logger.info(f"[LegalResearchSwarm] Synthesizing memo")
        synthesis_result = await self.synthesis.research(query, context)
        
        # Store research in KG
        store_query = """
        MERGE (r:ResearchMemo {case_id: $case_id, query: $query})
        SET r.memo = $memo,
            r.created_at = datetime()
        """
        await self.kg_service.run_cypher_query(store_query, {
            "case_id": case_id,
            "query": query[:200],
            "memo": str(synthesis_result.output)[:5000]
        })
        
        return {
            "query": query,
            "case_id": case_id,
            "cases": case_result.output,
            "statutes": statute_result.output,
            "secondary": secondary_result.output,
            "citations": citation_result.output,
            "memo": synthesis_result.output
        }


# Factory
_legal_research_swarm: Optional[LegalResearchSwarm] = None

def get_legal_research_swarm() -> LegalResearchSwarm:
    global _legal_research_swarm
    if _legal_research_swarm is None:
        _legal_research_swarm = LegalResearchSwarm()
    return _legal_research_swarm
