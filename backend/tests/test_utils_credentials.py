from __future__ import annotations

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pytest

from backend.app.utils.credentials import CredentialRegistry

def test_credential_registry_loads_entries(tmp_path: Path) -> None:
    registry_path = tmp_path / "creds.json"
    registry_path.write_text(json.dumps({"sharepoint": {"client_id": "abc", "secret": "xyz"}}))
    registry = CredentialRegistry(registry_path)

    payload = registry.get("sharepoint")
    assert payload == {"client_id": "abc", "secret": "xyz"}
    payload["client_id"] = "modified"
    # Ensure internal state remains immutable to callers
    assert registry.get("sharepoint")["client_id"] == "abc"

    available = registry.available()
    assert available == {"sharepoint": {"client_id": "abc", "secret": "xyz"}}
    assert "sharepoint" in available


def test_credential_registry_missing_reference(tmp_path: Path) -> None:
    registry = CredentialRegistry(tmp_path / "missing.json")
    with pytest.raises(KeyError):
        registry.get("unknown")
    assert registry.available() == {}


def test_credential_registry_invalid_structure(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps([{"oops": "not-a-dict"}]))
    registry = CredentialRegistry(invalid_path)
    with pytest.raises(ValueError):
        registry.available()


def test_credential_registry_invalid_entry(tmp_path: Path) -> None:
    invalid_entry = tmp_path / "entry.json"
    invalid_entry.write_text(json.dumps({"bad": "should-be-object"}))
    registry = CredentialRegistry(invalid_entry)
    with pytest.raises(ValueError):
        registry.get("bad")
