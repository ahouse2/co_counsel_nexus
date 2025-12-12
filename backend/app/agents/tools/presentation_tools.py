from __future__ import annotations
from typing import Dict, Any, List
from backend.app.services.timeline_service import TimelineService, TimelineEvent
from backend.app.config import get_settings

class TimelineTool:
    """
    A tool for agents to interact with the case timeline.
    """
    name = "timeline_tool"

    def __init__(self):
        self.service = TimelineService()

    def add_event(self, case_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds an event to the timeline for a given case.
        'event_data' should be a dictionary with 'title', 'description', and 'event_date'.
        """
        try:
            event = self.service.add_event(case_id, event_data)
            return event.model_dump()
        except Exception as e:
            return {"error": str(e)}

    def get_timeline(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the full timeline for a given case.
        """
        try:
            events = self.service.get_timeline(case_id)
            return [event.model_dump() for event in events]
        except Exception as e:
            return [{"error": str(e)}]

    def update_event(self, case_id: str, event_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates an event in the timeline.
        """
        try:
            event = self.service.update_event(case_id, event_id, update_data)
            if event:
                return event.model_dump()
            return {"error": f"Event with ID {event_id} not found."}
        except Exception as e:
            return {"error": str(e)}

    def remove_event(self, case_id: str, event_id: str) -> Dict[str, bool | str]:
        """
        Removes an event from the timeline.
        """
        try:
            success = self.service.remove_event(case_id, event_id)
            return {"success": success}
        except Exception as e:
            return {"error": str(e)}

# ExhibitManagerTool and PresentationStateTool would also go here.
# For now, we'll add placeholders.

class ExhibitManagerTool:
    """
    A tool for managing trial exhibits. (Placeholder)
    """
    def designate_exhibit(self, case_id: str, document_id: str, exhibit_number: str) -> Dict[str, Any]:
        # Logic to link a document to an exhibit number would go here.
        print(f"Designating document {document_id} as Exhibit {exhibit_number} for case {case_id}.")
        return {"status": "success", "case_id": case_id, "exhibit_number": exhibit_number}

class PresentationStateTool:
    """
    A tool for managing the state of the Trial HUD. (Placeholder)
    """
    def set_active_exhibit(self, case_id: str, exhibit_number: str) -> Dict[str, Any]:
        # Logic to update the presentation state would go here.
        print(f"Setting active exhibit to {exhibit_number} for case {case_id}.")
        return {"status": "success", "active_exhibit": exhibit_number}