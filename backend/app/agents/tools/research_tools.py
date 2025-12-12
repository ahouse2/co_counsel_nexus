from __future__ import annotations
from typing import Any, Dict, List

from backend.app.agents.definitions.qa_agents import AgentTool
from backend.app.services.api_clients.courtlistener_client import CourtListenerClient, CaseLawClient
from backend.app.services.api_clients.govinfo_client import GovInfoClient
from backend.app.services.web_scrapers.california_codes_scraper import CaliforniaCodesScraper
from backend.app.services.web_scrapers.ecfr_scraper import ECFRScraper
from backend.app.services.web_scraper_service import WebScraperService
# from backend.app.services.llm_service import get_llm_service # This would be the proper way to get the LLM service

class LegalResearchTool(AgentTool):
    """
    A tool that orchestrates various legal research clients and scrapers.
    """
    def __init__(self):
        super().__init__(
            name="LegalResearchTool",
            description="Orchestrates various legal research clients and scrapers for case law, statutes, and regulations.",
            func=self.search_case_law
        )
        self.courtlistener_client = CourtListenerClient()
        self.caselaw_client = CaseLawClient()
        self.govinfo_client = GovInfoClient()
        self.ca_scraper = CaliforniaCodesScraper()
        self.ecfr_scraper = ECFRScraper()

    async def search_case_law(self, query: str) -> Dict[str, Any]:
        """Searches CourtListener and Case.law for case law."""
        cl_results = await self.courtlistener_client.search_opinions(query)
        cl_caselaw = await self.caselaw_client.search_cases(query)
        return {"courtlistener": cl_results, "caselaw": cl_caselaw}

    async def search_us_code(self, query: str) -> Dict[str, Any]:
        """Searches the US Code via the GovInfo API."""
        return await self.govinfo_client.search(query, collection="USCODE")

    async def get_california_code_section(self, code: str, section: str) -> Dict | None:
        """Retrieves a specific section of the California code."""
        return await self.ca_scraper.get_code_section(code, section)

    async def search_ecfr(self, query: str) -> List[Dict]:
        """Searches the Electronic Code of Federal Regulations."""
        return await self.ecfr_scraper.search(query)

class WebScraperTool(AgentTool):
    """
    A general-purpose tool for scraping web pages.
    """
    def __init__(self):
        super().__init__(
            name="WebScraperTool",
            description="General-purpose web scraper for extracting content from web pages.",
            func=self.scrape_url
        )
        self.scraper = WebScraperService()

    async def scrape_url(self, url: str) -> str:
        """Scrapes the main content from a given URL."""
        return await self.scraper.scrape_page(url)

class ResearchSummarizerTool(AgentTool):
    """
    A tool to summarize research findings using an LLM.
    """
    def __init__(self):
        super().__init__(
            name="ResearchSummarizerTool",
            description="Summarizes research findings using an LLM to provide concise, contextual summaries.",
            func=self.summarize
        )
        from backend.ingestion.llama_index_factory import create_llm_service
        from backend.ingestion.settings import build_runtime_config
        from backend.app.config import get_settings
        
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        self.llm_service = create_llm_service(runtime_config.llm)

    async def summarize(self, text: str, query: str) -> str:
        """
        Summarizes a block of text in the context of a query.
        """
        prompt = f"Please summarize the following text in the context of the query: '{query}'\n\nText: {text[:4000]}..."
        try:
            summary = self.llm_service.generate_text(prompt)
            return summary
        except Exception as e:
            return f"Error generating summary: {e}"