from __future__ import annotations

import logging
from typing import Dict, List, Any

import httpx
from fastapi import HTTPException, status

from ...config import Settings, get_settings
from ...utils.credentials import CredentialRegistry
from ..services.ingestion_sources import CourtListenerSourceConnector

LOGGER = logging.getLogger(__name__)

class LegalResearchService:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        credential_registry: CredentialRegistry = Depends(CredentialRegistry),
    ) -> None:
        self.settings = settings
        self.credential_registry = credential_registry
        self.courtlistener_connector = CourtListenerSourceConnector(
            settings, credential_registry, LOGGER
        )

    async def search_courtlistener(
        self, query: str, cred_ref: str, page_size: int = 10, max_pages: int = 1
    ) -> List[Dict[str, Any]]:
        credentials = self.credential_registry.get(cred_ref)
        token = credentials.get("token") or credentials.get("api_key")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Credential {cred_ref} missing 'token' or 'api_key' for CourtListener",
            )

        # This is a simplified approach. In a real scenario, you'd adapt
        # CourtListenerSourceConnector's _materialize_async or create a new method
        # for direct search without materializing to disk.
        # For now, we'll simulate a direct search using its internal request logic.

        endpoint = credentials.get("endpoint") or self.courtlistener_connector._DEFAULT_ENDPOINT
        headers = self.courtlistener_connector._headers(token)
        params = {"q": query, "page_size": page_size}
        
        results = []
        next_url = endpoint
        page_count = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while next_url and page_count < max_pages:
                response = await self.courtlistener_connector._request(client, next_url, headers=headers, params=params if page_count == 0 else None)
                payload = response.json()
                results.extend(payload.get("results", []))
                next_url = payload.get("next")
                page_count += 1
        
        return results

def get_legal_research_service() -> LegalResearchService:
    return LegalResearchService()
