from __future__ import annotations

import pytest

from backend.app import (
    ProviderCapability,
    get_provider_registry,
    get_settings,
    reset_provider_registry_cache,
)
from backend.app.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistry,
)


@pytest.fixture(autouse=True)
def _reset_registry_cache() -> None:
    """Ensure each test exercises a fresh registry instance."""

    reset_provider_registry_cache()
    yield
    reset_provider_registry_cache()


def test_registry_uses_settings_defaults() -> None:
    registry = get_provider_registry()
    settings = get_settings()

    chat_resolution = registry.resolve(ProviderCapability.CHAT)
    embedding_resolution = registry.resolve(ProviderCapability.EMBEDDINGS)
    vision_resolution = registry.resolve(ProviderCapability.VISION)

    assert chat_resolution.provider.provider_id == settings.model_providers_primary
    assert chat_resolution.model.model_id == settings.default_chat_model
    assert embedding_resolution.model.model_id == settings.default_embedding_model
    assert vision_resolution.model.model_id == settings.default_vision_model
    assert get_provider_registry() is registry  # cached instance reused


def test_registry_override_selects_matching_provider() -> None:
    registry = ProviderRegistry(
        primary_provider="openai",
        secondary_provider="gemini",
        api_base_urls={},
        runtime_paths={},
        model_overrides={ProviderCapability.CHAT: "gemini-1.5-pro"},
    )

    resolution = registry.resolve(ProviderCapability.CHAT)

    assert resolution.provider.provider_id == "gemini"
    assert resolution.model.model_id == "gemini-1.5-pro"


def test_registry_falls_back_when_primary_lacks_capability() -> None:
    registry = ProviderRegistry(
        primary_provider="llama.cpp",
        secondary_provider="openai",
        api_base_urls={},
        runtime_paths={},
    )

    resolution = registry.resolve(ProviderCapability.VISION)

    assert resolution.provider.provider_id == "openai"
    assert ProviderCapability.VISION in resolution.model.capabilities


def test_unknown_provider_raises() -> None:
    registry = ProviderRegistry(
        primary_provider="openai",
        secondary_provider=None,
        api_base_urls={},
        runtime_paths={},
    )

    with pytest.raises(ProviderNotFoundError):
        registry.get_adapter("does-not-exist")


def test_registry_ignores_missing_override_but_keeps_capability() -> None:
    registry = ProviderRegistry(
        primary_provider="openai",
        secondary_provider="gemini",
        api_base_urls={},
        runtime_paths={},
        model_overrides={ProviderCapability.VISION: "non-existent-model"},
    )

    resolution = registry.resolve(ProviderCapability.VISION)

    assert resolution.model.model_id in {
        model.model_id
        for model in registry.get_adapter(resolution.provider.provider_id).list_vision_models()
    }

