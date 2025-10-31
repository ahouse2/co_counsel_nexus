"""Backend application package exports."""
from __future__ import annotations

from functools import lru_cache
from typing import Mapping

from .config import Settings, get_settings
from .providers.catalog import ProviderCapability
from .providers.registry import (
    ProviderRegistry,
    get_provider_registry as _get_provider_registry,
    reset_provider_registry_cache as _reset_registry_cache,
)


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    """Return the configured provider registry."""

    settings = get_settings()
    model_overrides: Mapping[ProviderCapability, str | None] = {
        ProviderCapability.CHAT: settings.default_chat_model,
        ProviderCapability.EMBEDDINGS: settings.default_embedding_model,
        ProviderCapability.VISION: settings.default_vision_model,
    }
    return _get_provider_registry(
        primary_provider=settings.model_providers_primary,
        secondary_provider=settings.model_providers_secondary,
        api_base_urls=settings.provider_api_base_urls,
        runtime_paths=settings.provider_local_runtime_paths,
        model_overrides=model_overrides,
    )


def reset_provider_registry_cache() -> None:
    """Clear the cached registry factory for testing."""

    _reset_registry_cache()
    get_provider_registry.cache_clear()


__all__ = [
    "Settings",
    "get_settings",
    "ProviderCapability",
    "ProviderRegistry",
    "get_provider_registry",
    "reset_provider_registry_cache",
]
