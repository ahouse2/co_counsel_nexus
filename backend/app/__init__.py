"""Backend application package exports."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Mapping

from .config import Settings, get_settings
from .providers.catalog import ProviderCapability
from .providers.registry import (
    ProviderRegistry,
    get_provider_registry as _get_provider_registry,
    reset_provider_registry_cache as _reset_registry_cache,
)
from .services.settings import SettingsService


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    """Return the configured provider registry."""

    settings = get_settings()
    settings_service = SettingsService(runtime_settings=settings)
    provider_snapshot = settings_service.snapshot().providers
    model_overrides: Mapping[ProviderCapability, str | None] = {
        ProviderCapability.CHAT: provider_snapshot.defaults.get("chat"),
        ProviderCapability.EMBEDDINGS: provider_snapshot.defaults.get("embeddings"),
        ProviderCapability.VISION: provider_snapshot.defaults.get("vision"),
    }
    runtime_paths = {
        provider_id: Path(path)
        for provider_id, path in provider_snapshot.local_runtime_paths.items()
        if path
    }
    return _get_provider_registry(
        primary_provider=provider_snapshot.primary or settings.model_providers_primary,
        secondary_provider=provider_snapshot.secondary or settings.model_providers_secondary,
        api_base_urls=provider_snapshot.api_base_urls,
        runtime_paths=runtime_paths,
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
