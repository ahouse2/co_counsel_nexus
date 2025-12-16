import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class AutonomousCourtListenerService:
    """
    Service for autonomously monitoring CourtListener for case updates.
    """
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://www.courtlistener.com/api/rest/v3"
        self.monitors = [] # In-memory store for now
        # Structure: { "monitor_id": str, "monitor_type": str, "value": str, ... }

    async def add_monitor(self, monitor_type: str, value: str, requested_by: str, 
                         check_interval_hours: int, priority: str, metadata: Optional[Dict] = None):
        """
        Adds a new monitor.
        """
        import uuid
        monitor_id = str(uuid.uuid4())
        
        # Map to internal structure
        monitor = {
            "monitor_id": monitor_id,
            "monitor_type": monitor_type,
            "value": value,
            "requested_by": requested_by,
            "check_interval_hours": check_interval_hours,
            "priority": priority,
            "metadata": metadata or {},
            "enabled": True,
            "last_check": None,
            "last_results_count": 0,
            "created_at": datetime.now()
        }
        
        # In a real app, save to DB
        self.monitors.append(monitor)
        logger.info(f"Added CourtListener monitor: {value} ({monitor_type})")
        
        # Return object with attribute access (Pydantic model in API expects attributes)
        class MonitorObj:
            def __init__(self, d): self.__dict__ = d
        return MonitorObj(monitor)

    def list_monitors(self) -> List[Dict]:
        return self.monitors

    def remove_monitor(self, monitor_id: str) -> bool:
        initial_len = len(self.monitors)
        self.monitors = [m for m in self.monitors if m["monitor_id"] != monitor_id]
        return len(self.monitors) < initial_len

    async def execute_monitor(self, monitor_id: str) -> Dict:
        """
        Manually triggers a monitor check.
        """
        monitor = next((m for m in self.monitors if m["monitor_id"] == monitor_id), None)
        if not monitor:
            return {"success": False, "error": "Monitor not found"}

        logger.info(f"Executing monitor {monitor_id}: {monitor['value']}")
        
        api_key = self.settings.courtlistener_api_key
        if not api_key:
             raise ValueError("CourtListener API key not configured. Cannot execute real monitor.")

        try:
            results = await self._fetch_from_api(monitor["monitor_type"], monitor["value"], api_key)
            
            ingested_count = 0
            for result in results:
                await self._ingest_opinion(result)
                ingested_count += 1

            monitor["last_check"] = datetime.now()
            monitor["last_results_count"] = len(results)
            
            return {
                "success": True,
                "monitor_id": monitor_id,
                "monitor_type": monitor["monitor_type"],
                "value": monitor["value"],
                "new_opinions": len(results),
                "ingested": ingested_count,
                "total_results": len(results)
            }
        except Exception as e:
            logger.error(f"Monitor execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def _fetch_from_api(self, monitor_type: str, value: str, api_key: str) -> List[Dict]:
        """
        Fetches opinions from CourtListener API.
        """
        url = f"{self.base_url}/search/"
        params = {"q": value, "type": "o", "order_by": "dateFiled desc"}
        
        # Add date filter if we have a last check time? 
        # For now, just getting recent ones.
        
        headers = {"Authorization": f"Token {api_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"CourtListener API error: {response.status} - {text}")
                
                data = await response.json()
                return data.get("results", [])

    async def _ingest_opinion(self, opinion_data: Dict):
        """
        Ingests a single opinion into the Knowledge Graph.
        """
        from backend.app.services.knowledge_graph_service import get_knowledge_graph_service
        kg_service = get_knowledge_graph_service()
        
        # Create Case Node
        case_name = opinion_data.get("caseName", "Unknown Case")
        case_id = f"cl_{opinion_data.get('id', 'unknown')}"
        
        case_props = {
            "id": case_id,
            "name": case_name,
            "docket_number": opinion_data.get("docketNumber", ""),
            "court": opinion_data.get("court", ""),
            "date_filed": opinion_data.get("dateFiled", ""),
            "judge": opinion_data.get("judge", ""),
            "source": "CourtListener"
        }
        
        await kg_service.add_entity("Case", case_props)
        
        # Create Document Node for the opinion text
        # (In a real scenario, we might download the PDF, but here we use the snippet or plain text)
        doc_id = f"doc_{case_id}"
        doc_props = {
            "id": doc_id,
            "title": f"Opinion: {case_name}",
            "type": "Opinion",
            "snippet": opinion_data.get("snippet", "")
        }
        await kg_service.add_entity("Document", doc_props)
        
        # Link Case -> Document
        await kg_service.add_relationship(
            from_entity_id=case_id, from_entity_type="Case",
            to_entity_id=doc_id, to_entity_type="Document",
            relationship_type="HAS_OPINION"
        )


_courtlistener_service = None

def get_autonomous_courtlistener_service():
    global _courtlistener_service
    if not _courtlistener_service:
        _courtlistener_service = AutonomousCourtListenerService()
    return _courtlistener_service
