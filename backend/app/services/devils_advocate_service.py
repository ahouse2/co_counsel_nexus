from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.services.llm_service import get_llm_service
from backend.app.services.timeline_service import TimelineService
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
    """
    def __init__(self, timeline_service: TimelineService, document_store: DocumentStore):
        self.timeline_service = timeline_service
        self.document_store = document_store
        self.llm_service = get_llm_service()
        self.settings = get_settings()

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
            response_text = await self.llm_service.generate_text(prompt)
            
            # Clean JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            import json
            import uuid
            data = json.loads(response_text)
            
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
