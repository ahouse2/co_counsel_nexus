from typing import List, Dict, Any
import json
from backend.app.config import get_settings
from backend.ingestion.llama_index_factory import create_llm_service
from backend.ingestion.settings import build_runtime_config
from backend.app.services.timeline import get_timeline_service

class EvidenceMapService:
    def __init__(self):
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        self.llm_service = create_llm_service(runtime_config.llm)
        self.timeline_service = get_timeline_service()

    def analyze_locations(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Extracts geospatial locations from the case timeline.
        """
        # 1. Get Timeline Events
        try:
            timeline_result = self.timeline_service.list_events(case_id)
            events = timeline_result.events if timeline_result else []
        except Exception:
            return []

        if not events:
            return []

        # 2. Filter for events that likely have locations
        # (Heuristic: look for "at", "in", "near" or just send batch to LLM)
        # For prototype, we'll send the most recent 20 events to avoid context limits
        recent_events = sorted(events, key=lambda e: e.ts)[-20:]
        
        events_text = "\n".join([
            f"ID: {e.id}\nTime: {e.ts}\nSummary: {e.summary}" 
            for e in recent_events
        ])

        # 3. Prompt LLM
        prompt = f"""
        Analyze the following timeline events and extract any PHYSICAL LOCATIONS mentioned or implied.
        For each location, provide:
        1. The name of the place.
        2. Estimated Latitude/Longitude (best guess based on context, default to New York City area 40.7128, -74.0060 if unknown but looks urban).
        3. The Event ID it is associated with.

        TIMELINE:
        {events_text}

        Return ONLY a JSON list of objects with keys:
        - "event_id": str
        - "location_name": str
        - "lat": float
        - "lng": float
        - "description": str (brief context)
        """

        try:
            response = self.llm_service.complete(prompt)
            text = response.text
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            locations = json.loads(text.strip())
            return locations
        except Exception as e:
            print(f"Evidence Map Error: {e}")
            return []
