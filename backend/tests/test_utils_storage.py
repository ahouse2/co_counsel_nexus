from __future__ import annotations

from pathlib import Path

import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pytest

from backend.app.utils.storage import atomic_write_json, read_json, safe_path, sanitise_identifier

def test_sanitise_identifier_normalises_values() -> None:
    assert sanitise_identifier("../weird\nname") == "weird_name"
    hashed = sanitise_identifier("!!!")
    assert len(hashed) == 64  # sha256 fallback


def test_safe_path_guards_traversal(tmp_path: Path) -> None:
    safe = safe_path(tmp_path, "case::id")
    assert safe.parent == tmp_path.resolve()
    escape = safe_path(tmp_path, "../../escape")
    assert escape.parent == tmp_path.resolve()
    assert escape.name.endswith(".json")


def test_atomic_write_and_read_json(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"
    atomic_write_json(target, {"value": 1})
    assert target.exists()
    assert read_json(target) == {"value": 1}

    with target.open("w", encoding="utf-8") as handle:
        handle.write("not-json")
    with pytest.raises(json.JSONDecodeError):
        read_json(target)
