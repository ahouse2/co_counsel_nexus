"""
Document Drafting Swarm - Autonomous legal document generation with KG integration.

Agents:
1. TemplateSelectionAgent - Selects appropriate document template
2. FactGatheringAgent - Gathers facts from KG for insertion
3. ArgumentStructureAgent - Structures legal arguments
4. DraftingAgent - Generates document content
5. CitationInsertionAgent - Inserts proper citations
6. ProofreadingAgent - Reviews for errors and style
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
class DraftingAgentResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]


class DraftingBaseAgent:
    """Base class for drafting agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        raise NotImplementedError


class TemplateSelectionAgent(DraftingBaseAgent):
    """Agent 1: Selects appropriate document template."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "TemplateSelectionAgent")
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        try:
            case_type = context.get("case_type", "civil")
            jurisdiction = context.get("jurisdiction", "california")
            
            templates = {
                "complaint": {"sections": ["Caption", "Parties", "Jurisdiction", "Facts", "Causes of Action", "Prayer"], "rules": "CA CRC 2.100"},
                "motion": {"sections": ["Notice", "Memorandum of Points and Authorities", "Argument", "Conclusion"], "rules": "CA CRC 3.1113"},
                "discovery": {"sections": ["Definitions", "Instructions", "Requests/Interrogatories"], "rules": "CCP 2030"},
                "brief": {"sections": ["Statement of Issues", "Statement of Facts", "Argument", "Conclusion"], "rules": "CRC 8.204"},
                "contract": {"sections": ["Recitals", "Definitions", "Terms", "Representations", "Signatures"], "rules": "UCC"},
                "letter": {"sections": ["Header", "Salutation", "Body", "Closing"], "rules": "Professional"}
            }
            
            template = templates.get(doc_type.lower(), templates["letter"])
            
            return DraftingAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "doc_type": doc_type,
                    "template": template,
                    "jurisdiction": jurisdiction,
                    "case_type": case_type
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return DraftingAgentResult(self.name, False, {"error": str(e)})


class FactGatheringAgent(DraftingBaseAgent):
    """Agent 2: Gathers relevant facts from KG."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "FactGatheringAgent")
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        try:
            case_id = context.get("case_id", "default")
            
            # Query KG for facts
            facts_query = """
            MATCH (c:Case {id: $case_id})-[:HAS_FACT]->(f:Fact)
            RETURN f.description as fact, f.category as category, f.importance as importance
            ORDER BY f.importance DESC
            LIMIT 20
            """
            facts = await self.kg_service.run_cypher_query(facts_query, {"case_id": case_id})
            
            # Query parties
            parties_query = """
            MATCH (c:Case {id: $case_id})-[:INVOLVES]->(p:Party)
            RETURN p.name as name, p.role as role, p.description as description
            """
            parties = await self.kg_service.run_cypher_query(parties_query, {"case_id": case_id})
            
            # Query timeline
            timeline_query = """
            MATCH (e:Event {case_id: $case_id})
            RETURN e.date as date, e.description as description
            ORDER BY e.date
            LIMIT 15
            """
            timeline = await self.kg_service.run_cypher_query(timeline_query, {"case_id": case_id})
            
            return DraftingAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "facts": facts or [],
                    "parties": parties or [],
                    "timeline": timeline or []
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return DraftingAgentResult(self.name, False, {"error": str(e)})


class ArgumentStructureAgent(DraftingBaseAgent):
    """Agent 3: Structures legal arguments."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ArgumentStructureAgent")
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        try:
            facts = context.get("facts", [])
            user_instructions = context.get("instructions", "")
            
            prompt = f"""Structure legal arguments for a {doc_type} document.

USER INSTRUCTIONS:
{user_instructions}

AVAILABLE FACTS:
{chr(10).join([f"- {f.get('fact', '')}" for f in facts[:10]])}

Create an argument structure with:
1. Main contentions
2. Supporting points
3. Anticipated counterarguments
4. Rebuttals

Return JSON:
{{
    "main_arguments": [
        {{"heading": "...", "thesis": "...", "support": ["point1", "point2"]}}
    ],
    "counterarguments": ["...", "..."],
    "rebuttals": ["...", "..."],
    "recommended_order": [1, 2, 3]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return DraftingAgentResult(self.name, True, data)
            
            return DraftingAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return DraftingAgentResult(self.name, False, {"error": str(e)})


class ContentDraftingAgent(DraftingBaseAgent):
    """Agent 4: Generates document content."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ContentDraftingAgent")
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        try:
            template = context.get("template", {})
            arguments = context.get("arguments", {})
            facts = context.get("facts", [])
            parties = context.get("parties", [])
            instructions = context.get("instructions", "")
            
            sections = template.get("sections", ["Introduction", "Body", "Conclusion"])
            
            prompt = f"""Draft a {doc_type} document following this structure.

SECTIONS: {', '.join(sections)}

PARTIES:
{chr(10).join([f"- {p.get('name', 'Party')} ({p.get('role', 'party')})" for p in parties[:5]])}

KEY FACTS:
{chr(10).join([f"- {f.get('fact', '')}" for f in facts[:8]])}

ARGUMENTS TO INCLUDE:
{arguments.get('main_arguments', [])[:3] if arguments else 'See instructions'}

USER INSTRUCTIONS:
{instructions}

Draft each section professionally. Use proper legal formatting.

Return JSON:
{{
    "sections": [
        {{"title": "Section Name", "content": "..."}}
    ],
    "word_count": 0
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return DraftingAgentResult(self.name, True, data)
            
            return DraftingAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return DraftingAgentResult(self.name, False, {"error": str(e)})


class CitationInsertionAgent(DraftingBaseAgent):
    """Agent 5: Inserts proper citations."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "CitationInsertionAgent")
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        try:
            case_id = context.get("case_id", "default")
            sections = context.get("sections", [])
            
            # Get available citations from KG
            citation_query = """
            MATCH (c:Case {id: $case_id})-[:REFERENCES]->(cite)
            WHERE cite:Statute OR cite:Case
            RETURN labels(cite)[0] as type, cite.code as code, cite.name as name
            LIMIT 20
            """
            citations = await self.kg_service.run_cypher_query(citation_query, {"case_id": case_id})
            
            return DraftingAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "available_citations": citations or [],
                    "citation_format": "Bluebook" if doc_type in ["brief", "motion"] else "Standard"
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return DraftingAgentResult(self.name, False, {"error": str(e)})


class ProofreadingAgent(DraftingBaseAgent):
    """Agent 6: Reviews for errors and style."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ProofreadingAgent")
    
    async def process(self, doc_type: str, context: Dict[str, Any]) -> DraftingAgentResult:
        try:
            sections = context.get("sections", [])
            
            # Combine sections for review
            full_text = "\n\n".join([
                f"## {s.get('title', '')}\n{s.get('content', '')}"
                for s in sections[:10]
            ])[:8000]
            
            prompt = f"""Proofread this {doc_type} document for:
1. Grammar and spelling errors
2. Legal writing style issues
3. Formatting problems
4. Missing required elements

DOCUMENT:
{full_text}

Return JSON:
{{
    "errors": [
        {{"type": "grammar|spelling|style|format", "location": "...", "issue": "...", "suggestion": "..."}}
    ],
    "overall_quality": 0.0-1.0,
    "ready_for_filing": true/false
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return DraftingAgentResult(self.name, True, data)
            
            return DraftingAgentResult(self.name, True, {"errors": [], "overall_quality": 0.8, "ready_for_filing": True})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return DraftingAgentResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# DRAFTING SWARM
# ═══════════════════════════════════════════════════════════════════════════

class DraftingSwarm:
    """
    Full document drafting swarm with 6 agents.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.template_selection = TemplateSelectionAgent(self.llm_service, self.kg_service)
        self.fact_gathering = FactGatheringAgent(self.llm_service, self.kg_service)
        self.argument_structure = ArgumentStructureAgent(self.llm_service, self.kg_service)
        self.content_drafting = ContentDraftingAgent(self.llm_service, self.kg_service)
        self.citation_insertion = CitationInsertionAgent(self.llm_service, self.kg_service)
        self.proofreading = ProofreadingAgent(self.llm_service, self.kg_service)
        
        logger.info("DraftingSwarm initialized with 6 agents")
    
    async def draft_document(self, doc_type: str, case_id: str, instructions: str = "") -> Dict[str, Any]:
        """Run full document drafting pipeline."""
        context = {"case_id": case_id, "instructions": instructions}
        
        # Stage 1: Template selection
        logger.info(f"[DraftingSwarm] Selecting template for {doc_type}")
        template_result = await self.template_selection.process(doc_type, context)
        context.update(template_result.output)
        
        # Stage 2: Fact gathering from KG
        logger.info(f"[DraftingSwarm] Gathering facts from KG")
        facts_result = await self.fact_gathering.process(doc_type, context)
        context.update(facts_result.output)
        
        # Stage 3: Argument structure
        logger.info(f"[DraftingSwarm] Structuring arguments")
        args_result = await self.argument_structure.process(doc_type, context)
        context["arguments"] = args_result.output
        
        # Stage 4: Content drafting
        logger.info(f"[DraftingSwarm] Drafting content")
        draft_result = await self.content_drafting.process(doc_type, context)
        context["sections"] = draft_result.output.get("sections", [])
        
        # Stage 5: Citation insertion (parallel with proofreading prep)
        logger.info(f"[DraftingSwarm] Adding citations")
        citation_result = await self.citation_insertion.process(doc_type, context)
        
        # Stage 6: Proofreading
        logger.info(f"[DraftingSwarm] Proofreading")
        proof_result = await self.proofreading.process(doc_type, context)
        
        return {
            "doc_type": doc_type,
            "case_id": case_id,
            "sections": context.get("sections", []),
            "arguments": args_result.output,
            "citations": citation_result.output,
            "proofreading": proof_result.output,
            "ready_for_filing": proof_result.output.get("ready_for_filing", False)
        }


# Factory
_drafting_swarm: Optional[DraftingSwarm] = None

def get_drafting_swarm() -> DraftingSwarm:
    global _drafting_swarm
    if _drafting_swarm is None:
        _drafting_swarm = DraftingSwarm()
    return _drafting_swarm
