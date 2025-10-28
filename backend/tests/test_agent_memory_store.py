from __future__ import annotations

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from backend.app.storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord

def test_agent_memory_store_round_trip(tmp_path: Path) -> None:
    store = AgentMemoryStore(tmp_path)
    record = AgentThreadRecord(thread_id="thread-1", payload={"messages": ["hello"]})
    store.write(record)
    data = store.read("thread-1")
    assert data == {"messages": ["hello"]}

    store.write(AgentThreadRecord(thread_id="thread-2", payload={"messages": ["hi"]}))
    threads = store.list_threads()
    assert threads == ["thread-1", "thread-2"]

    store.purge(["thread-1"])
    assert "thread-1" not in store.list_threads()


def test_agent_memory_store_validates_payload(tmp_path: Path) -> None:
    store = AgentMemoryStore(tmp_path)
    path = tmp_path / "corrupt.json"
    path.write_text(json.dumps(["not-a-dict"]))
    with pytest.raises(ValueError):
        store.read("corrupt")


def test_agent_memory_store_missing_thread(tmp_path: Path) -> None:
    store = AgentMemoryStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read("missing")
