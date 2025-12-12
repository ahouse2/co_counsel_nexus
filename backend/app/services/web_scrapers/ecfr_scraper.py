from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class ECFRScraper:
    """
    A web scraper for the Electronic Code of Federal Regulations (eCFR).
    Website: https://www.ecfr.gov/
    """

    def __init__(self):
        self.base_url = "https://www.ecfr.gov"

    async def get_regulation(self, title: int, part: int, section: str) -> dict | None:
        """
        Retrieves a specific regulation from the eCFR.
        e.g., title=12, part=205, section="205.1"

        :param title: The title number of the CFR.
        :param part: The part number of the CFR.
        :param section: The section number.
        """
        # The URL structure is generally predictable
        url = f"{self.base_url}/current/title-{title}/part-{part}/section-{section}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'lxml')
                
                # The main content is usually in a div with a 'section' class
                content_div = soup.find('div', class_='section')
                if not content_div:
                    return None

                title_tag = soup.find('h1')
                title_text = title_tag.get_text(strip=True) if title_tag else "Title not found"

                return {
                    "title": title_text,
                    "url": url,
                    "text": content_div.get_text(separator='\n', strip=True)
                }

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {"error": "Regulation not found", "url": url}
                return {"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}
            except Exception as e:
                return {"error": "An unexpected error occurred", "details": str(e)}

    async def search(self, query: str) -> list[dict]:
        """
        Performs a search on the eCFR website.
        """
        search_url = f"{self.base_url}/search/results"
        params = {'q': query}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(search_url, params=params, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'lxml')
                
                results = []
                for result_item in soup.find_all('li', class_='result-item'):
                    title_tag = result_item.find('h4')
                    link_tag = title_tag.find('a') if title_tag else None
                    summary_tag = result_item.find('p', class_='snippet')

                    if title_tag and link_tag:
                        results.append({
                            "title": title_tag.get_text(strip=True),
                            "url": urljoin(self.base_url, link_tag['href']),
                            "summary": summary_tag.get_text(strip=True) if summary_tag else ""
                        })
                
                return results

            except httpx.HTTPStatusError as e:
                return [{"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}]
            except Exception as e:
                return [{"error": "An unexpected error occurred", "details": str(e)}]
    
    async def search_regulations(self, query: str) -> list[dict]:
        """Alias for search method for consistency."""
        return await self.search(query)