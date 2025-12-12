"""
Federal Codes Scraper

Scrapes USC (United States Code) from:
- https://uscode.house.gov/ (Official House of Representatives site)
- Cornell LII as fallback (https://www.law.cornell.edu/uscode)

Features:
- Search USC titles
- Get specific sections
- Upsert to knowledge graph
"""
from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# Common USC Titles
USC_TITLES = {
    1: "General Provisions",
    5: "Government Organization and Employees",
    7: "Agriculture",
    11: "Bankruptcy",
    15: "Commerce and Trade",
    17: "Copyrights",
    18: "Crimes and Criminal Procedure",
    26: "Internal Revenue Code",
    28: "Judiciary and Judicial Procedure",
    29: "Labor",
    35: "Patents",
    42: "The Public Health and Welfare",
    47: "Telecommunications",
}


class FederalCodesScraper:
    """
    Scrapes United States Code (USC) for federal law research.
    """
    
    def __init__(self, kg_service=None):
        self.primary_url = "https://uscode.house.gov"
        self.cornell_url = "https://www.law.cornell.edu/uscode"
        self.kg_service = kg_service
    
    async def search_codes(self, query: str, title: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search USC for a query.
        
        Args:
            query: Search term
            title: Optional USC title number (e.g., 18 for criminal code)
        """
        logger.info(f"Searching USC for: {query}")
        
        results = []
        
        try:
            # Use Cornell LII search (more accessible)
            search_url = f"{self.cornell_url}/text"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Cornell has a search endpoint
                params = {"q": query}
                if title:
                    params["title"] = str(title)
                
                response = await client.get(search_url, params=params)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    results = self._parse_cornell_results(soup, query)
                    logger.info(f"Found {len(results)} USC results for '{query}'")
        
        except Exception as e:
            logger.error(f"USC search failed: {e}", exc_info=True)
        
        return results
    
    def _parse_cornell_results(self, soup: BeautifulSoup, query: str) -> List[Dict[str, Any]]:
        """Parse search results from Cornell LII."""
        results = []
        
        # Find result items (Cornell uses specific classes)
        result_items = soup.find_all('div', class_=re.compile(r'search-result|section-content'))
        
        for item in result_items[:10]:
            try:
                # Extract title and link
                link = item.find('a', href=re.compile(r'/uscode/text/'))
                if link:
                    title = link.get_text(strip=True)
                    url = link.get('href', '')
                    if not url.startswith('http'):
                        url = f"https://www.law.cornell.edu{url}"
                    
                    # Try to extract section number from URL
                    section_match = re.search(r'text/(\d+)/(\d+[a-z]*)', url)
                    usc_title = section_match.group(1) if section_match else ""
                    section = section_match.group(2) if section_match else ""
                    
                    results.append({
                        "title": title[:200],
                        "usc_title": usc_title,
                        "section": section,
                        "url": url,
                        "source": "Cornell LII",
                        "query": query
                    })
            except Exception as e:
                logger.debug(f"Failed to parse result: {e}")
        
        return results
    
    async def get_section(self, title: int, section: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific USC section.
        
        Args:
            title: USC title number (e.g., 18)
            section: Section number (e.g., "1341")
        
        Returns:
            Section details or None
        """
        logger.info(f"Fetching {title} U.S.C. § {section}")
        
        url = f"{self.cornell_url}/text/{title}/{section}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract content
                    content_div = soup.find('div', id='content') or soup.find('div', class_='section-content')
                    title_elem = soup.find('h1') or soup.find('title')
                    
                    if content_div:
                        return {
                            "usc_title": str(title),
                            "usc_title_name": USC_TITLES.get(title, f"Title {title}"),
                            "section": section,
                            "title": title_elem.get_text(strip=True) if title_elem else f"{title} U.S.C. § {section}",
                            "text": content_div.get_text(strip=True)[:5000],
                            "url": url,
                            "source": "Cornell LII"
                        }
                
                elif response.status_code == 404:
                    logger.warning(f"Section not found: {title} U.S.C. § {section}")
                    
        except Exception as e:
            logger.error(f"Failed to fetch USC section: {e}")
        
        return None
    
    async def upsert_to_knowledge_graph(self, code_section: Dict[str, Any], case_id: str) -> bool:
        """
        Add a USC section to the knowledge graph.
        """
        if not self.kg_service:
            logger.warning("No KG service configured, cannot upsert")
            return False
        
        try:
            usc_title = code_section.get("usc_title", "0")
            section = code_section.get("section", "0")
            entity_id = f"statute:usc:{usc_title}:{section}"
            
            await self.kg_service.add_entity(
                entity_id=entity_id,
                entity_type="Statute",
                properties={
                    "jurisdiction": "Federal",
                    "code": f"{usc_title} U.S.C.",
                    "usc_title": usc_title,
                    "usc_title_name": code_section.get("usc_title_name", ""),
                    "section": section,
                    "title": code_section.get("title", ""),
                    "text_excerpt": code_section.get("text", "")[:2000],
                    "source_url": code_section.get("url", ""),
                    "scraped_at": datetime.now().isoformat()
                }
            )
            
            # Create relationship to case
            if case_id:
                await self.kg_service.add_relationship(
                    source_id=f"case:{case_id}",
                    relationship_type="REFERENCES_STATUTE",
                    target_id=entity_id,
                    properties={"discovered_via": "research_swarm"}
                )
            
            logger.info(f"Upserted {usc_title} U.S.C. § {section} to knowledge graph")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert statute to KG: {e}")
            return False


class FederalCodesResearchAgent:
    """
    Agent that autonomously researches Federal codes based on case context.
    """
    
    def __init__(self, llm_service=None, kg_service=None):
        self.scraper = FederalCodesScraper(kg_service=kg_service)
        self.llm_service = llm_service
        self.name = "FederalCodesAgent"
    
    async def research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research Federal codes based on query and context.
        """
        logger.info(f"{self.name} researching: {query}")
        
        try:
            # Search for relevant codes
            results = await self.scraper.search_codes(query)
            
            # Upsert to knowledge graph if case_id provided
            case_id = context.get("case_id")
            if case_id and results:
                for result in results[:5]:  # Limit upserts
                    if result.get("usc_title") and result.get("section"):
                        section_data = await self.scraper.get_section(
                            int(result["usc_title"]),
                            result["section"]
                        )
                        if section_data:
                            await self.scraper.upsert_to_knowledge_graph(section_data, case_id)
            
            return {
                "agent": self.name,
                "query": query,
                "results": results,
                "status": "success",
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"{self.name} research failed: {e}")
            return {
                "agent": self.name,
                "query": query,
                "status": "error",
                "error": str(e)
            }


# Factory function
def get_federal_codes_scraper(kg_service=None) -> FederalCodesScraper:
    return FederalCodesScraper(kg_service=kg_service)
