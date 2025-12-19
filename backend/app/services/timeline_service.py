from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    event_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict) # To link to documents, evidence, etc.

from backend.app.config import get_settings
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService

class TimelineService:
    """
    Manages the creation, retrieval, and modification of case timelines.
    Enhanced with KG integration for graph-derived temporal data.
    """
    def __init__(self, kg_service: Optional[KnowledgeGraphService] = None):
        settings = get_settings()
        self.storage_path = settings.timeline_storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        # KG Integration: Query graph for events and temporal relationships
        self.kg_service = kg_service or get_knowledge_graph_service()

    def _get_timeline_path(self, case_id: str) -> Path:
        return self.storage_path / f"timeline_{case_id}.json"

    def _read_timeline(self, case_id: str) -> List[TimelineEvent]:
        timeline_path = self._get_timeline_path(case_id)
        if not timeline_path.exists():
            return []
        with open(timeline_path, 'r') as f:
            events_data = json.load(f)
        return [TimelineEvent(**data) for data in events_data]

    def _write_timeline(self, case_id: str, events: List[TimelineEvent]):
        timeline_path = self._get_timeline_path(case_id)
        events_data = [event.model_dump() for event in events]
        with open(timeline_path, 'w') as f:
            json.dump(events_data, f, indent=4, default=str)

    def add_event(self, case_id: str, event_data: Dict[str, Any]) -> TimelineEvent:
        """Adds a new event to a case's timeline."""
        events = self._read_timeline(case_id)
        new_event = TimelineEvent(**event_data)
        events.append(new_event)
        events.sort(key=lambda e: e.event_date) # Keep timeline sorted
        self._write_timeline(case_id, events)
        return new_event

    def get_timeline(self, case_id: str) -> List[TimelineEvent]:
        """Retrieves the entire timeline for a case."""
        return self._read_timeline(case_id)

    def update_event(self, case_id: str, event_id: str, update_data: Dict[str, Any]) -> Optional[TimelineEvent]:
        """Updates an existing event in the timeline."""
        events = self._read_timeline(case_id)
        event_to_update = None
        for event in events:
            if event.id == event_id:
                event_to_update = event
                break
        
        if not event_to_update:
            return None

        update_data['updated_at'] = datetime.utcnow()
        updated_event = event_to_update.model_copy(update=update_data)
        
        # Replace the old event with the updated one
        updated_events = [updated_event if e.id == event_id else e for e in events]
        updated_events.sort(key=lambda e: e.event_date)
        self._write_timeline(case_id, updated_events)
        
        return updated_event

    def remove_event(self, case_id: str, event_id: str) -> bool:
        """Removes an event from the timeline."""
        events = self._read_timeline(case_id)
        original_count = len(events)
        events = [event for event in events if event.id != event_id]
        
        if len(events) < original_count:
            self._write_timeline(case_id, events)
            return True
        return False

    async def sync_from_kg(self, case_id: str) -> int:
        """
        Queries the Knowledge Graph for events and merges them into the timeline.
        Returns the number of new events added.
        """
        # Query for nodes with dates or explicit Event nodes
        query = """
        MATCH (c:Case {id: $case_id})
        MATCH (n)-[:MENTIONS|HAS_DATE]->(d:Date)
        WHERE n:Document OR n:Event
        RETURN n, d.date as date, labels(n) as labels
        UNION
        MATCH (c:Case {id: $case_id})-[:HAS_EVENT]->(e:Event)
        RETURN e as n, e.date as date, labels(e) as labels
        """
        
        try:
            results = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            if not results:
                return 0
                
            current_events = self._read_timeline(case_id)
            # Create a set of existing event signatures to avoid duplicates
            # Signature: date + title (first 50 chars)
            existing_signatures = {
                (e.event_date.strftime("%Y-%m-%d"), e.title[:50]) 
                for e in current_events
            }
            
            new_events = []
            for row in results:
                node = row.get("n", {})
                date_str = row.get("date")
                labels = row.get("labels", [])
                
                if not date_str:
                    continue
                    
                try:
                    # Handle various date formats if needed, assuming ISO for now
                    event_date = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                except ValueError:
                    continue
                    
                # Determine title and description
                if "Document" in labels:
                    title = f"Document: {node.get('filename', 'Unknown Document')}"
                    description = node.get('summary', 'No summary available')
                else:
                    title = node.get('name') or node.get('title') or "Untitled Event"
                    description = node.get('description') or node.get('summary') or "No description"
                
                # Check for duplicate
                signature = (event_date.strftime("%Y-%m-%d"), title[:50])
                if signature in existing_signatures:
                    continue
                    
                new_event = TimelineEvent(
                    title=title,
                    description=description,
                    event_date=event_date,
                    metadata={"source": "knowledge_graph", "node_id": node.get("elementId")}
                )
                new_events.append(new_event)
                existing_signatures.add(signature)
            
            if new_events:
                current_events.extend(new_events)
                current_events.sort(key=lambda e: e.event_date)
                self._write_timeline(case_id, current_events)
                return len(new_events)
                
            return 0
            
        except Exception as e:
            print(f"Failed to sync timeline from KG: {e}")
            return 0