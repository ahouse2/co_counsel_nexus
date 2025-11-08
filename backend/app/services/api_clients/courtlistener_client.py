from __future__ import annotations
import httpx
from typing import Any, Dict, Optional

from backend.app.config import get_settings

class CourtListenerClient:
    """
    An API client for interacting with the CourtListener API.
    API documentation: https://www.courtlistener.com/help/api/
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.courtlistener_token
        self.base_url = settings.courtlistener_endpoint
        if not self.api_key:
            raise ValueError("CourtListener API key is not configured.")

    async def search_opinions(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Searches for opinions in the CourtListener database.

        :param query: The search query.
        :param kwargs: Additional search parameters as defined in the API docs.
        :return: The JSON response from the API.
        """
        headers = {"Authorization": f"Token {self.api_key}"}
        params = {"q": query, **kwargs}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # Log the error and return a structured error message
                # In a real app, you'd use a proper logger
                print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
                return {"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}
            except httpx.RequestError as e:
                print(f"An error occurred while requesting {e.request.url!r}.")
                return {"error": "Request failed", "details": str(e)}

class CaseLawClient:
    """
    An API client for interacting with the Case.law API.
    API documentation: https://case.law/docs/
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.caselaw_api_key
        self.base_url = settings.caselaw_endpoint
        if not self.api_key:
            raise ValueError("Case.law API key is not configured.")

    async def search_cases(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Searches for cases in the Case.law database.

        :param query: The search query.
        :param kwargs: Additional search parameters.
        :return: The JSON response from the API.
        """
        headers = {"Authorization": f"Token {self.api_key}"}
        params = {"search": query, **kwargs}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
                return {"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}
            except httpx.RequestError as e:
                print(f"An error occurred while requesting {e.request.url!r}.")
                return {"error": "Request failed", "details": str(e)}