from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CaliforniaCodesScraper:
    """
    A web scraper for the California Legislative Information website.
    Website: https://leginfo.legislature.ca.gov/faces/codes.xhtml
    
    Features:
    - Search codes by keyword or abbreviation
    - Get specific code sections
    - Upsert to knowledge graph
    """

    def __init__(self, kg_service=None):
        self.base_url = "https://leginfo.legislature.ca.gov"
        self.codes_index_url = f"{self.base_url}/faces/codes.xhtml"
        self.kg_service = kg_service

    async def _fetch_page(self, url: str, params: Dict[str, str] = None) -> BeautifulSoup:
        """Helper to fetch and parse a page."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, follow_redirects=True)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')

    async def _get_code_index_page(self) -> BeautifulSoup:
        """Fetches the main codes index page."""
        return await self._fetch_page(self.codes_index_url)

    async def _parse_code_list(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Parses the main codes index page to get a mapping of code abbreviations to full names and URLs."""
        code_map = {}
        # The structure is typically a table or list of links
        # This is a heuristic based on common patterns, may need adjustment
        for link in soup.find_all('a', href=True):
            if 'codes_displaySection.xhtml' in link['href'] and 'lawCode' in link['href']:
                match = re.search(r'lawCode=([A-Z]+)', link['href'])
                if match:
                    code_abbr = match.group(1)
                    code_name = link.get_text(strip=True)
                    code_map[code_name.upper()] = code_abbr
                    code_map[code_abbr] = code_abbr # Allow searching by abbreviation
        return code_map

    async def search_codes(self, query: str) -> list[dict]:
        """
        Searches for code sections by navigating the site.
        This is still a simplified search. A full search would involve more complex
        navigation or external search engine integration.
        """
        soup = await self._get_code_index_page()
        code_map = await self._parse_code_list(soup)

        results = []
        query_upper = query.upper()

        # Try to find a direct match for a code abbreviation or name
        target_code_abbr = None
        for code_name, abbr in code_map.items():
            if query_upper in code_name.upper() or query_upper == abbr:
                target_code_abbr = abbr
                break
        
        if target_code_abbr:
            # For now, we can't easily list all sections for a code without deeper navigation
            # This would require navigating to the code's main page and parsing its table of contents
            results.append({
                "title": f"Found Code: {target_code_abbr}",
                "summary": f"To get specific sections, use get_code_section with code='{target_code_abbr}' and the section number.",
                "url": f"{self.base_url}/faces/codes_displaySection.xhtml?lawCode={target_code_abbr}&sectionNum=1" # Example URL
            })
        else:
            results.append({
                "title": "Code not found directly",
                "summary": "Could not find a direct match for the query in the list of codes. Try a more specific section number with get_code_section.",
                "url": ""
            })
        
        return results

    async def get_code_section(self, code: str, section: str) -> dict | None:
        """
        Retrieves a specific code section.
        e.g., code='PEN' (Penal Code), section='484'
        """
        search_url = f"{self.base_url}/faces/codes_displaySection.xhtml"
        params = {'lawCode': code.upper(), 'sectionNum': section}

        try:
            soup = await self._fetch_page(search_url, params=params)
            
            content_div = soup.find('div', id='section_content')
            if not content_div:
                # Check for error messages or redirection
                error_message = soup.find('span', class_='ui-messages-error-detail')
                if error_message:
                    return {"error": error_message.get_text(strip=True)}
                return None

            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else f"Section {section} of {code} Code"

            return {
                "title": title,
                "code": code.upper(),
                "section": section,
                "url": str(search_url + "?" + "&".join([f"{k}={v}" for k,v in params.items()])), # Construct URL manually for clarity
                "text": content_div.get_text(separator='\n', strip=True)
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"Code section {code} {section} not found (404)."}
            return {"error": f"HTTP request failed: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred while getting code section {code} {section}: {e}"}

    async def upsert_to_knowledge_graph(self, code_section: Dict[str, Any], case_id: str) -> bool:
        """
        Add a code section to the knowledge graph.
        
        Creates:
        - Statute node with code details
        - Relationship to case if case_id provided
        """
        if not self.kg_service:
            logger.warning("No KG service configured, cannot upsert")
            return False
        
        try:
            code = code_section.get("code", "UNKNOWN")
            section = code_section.get("section", "UNKNOWN")
            entity_id = f"statute:ca:{code}:{section}"
            
            await self.kg_service.add_entity(
                entity_id=entity_id,
                entity_type="Statute",
                properties={
                    "jurisdiction": "California",
                    "code": code,
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
            
            logger.info(f"Upserted CA {code} § {section} to knowledge graph")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert statute to KG: {e}")
            return False

