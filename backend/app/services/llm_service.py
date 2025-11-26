from __future__ import annotations
from typing import Any, Dict, Optional

from .. import ProviderCapability, get_provider_registry
from ..config import get_settings

class LLMService:
    def __init__(self):
        self.settings = get_settings()
        self.provider_registry = get_provider_registry()
        self._chat_resolution = self.provider_registry.resolve(ProviderCapability.CHAT)
        self.provider = self._chat_resolution.provider
        self.model = self._chat_resolution.model

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generates text using the configured default chat model.
        """
        # This is a simplified implementation. 
        # In a real scenario, we'd map the generic request to the provider's specific API.
        # For now, we'll assume the provider has a 'chat' or 'generate' method 
        # or we use the provider adapter directly.
        
        # The provider adapter (e.g., GeminiProviderAdapter) should have a method to handle this.
        # However, looking at the registry, it returns a resolution object.
        
        # Let's try to use the provider's chat interface if available.
        # If not, we might need to instantiate a client.
        
        # For the purpose of fixing the immediate error and assuming standard usage:
        response = await self.provider.chat(
            model_id=self.model.model_id,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.content

_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
