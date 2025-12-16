from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.services.llm_service import get_llm_service
from backend.app.services.timeline_service import TimelineService
from backend.app.storage.document_store import DocumentStore
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class Contradiction(BaseModel):
    id: str = Field(..., description="Unique ID for the contradiction")
    description: str = Field(..., description="Description of the contradiction")
    source_a: str = Field(..., description="First conflicting source (e.g., 'Timeline Event: Meeting')")
    source_b: str = Field(..., description="Second conflicting source (e.g., 'Document: Email Log')")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    severity: str = Field(..., description="Severity: 'high', 'medium', 'low'")

class NarrativeService:
    """
    Service for generating case narratives and detecting contradictions using LLM.
    """
    def __init__(self, timeline_service: TimelineService, document_store: DocumentStore):
        self.timeline_service = timeline_service
        self.document_store = document_store
        self.llm_service = get_llm_service()
        self.settings = get_settings()

    async def generate_narrative(self, case_id: str) -> str:
        """
        Generates a coherent narrative summary of the case based on timeline events and key documents.
        """
        logger.info(f"Generating narrative for case {case_id}")
        
        # 1. Gather Context
        events = self.timeline_service.get_timeline(case_id)
        documents = self.document_store.list_all_documents(case_id)
        
        # Sort events by date
        sorted_events = sorted(events, key=lambda x: x.event_date)
        
        # Prepare context string
        context_lines = ["TIMELINE EVENTS:"]
        for event in sorted_events:
            context_lines.append(f"- {event.event_date}: {event.title} - {event.description}")
            
        context_lines.append("\nKEY DOCUMENTS:")
        # Limit to top 20 documents to avoid context window issues for now
        # Ideally we'd use vector search to find relevant ones, but this is a global summary.
        for doc in documents[:20]: 
            summary = (doc.get("metadata") or {}).get("ai_summary", {}).get("summary", "No summary available")
            context_lines.append(f"- {doc['filename']}: {summary}")
            
        context_str = "\n".join(context_lines)
        
        # 2. Construct Prompt
        prompt = f"""
        You are an expert legal analyst. Your task is to generate a comprehensive narrative summary for a legal case based on the following timeline events and document summaries.
        
        The narrative should:
        1. Be written in a professional, objective tone.
        2. Chronologically weave together the events and evidence.
        3. Highlight key actors and their actions.
        4. Identify the central conflict or legal issue.
        
        CASE CONTEXT:
        {context_str}
        
        NARRATIVE:
        """
        
        # 3. Call LLM
        try:
            narrative = await self.llm_service.generate_text(prompt)
            return narrative.strip()
        except Exception as e:
            logger.error(f"Failed to generate narrative: {e}")
            return "Failed to generate narrative due to an internal error."

    async def detect_contradictions(self, case_id: str) -> List[Contradiction]:
        """
        Analyzes the case data to detect contradictions between timeline events and documents.
        """
        logger.info(f"Detecting contradictions for case {case_id}")
        
        # 1. Gather Context (Reuse similar logic)
        events = self.timeline_service.get_timeline(case_id)
        documents = self.document_store.list_all_documents(case_id)
        
        context_lines = ["TIMELINE EVENTS:"]
        for event in events:
            context_lines.append(f"- [Event ID: {event.id}] {event.event_date}: {event.title} - {event.description}")
            
        context_lines.append("\nDOCUMENTS:")
        for doc in documents[:20]:
            summary = (doc.get("metadata") or {}).get("ai_summary", {}).get("summary", "No summary available")
            context_lines.append(f"- [Doc ID: {doc['id']}] {doc['filename']}: {summary}")
            
        context_str = "\n".join(context_lines)
        
        # 2. Construct Prompt
        prompt = f"""
        You are an expert legal analyst. Analyze the following timeline events and document summaries to identify factual contradictions or inconsistencies.
        
        A contradiction occurs when:
        - Two events claim different things happened at the same time.
        - A document contradicts a timeline event description.
        - Timestamps are impossible (e.g., action before cause).
        
        Return the result as a JSON list of objects with the following keys:
        - "description": Brief description of the contradiction.
        - "source_a": The first conflicting source (e.g., "Event: Meeting on 2023-01-01").
        - "source_b": The second conflicting source.
        - "confidence": Float between 0.0 and 1.0.
        - "severity": "high", "medium", or "low".
        
        If no contradictions are found, return an empty list [].
        
        CASE CONTEXT:
        {context_str}
        
        JSON OUTPUT:
        """
        
        # 3. Call LLM
        try:
            logger.info("Calling LLM for contradiction detection...")
            response_text = await self.llm_service.generate_text(prompt)
            logger.info(f"LLM response received (Length: {len(response_text)})")
            
            # Clean up response to ensure it's valid JSON
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
                logger.error(f"Failed to parse JSON from LLM: {e}. Response: {response_text}")
                return []
            
            contradictions = []
            for item in data:
                contradictions.append(Contradiction(
                    id=str(uuid.uuid4()),
                    description=item.get("description", "Unknown contradiction"),
                    source_a=item.get("source_a", "Unknown"),
                    source_b=item.get("source_b", "Unknown"),
                    confidence=float(item.get("confidence", 0.5)),
                    severity=item.get("severity", "medium")
                ))
                
            logger.info(f"Detected {len(contradictions)} contradictions.")
            return contradictions
            
        except Exception as e:
            logger.error(f"Failed to detect contradictions: {e}")
            return []
