import pytest
from backend.app.providers.registry import get_provider_registry, ProviderCapability, ProviderNotFoundError
from pathlib import Path

def test_provider_registry_initialization():
    registry = get_provider_registry(
        primary_provider="openai",
        secondary_provider="gemini",
        api_base_urls={"openai": "https://api.openai.com/v1"},
        runtime_paths={},
        model_overrides={}
    )
    assert registry is not None
    assert "openai" in registry.list_providers()
    assert "gemini" in registry.list_providers()

def test_provider_registry_resolution():
    registry = get_provider_registry(
        primary_provider="openai",
        secondary_provider=None,
        api_base_urls={},
        runtime_paths={},
        model_overrides={}
    )
    
    # Test resolving chat capability
    resolution = registry.resolve(ProviderCapability.CHAT)
    assert resolution.provider.provider_id == "openai"
    assert resolution.model.capabilities[0] == ProviderCapability.CHAT

def test_provider_registry_get_adapter():
    registry = get_provider_registry(
        primary_provider="openai",
        secondary_provider=None,
        api_base_urls={},
        runtime_paths={},
        model_overrides={}
    )
    
    adapter = registry.get_adapter("openai")
    assert adapter.provider_id == "openai"
    assert adapter.display_name == "OpenAI"
    
    with pytest.raises(ProviderNotFoundError):
        registry.get_adapter("non_existent_provider")

def test_provider_registry_model_override():
    registry = get_provider_registry(
        primary_provider="openai",
        secondary_provider=None,
        api_base_urls={},
        runtime_paths={},
        model_overrides={ProviderCapability.CHAT: "gpt-4o"}
    )
    
    resolution = registry.resolve(ProviderCapability.CHAT)
    assert resolution.model.model_id == "gpt-4o"
