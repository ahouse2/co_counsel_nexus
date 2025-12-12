from typing import List, Dict, Any
import json
import logging
from datetime import datetime

from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class TimelineAgent:
    """
    Autonomous agent specialized in extracting chronological events from legal documents.
    """
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def extract_events(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyzes text and returns a list of timeline events.
        """
        # Limit text length to avoid context window issues (simple truncation for now)
        # In production, we'd chunk this.
        truncated_text = text[:50000] 
        
        prompt = f"""
        You are an expert legal analyst. Your task is to extract a chronological timeline of factual events from the provided document text.

        Document Metadata: {json.dumps(metadata, default=str)}

        Instructions:
        1. Identify specific factual events with dates/times.
        2. Ignore procedural events (e.g., "Motion filed") unless critical to the case narrative. Focus on the underlying facts (e.g., "Plaintiff signed contract", "Accident occurred").
        3. Extract the exact date (YYYY-MM-DD) or datetime (YYYY-MM-DD HH:MM:SS). If approximate, use the first of the month/year.
        4. Provide a concise title and a detailed description for each event.
        5. Return the output as a JSON list of objects.

        Output Format:
        [
            {{
                "title": "Event Title",
                "description": "Detailed description of what happened.",
                "event_date": "YYYY-MM-DDTHH:MM:SS",
                "confidence": 0.9
            }}
        ]

        Text to Analyze:
        {truncated_text}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Timeline extraction failed: {e}")
            return []

    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        try:
            # Clean markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            events = json.loads(response.strip())
            
            # Validate and format
            valid_events = []
            for event in events:
                if "title" in event and "event_date" in event:
                    # Ensure metadata dict exists
                    event["metadata"] = {"source": "ai_extraction"}
                    valid_events.append(event)
            
            return valid_events
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {response[:100]}...")
            return []
