from __future__ import annotations

from typing import Dict

import pytest

from backend.app import get_settings, get_provider_registry, reset_provider_registry_cache
from backend.app.models.api import SettingsUpdateRequest
from backend.app.providers.catalog import ProviderCapability


def _settings_headers(security_materials, *, scopes: list[str]) -> Dict[str, str]:
    settings = get_settings()
    return security_materials.auth_headers(
        scopes=scopes,
        roles=["PlatformEngineer"],
        audience=[settings.security_audience_settings],
    )


def test_settings_default_snapshot(client, security_materials) -> None:
    response = client.get("/settings", headers=_settings_headers(security_materials, scopes=["settings:read"]))
    assert response.status_code == 200
    payload = response.json()

    providers = payload["providers"]
    assert providers["primary"] == "gemini"
    assert providers["defaults"]["chat"] == "gemini-2.5-flash"
    assert providers["defaults"]["embeddings"] == "text-embedding-004"
    assert providers["defaults"]["vision"] == "gemini-2.5-flash"
    assert any(entry["provider_id"] == "gemini" for entry in providers["available"])

    credentials = payload["credentials"]
    provider_status = {entry["provider_id"]: entry["has_api_key"] for entry in credentials["providers"]}
    assert provider_status["gemini"] is False
    assert provider_status["openai"] is False
    assert credentials["services"]["courtlistener"] is False
    assert credentials["services"]["research_browser"] is False

    appearance = payload["appearance"]
    assert appearance["theme"] == "system"


def test_settings_update_persists_and_updates_registry(client, security_materials) -> None:
    headers = _settings_headers(security_materials, scopes=["settings:read", "settings:write"])

    update_payload = {
        "providers": {
            "primary": "openai",
            "secondary": "gemini",
            "defaults": {
                "chat": "gpt-5.0",
                "embeddings": "text-embedding-3-large",
            },
            "api_base_urls": {"openai": "https://api.openai.com/v2"},
            "local_runtime_paths": {"ollama": "/opt/ollama"},
        },
        "credentials": {
            "provider_api_keys": {"openai": "sk-live-secret"},
            "courtlistener_token": "court-token",
        },
        "appearance": {"theme": "dark"},
    }

    response = client.put("/settings", json=update_payload, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    providers = payload["providers"]

    assert providers["primary"] == "openai"
    assert providers["secondary"] == "gemini"
    assert providers["defaults"]["chat"] == "gpt-5.0"
    assert providers["defaults"]["embeddings"] == "text-embedding-3-large"
    assert providers["defaults"]["vision"]
    assert providers["api_base_urls"]["openai"] == "https://api.openai.com/v2"
    assert providers["local_runtime_paths"]["ollama"] == "/opt/ollama"

    provider_status = {entry["provider_id"]: entry["has_api_key"] for entry in payload["credentials"]["providers"]}
    assert provider_status["openai"] is True
    services_status = payload["credentials"]["services"]
    assert services_status["courtlistener"] is True
    assert services_status["research_browser"] is False

    assert payload["appearance"]["theme"] == "dark"

    # Subsequent read reflects persisted changes and does not leak secrets.
    snapshot = client.get("/settings", headers=_settings_headers(security_materials, scopes=["settings:read"]))
    assert snapshot.status_code == 200
    snapshot_payload = snapshot.json()
    assert snapshot_payload["providers"]["primary"] == "openai"
    assert "sk-live-secret" not in str(snapshot_payload)

    # Underlying store keeps secrets encrypted.
    settings = get_settings()
    store_contents = settings.settings_store_path.read_text(encoding="utf-8")
    assert "sk-live-secret" not in store_contents
    assert "court-token" not in store_contents

    # Provider registry picks up updated defaults.
    reset_provider_registry_cache()
    registry = get_provider_registry()
    chat_resolution = registry.resolve(ProviderCapability.CHAT)
    assert chat_resolution.provider.provider_id == "openai"
    assert chat_resolution.model.model_id == "gpt-5.0"
