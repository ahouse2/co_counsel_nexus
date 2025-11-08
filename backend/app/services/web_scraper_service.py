from __future__ import annotations
import httpx
from bs4 import BeautifulSoup

class WebScraperService:
    """
    A service to scrape and extract the main content from web pages.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def scrape_page(self, url: str) -> str:
        """
        Fetches the content of a URL and extracts the main text content.

        :param url: The URL to scrape.
        :return: The extracted main text content of the page.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            # Remove common boilerplate elements
            for element in soup(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                element.decompose()

            # Attempt to find the main content area
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: x and 'content' in x)
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                # Fallback to using the whole body if no main content tag is found
                text = soup.body.get_text(separator='\n', strip=True)

            return text

        except httpx.HTTPStatusError as e:
            return f"Error: HTTP request failed with status code {e.response.status_code} for URL: {url}"
        except httpx.RequestError as e:
            return f"Error: An error occurred while requesting the URL: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

class ForensicTechniqueIngestor:
    """
    Uses the WebScraperService to gather information on forensic techniques.
    """
    def __init__(self, scraper: WebScraperService):
        self.scraper = scraper

    async def gather_techniques(self, urls: list[str]) -> str:
        """
        Scrapes a list of URLs and compiles the content.

        :param urls: A list of URLs containing forensic techniques.
        :return: A single string with the compiled content from all URLs.
        """
        compiled_text = ""
        for url in urls:
            content = await self.scraper.scrape_page(url)
            compiled_text += f"--- Content from {url} ---\n\n{content}\n\n"
        
        return compiled_text