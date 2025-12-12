from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional

from .. import ProviderCapability, get_provider_registry
from ..config import get_settings
from backend.ingestion.llama_index_factory import create_llm_service
from backend.ingestion.settings import build_llm_config

class LLMService:
    def __init__(self):
        self.settings = get_settings()
        # We still keep provider registry for metadata if needed, but use factory for actual service
        self.provider_registry = get_provider_registry()
        self._chat_resolution = self.provider_registry.resolve(ProviderCapability.CHAT)
        
        # Initialize the actual LLM service using the ingestion factory
        llm_config = build_llm_config(self.settings)
        self.real_service = create_llm_service(llm_config)

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generates text using the configured default chat model.
        """
        # Run the synchronous generate_text in a thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.real_service.generate_text, prompt)

_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
