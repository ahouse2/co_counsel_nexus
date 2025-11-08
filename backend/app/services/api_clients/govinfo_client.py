from __future__ import annotations
import httpx
from typing import Any, Dict, Optional

from backend.app.config import get_settings

class GovInfoClient:
    """
    An API client for interacting with the GovInfo API.
    API documentation: https://api.govinfo.gov/docs/
    """

    def __init__(self, api_key: Optional[str] = None):
        # Assuming the API key is stored in a setting like `govinfo_api_key`
        # For now, let's imagine it's in a general-purpose secrets dictionary
        # or a dedicated setting. Let's call it `govinfo_api_key`.
        # settings = get_settings()
        # self.api_key = api_key or settings.govinfo_api_key
        settings = get_settings()
        self.api_key = api_key or settings.govinfo_api_key
        self.base_url = "https://api.govinfo.gov"

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Performs a search across all collections.

        :param query: The search query.
        :param kwargs: Additional search parameters (e.g., pageSize, offset).
        :return: The JSON response from the API.
        """
        endpoint = f"{self.base_url}/search"
        params = {"query": query, "api_key": self.api_key, **kwargs}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}
            except httpx.RequestError as e:
                return {"error": "Request failed", "details": str(e)}

    async def get_collection_summary(self, collection_code: str) -> Dict[str, Any]:
        """
        Retrieves the summary for a specific collection.

        :param collection_code: The code for the collection (e.g., 'USCODE').
        :return: The JSON response from the API.
        """
        endpoint = f"{self.base_url}/collections/{collection_code}"
        params = {"api_key": self.api_key}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}
            except httpx.RequestError as e:
                return {"error": "Request failed", "details": str(e)}

    async def get_package_details(self, package_id: str) -> Dict[str, Any]:
        """
        Retrieves details for a specific package.

        :param package_id: The ID of the package (e.g., 'USCODE-2022-title1-partI-chapter1-sec1_1').
        :return: The JSON response from the API.
        """
        endpoint = f"{self.base_url}/packages/{package_id}/summary"
        params = {"api_key": self.api_key}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": "API request failed", "status_code": e.response.status_code, "details": e.response.text}
            except httpx.RequestError as e:
                return {"error": "Request failed", "details": str(e)}