from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from backend.app import config
from backend.app.agents.context import AgentContext
from backend.app.agents.memory import CaseThreadMemory
from backend.app.agents.tools import ForensicsTool
from backend.app.agents.types import AgentThread
from backend.app.services.forensics import ForensicsService
from backend.app.storage.agent_memory_store import AgentMemoryStore


class _StubDocumentStore:
    def __init__(self, records: dict[str, dict[str, object]]) -> None:
        self._records = records

    def read_document(self, doc_id: str) -> dict[str, object]:
        return dict(self._records[doc_id])

    def list_documents(self) -> list[dict[str, object]]:  # pragma: no cover - unused here
        return [dict(item) for item in self._records.values()]


@pytest.fixture()
def forensics_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ForensicsService:
    forensics_dir = tmp_path / "forensics"
    chain_path = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("FORENSICS_DIR", str(forensics_dir))
    monkeypatch.setenv("FORENSICS_CHAIN_PATH", str(chain_path))
    config.reset_settings_cache()
    return ForensicsService()


def _build_dfir_document(service: ForensicsService, tmp_path: Path) -> None:
    doc_path = tmp_path / "dfir.txt"
    doc_path.write_text("Unauthorized access detected\nCredential dump located\n")
    nodes = [
        {
            "node_id": "dfir-1::0",
            "chunk_index": 0,
            "text": "Unauthorized access detected",
            "metadata": {"source_type": "local"},
            "embedding": [1.0, 0.0, 0.0],
        },
        {
            "node_id": "dfir-1::1",
            "chunk_index": 1,
            "text": "Unauthorized access detected",
            "metadata": {"source_type": "local"},
            "embedding": [1.0, 0.0, 0.0],
        },
        {
            "node_id": "dfir-1::2",
            "chunk_index": 2,
            "text": "Credential dump located with entropy !!!",
            "metadata": {"source_type": "local"},
            "embedding": [4.0, 4.0, 4.0],
        },
    ]
    service.build_document_artifact("dfir-1", doc_path, nodes=nodes)


def _build_financial_ledger(service: ForensicsService, tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.csv"
    frame = pd.DataFrame(
        {
            "entity": ["A", "A", "B", "C", "C"],
            "amount": [Decimal("100"), Decimal("100"), Decimal("200"), Decimal("2500"), Decimal("2600")],
            "balance": [Decimal("100"), Decimal("110"), Decimal("210"), Decimal("5000"), Decimal("5100")],
        }
    )
    frame.to_csv(ledger_path, index=False)
    service.build_financial_artifact("fin-1", ledger_path)


def test_forensics_tool_directives_trigger_connectors(
    forensics_service: ForensicsService, tmp_path: Path
) -> None:
    _build_dfir_document(forensics_service, tmp_path)
    _build_financial_ledger(forensics_service, tmp_path)

    document_store = _StubDocumentStore(
        {
            "dfir-1": {"id": "dfir-1", "type": "document"},
            "fin-1": {"id": "fin-1", "type": "financial"},
        }
    )
    tool = ForensicsTool(document_store, forensics_service)

    memory_store = AgentMemoryStore(tmp_path / "memory")
    now = datetime.now(timezone.utc)
    thread = AgentThread(
        thread_id="thread-1",
        case_id="case-1",
        question="Investigate breach and ledger anomalies",
        created_at=now,
        updated_at=now,
    )
    memory = CaseThreadMemory(thread, memory_store)
    context = AgentContext(
        case_id="case-1",
        question="Investigate breach and ledger anomalies",
        top_k=5,
        actor={"id": "unit-test"},
        memory=memory,
        telemetry={},
    )

    retrieval_payload = {
        "answer": "Potential breach detected.",
        "citations": [
            {"docId": "dfir-1", "span": "Unauthorized access"},
            {"docId": "fin-1", "span": "Ledger anomaly"},
        ],
        "traces": {
            "vector": [
                {
                    "docId": "dfir-1",
                    "score": 0.95,
                    "chunkIndex": 2,
                    "sourceType": "local",
                    "textPreview": "Credential dump located",
                }
            ],
            "graph": {"nodes": [], "edges": []},
            "forensics": [],
            "privilege": {
                "decisions": [
                    {
                        "doc_id": "dfir-1",
                        "label": "privileged",
                        "score": 0.92,
                        "explanation": "subject=breach",
                    }
                ],
                "aggregate": {
                    "label": "privileged",
                    "flagged": ["dfir-1"],
                    "score": 0.92,
                    "rationale": "max=dfir-1:0.92; avg=0.92; flagged=1",
                },
            },
        },
    }
    memory.update("insights", {"retrieval": retrieval_payload})
    memory.update("directives", {"dfir": True, "financial": True})

    turn, bundle = tool.execute(context)

    connectors = bundle.get("connectors", {})
    assert "dfir" in connectors
    assert connectors["dfir"]["status"] == "reported"
    assert connectors["dfir"]["findings"], "DFIR findings should surface"
    assert "financial" in connectors
    assert connectors["financial"]["ledgers"], "Financial ledger summary should surface"
    assert context.memory.state.get("artifacts", {}).get("connectors") == connectors
    assert turn.metrics["connectors"]
