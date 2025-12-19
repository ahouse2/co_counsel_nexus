from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.services.llm_service import get_llm_service
from backend.app.services.timeline_service import TimelineService
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService
from backend.app.storage.document_store import DocumentStore
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class CaseWeakness(BaseModel):
    id: str = Field(..., description="Unique ID for the weakness")
    title: str = Field(..., description="Short title of the weakness")
    description: str = Field(..., description="Detailed description")
    severity: str = Field(..., description="Severity: 'critical', 'high', 'medium', 'low'")
    suggested_rebuttal: str = Field(..., description="How to counter this weakness")
    related_evidence_ids: List[str] = Field(default_factory=list, description="IDs of related evidence/events")

class CrossExamQuestion(BaseModel):
    question: str
    rationale: str
    difficulty: str

class DevilsAdvocateService:
    """
    Service that acts as opposing counsel, finding holes in the case and simulating opposition.
    Enhanced with KnowledgeGraphService for evidence-based adversarial analysis.
    """
    def __init__(self, timeline_service: TimelineService, document_store: DocumentStore, kg_service: Optional[KnowledgeGraphService] = None):
        self.timeline_service = timeline_service
        self.document_store = document_store
        self.llm_service = get_llm_service()
        self.settings = get_settings()
        # KG Integration: Query graph for evidence connections and contradictions
        self.kg_service = kg_service or get_knowledge_graph_service()

    async def review_case(self, case_id: str, case_theory: Optional[str] = None) -> List[CaseWeakness]:
        """
        Analyzes the case timeline and key documents to find weaknesses, acting as an autonomous opposing counsel.
        """
        logger.info(f"Devil's Advocate reviewing case {case_id} with theory: {case_theory[:50] if case_theory else 'None'}")
        
        # 1. Gather Context
        events = self.timeline_service.get_timeline(case_id)
        documents = self.document_store.list_all_documents(case_id)
        
        context_lines = ["TIMELINE:"]
        for event in events:
            context_lines.append(f"- {event.event_date}: {event.title} - {event.description}")
            
        context_lines.append("\nKEY EVIDENCE:")
        for doc in documents[:15]:
            summary = (doc.get("metadata") or {}).get("ai_summary", {}).get("summary", "No summary")
            context_lines.append(f"- {doc['filename']}: {summary}")
        
        # ═══════════════════════════════════════════════════════════════════
        # KG INTEGRATION: Query graph for evidence gaps and support scores
        # ═══════════════════════════════════════════════════════════════════
        kg_weaknesses = await self._analyze_kg_for_weaknesses(case_id)
        if kg_weaknesses:
            context_lines.append("\nKNOWLEDGE GRAPH ANALYSIS:")
            context_lines.extend(kg_weaknesses)
            
        context_str = "\n".join(context_lines)
        
        # 2. Prompt
        theory_context = f"USER'S CASE THEORY:\n{case_theory}\n" if case_theory else "NO EXPLICIT THEORY PROVIDED. INFER THE PLAINTIFF/PROSECUTION THEORY FROM THE FACTS."

        prompt = f"""
        You are "The Devil's Advocate" — an autonomous, ruthless, and highly skilled opposing counsel.
        Your goal is not just to find bugs, but to dismantle the case strategy.

        {theory_context}

        CASE CONTEXT:
        {context_str}

        INSTRUCTIONS:
        1. Analyze the facts and the provided (or inferred) theory.
        2. Identify the most critical legal and factual weaknesses.
        3. "Litmus Test" the theory: Does the evidence actually support the claims? Are there alternative explanations?
        4. Construct a strategic counter-narrative.
        
        Return a JSON list of objects with:
        - "title": Short, punchy title of the weakness (e.g., "Lack of Causation", "Hearsay Evidence").
        - "description": Detailed legal/factual analysis of why this is a weakness.
        - "severity": "critical", "high", "medium", or "low".
        - "suggested_rebuttal": Strategic advice on how to fix this or what the opposition will argue.
        - "related_evidence_ids": List of strings (optional).
        
        JSON OUTPUT:
        """
        
        # 3. Call LLM
        try:
            logger.info("Devil's Advocate calling LLM for review...")
            response_text = await self.llm_service.generate_text(prompt)
            logger.info(f"Devil's Advocate LLM response received (Length: {len(response_text)})")
            
            # Clean JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            import json
            import uuid
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Devil's Advocate LLM: {e}. Response: {response_text}")
                return []
            
            weaknesses = []
            for item in data:
                weaknesses.append(CaseWeakness(
                    id=str(uuid.uuid4()),
                    title=item.get("title", "Unknown Weakness"),
                    description=item.get("description", ""),
                    severity=item.get("severity", "medium"),
                    suggested_rebuttal=item.get("suggested_rebuttal", ""),
                    related_evidence_ids=item.get("related_evidence_ids", [])
                ))
            
            logger.info(f"Devil's Advocate found {len(weaknesses)} weaknesses.")
            return weaknesses
        except Exception as e:
            logger.error(f"Devil's Advocate review failed: {e}")
            return []

    async def generate_cross_examination(self, witness_statement: str, witness_profile: str = "") -> List[CrossExamQuestion]:
        """
        Generates cross-examination questions for a given witness statement.
        """
        prompt = f"""
        You are an expert trial lawyer conducting cross-examination.
        
        WITNESS PROFILE: {witness_profile}
        WITNESS STATEMENT: "{witness_statement}"
        
        Generate 5 tough cross-examination questions intended to impeach this witness or expose bias/inconsistency.
        For each, provide the rationale and difficulty level.
        
        Return JSON list:
        - "question": The question text.
        - "rationale": Why ask this?
        - "difficulty": "easy", "medium", "hard".
        
        JSON OUTPUT:
        """
        
        try:
            response_text = await self.llm_service.generate_text(prompt)
             # Clean JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            import json
            data = json.loads(response_text)
            
            questions = []
            for item in data:
                questions.append(CrossExamQuestion(**item))
            return questions
            
        except Exception as e:
            logger.error(f"Cross-exam generation failed: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # KNOWLEDGE GRAPH INTEGRATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _analyze_kg_for_weaknesses(self, case_id: str) -> List[str]:
        """
        Query the Knowledge Graph for evidence gaps, weak cause support,
        and contradictions that could be exploited by opposing counsel.
        """
        analysis_lines = []
        
        try:
            # 1. Check cause of action support scores (low scores = weaknesses)
            cause_scores = await self.kg_service.cause_support_scores(case_id)
            if cause_scores:
                weak_causes = [(c, s) for c, s in cause_scores.items() if s < 0.5]
                if weak_causes:
                    analysis_lines.append("WEAK CAUSES OF ACTION:")
                    for cause, score in sorted(weak_causes, key=lambda x: x[1]):
                        analysis_lines.append(f"  - {cause}: only {score:.0%} support (VULNERABLE)")
            
            # 2. Query for evidence contradictions
            contradiction_query = """
            MATCH (e1:Evidence)-[:CONTRADICTS]->(e2:Evidence)
            WHERE e1.case_id = $case_id OR e2.case_id = $case_id
            RETURN e1.summary as evidence1, e2.summary as evidence2
            LIMIT 5
            """
            try:
                contradictions = await self.kg_service.run_cypher_query(
                    contradiction_query, 
                    {"case_id": case_id}
                )
                if contradictions:
                    analysis_lines.append("EVIDENCE CONTRADICTIONS:")
                    for c in contradictions:
                        analysis_lines.append(f"  - \"{c.get('evidence1', '?')}\" vs \"{c.get('evidence2', '?')}\"")
            except Exception as e:
                logger.debug(f"No contradictions found in graph: {e}")
            
            # 3. Check for unsupported claims (entities without evidence links)
            unsupported_query = """
            MATCH (claim:Claim {case_id: $case_id})
            WHERE NOT (claim)<-[:SUPPORTS]-(:Evidence)
            RETURN claim.text as claim_text
            LIMIT 3
            """
            try:
                unsupported = await self.kg_service.run_cypher_query(
                    unsupported_query,
                    {"case_id": case_id}
                )
                if unsupported:
                    analysis_lines.append("UNSUPPORTED CLAIMS:")
                    for item in unsupported:
                        claim = item.get("claim_text", "Unknown claim")[:100]
                        analysis_lines.append(f"  - {claim}... (NO EVIDENCE)")
            except Exception as e:
                logger.debug(f"No unsupported claims query result: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to analyze KG for weaknesses: {e}")
        
        return analysis_lines

