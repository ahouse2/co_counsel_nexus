import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class AutonomousScraperService:
    """
    Service for autonomously scraping websites for legal updates.
    """
    def __init__(self):
        self.triggers = [] 
        # Structure: { "trigger_id": str, "source": str, "query": str, ... }

    async def add_trigger(self, source: str, query: str, frequency: str, 
                         requested_by: str, priority: str, metadata: Optional[Dict] = None):
        import uuid
        trigger_id = str(uuid.uuid4())
        
        trigger = {
            "trigger_id": trigger_id,
            "source": source,
            "query": query,
            "frequency": frequency,
            "requested_by": requested_by,
            "priority": priority,
            "metadata": metadata or {},
            "enabled": True,
            "last_run": None,
            "created_at": datetime.now()
        }
        self.triggers.append(trigger)
        logger.info(f"Added scraper trigger: {source} - {query}")
        
        class TriggerObj:
            def __init__(self, d): self.__dict__ = d
        return TriggerObj(trigger)

    def list_triggers(self) -> List[Dict]:
        return self.triggers

    def remove_trigger(self, trigger_id: str) -> bool:
        initial_len = len(self.triggers)
        self.triggers = [t for t in self.triggers if t["trigger_id"] != trigger_id]
        return len(self.triggers) < initial_len

    async def execute_trigger(self, trigger_id: str) -> Dict:
        trigger = next((t for t in self.triggers if t["trigger_id"] == trigger_id), None)
        if not trigger:
            return {"success": False, "error": "Trigger not found"}

        logger.info(f"Executing trigger {trigger_id}: {trigger['source']}")
        
        # Determine URL based on source/query (simplified mapping for now)
        url = self._resolve_url(trigger["source"], trigger["query"])
        
        try:
            content = await self._scrape_url(url)
            ingested = await self._ingest_content(content, trigger["source"], trigger["query"])
            
            trigger["last_run"] = datetime.now()
            
            return {
                "success": True,
                "trigger_id": trigger_id,
                "source": trigger["source"],
                "query": trigger["query"],
                "total_results": 1, # 1 URL scraped
                "ingested": 1 if ingested else 0,
                "skipped": 0 if ingested else 1
            }
        except Exception as e:
            logger.error(f"Trigger execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def scrape_and_ingest(self, source: str, query: str) -> Dict:
        """
        Ad-hoc scrape request.
        """
        logger.info(f"Manual scrape: {source} - {query}")
        url = self._resolve_url(source, query)
        
        try:
            content = await self._scrape_url(url)
            ingested = await self._ingest_content(content, source, query)
            
            return {
                "success": True,
                "source": source,
                "query": query,
                "total_results": 1,
                "ingested": 1 if ingested else 0,
                "skipped": 0 if ingested else 1
            }
        except Exception as e:
            logger.error(f"Manual scrape failed: {e}")
            return {"success": False, "error": str(e)}

    def _resolve_url(self, source: str, query: str) -> str:
        # Basic mapping for demo purposes - in real app this would be more sophisticated
        if source == "california_codes":
            # Example: Search CA codes (this is a placeholder URL structure, would need real search endpoint)
            return f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode={query.split(' ')[0]}&sectionNum={query.split(' ')[-1]}"
        elif source == "ecfr":
            return f"https://www.ecfr.gov/current/title-{query.split(' ')[-1]}"
        else:
            # Assume query is a direct URL if source is generic
            if query.startswith("http"):
                return query
            return f"https://www.google.com/search?q={query}"

    async def _scrape_url(self, url: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Scraping error: {response.status}")
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Basic extraction
                title = soup.title.string if soup.title else "No Title"
                text = soup.get_text(separator=' ', strip=True)[:5000] # Limit text length
                
                return {
                    "url": url,
                    "title": title,
                    "text": text
                }

    async def _ingest_content(self, content: Dict, source: str, query: str) -> bool:
        try:
            from backend.app.services.knowledge_graph_service import get_knowledge_graph_service
            kg_service = get_knowledge_graph_service()
            
            logger.info(f"Ingesting content from {content['url']}")
            
            # Create WebResource Node
            resource_id = f"web_{hash(content['url'])}"
            resource_props = {
                "id": resource_id,
                "url": content["url"],
                "title": content["title"],
                "source": source,
                "query": query,
                "ingested_at": datetime.now().isoformat()
            }
            await kg_service.add_entity("WebResource", resource_props)
            logger.info(f"Created WebResource node: {resource_id}")
            
            # Create Document Node for content
            doc_id = f"doc_{resource_id}"
            doc_props = {
                "id": doc_id,
                "title": content["title"],
                "type": "WebPage",
                "text_preview": content["text"][:200]
            }
            await kg_service.add_entity("Document", doc_props)
            logger.info(f"Created Document node: {doc_id}")
            
            await kg_service.add_relationship(
                from_entity_id=resource_id, from_entity_type="WebResource",
                to_entity_id=doc_id, to_entity_type="Document",
                relationship_type="HAS_CONTENT"
            )
            logger.info("Created HAS_CONTENT relationship")
            return True
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return False

_scraper_service = None

def get_autonomous_scraper_service():
    global _scraper_service
    if not _scraper_service:
        _scraper_service = AutonomousScraperService()
    return _scraper_service
