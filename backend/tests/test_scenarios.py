from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pytest

from backend.app.scenarios.registry import ScenarioRegistry
from backend.app.services.errors import WorkflowAbort
from backend.app.services.scenarios import (
    ScenarioEngine,
    ScenarioEvidenceBinding,
    ScenarioRunOptions,
    get_scenario_engine,
)
from backend.app.storage.agent_memory_store import AgentMemoryStore


class _StubAgentsService:
    def __init__(self, root: Path) -> None:
        self.memory_store = AgentMemoryStore(root)

    def run_case(  # type: ignore[override]
        self,
        case_id: str,
        question: str,
        *,
        top_k: int | None = None,
        principal=None,
    ) -> Dict[str, object]:
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "thread_id": f"thread-{case_id}-{abs(hash(question)) % 10000}",
            "case_id": case_id,
            "question": question,
            "created_at": timestamp,
            "updated_at": timestamp,
            "status": "succeeded",
            "turns": [],
            "final_answer": f"Dynamic response for: {question}",
            "citations": [],
            "qa_scores": {},
            "qa_notes": [],
            "telemetry": {"total_duration_ms": 12.5},
            "errors": [],
            "memory": {},
        }


def _library_path() -> Path:
    return Path(__file__).resolve().parents[1] / "app" / "scenarios" / "library"


def test_scenario_engine_run(tmp_path: Path) -> None:
    registry = ScenarioRegistry(_library_path())
    agents = _StubAgentsService(tmp_path / "threads")
    engine = ScenarioEngine(
        registry=registry,
        agents_service=agents,
        memory_store=agents.memory_store,
        tts_service=None,
    )
    scenario = registry.get("cross_examination_smith")
    options = ScenarioRunOptions(
        scenario_id=scenario.id,
        case_id="case-001",
        variables={
            "issue": "Chain of custody gap",
            "witness_fact": "The hand-off occurred at 21:07",
            "timeframe": "January 12 2025 21:00-21:15",
        },
        evidence={
            "primary_document": ScenarioEvidenceBinding(
                slot_id="primary_document",
                value="Exhibit 12",
                document_id="doc-primary",
            ),
            "timeline_event": ScenarioEvidenceBinding(
                slot_id="timeline_event",
                value="Timeline entry 42",
            ),
        },
        participants=[participant.id for participant in scenario.participants],
        use_tts=False,
    )
    result = engine.run(options)
    assert result["run_id"]
    assert len(result["transcript"]) == len(scenario.beats)
    assert all(turn["text"].startswith("Dynamic response") for turn in result["transcript"] if turn["kind"] == "dynamic")
    stored_runs = agents.memory_store.list_scenarios()
    assert stored_runs, "Scenario transcript was not persisted"


def test_scenario_engine_rejects_inactive_participant(tmp_path: Path) -> None:
    registry = ScenarioRegistry(_library_path())
    agents = _StubAgentsService(tmp_path / "threads_inactive")
    engine = ScenarioEngine(
        registry=registry,
        agents_service=agents,
        memory_store=agents.memory_store,
        tts_service=None,
    )
    scenario = registry.get("cross_examination_smith")
    inactive_participant = "witness"
    assert any(p.id == inactive_participant and p.optional for p in scenario.participants)

    options = ScenarioRunOptions(
        scenario_id=scenario.id,
        case_id="case-omit-witness",
        variables={
            "issue": "Chain of custody gap",
            "witness_fact": "The hand-off occurred at 21:07",
            "timeframe": "January 12 2025 21:00-21:15",
        },
        evidence={
            "primary_document": ScenarioEvidenceBinding(
                slot_id="primary_document",
                value="Exhibit 12",
            ),
            "timeline_event": ScenarioEvidenceBinding(
                slot_id="timeline_event",
                value="Timeline entry 42",
            ),
        },
        participants=[p.id for p in scenario.participants if p.id != inactive_participant],
        use_tts=False,
    )

    with pytest.raises(WorkflowAbort) as exc:
        engine.run(options)

    assert exc.value.error.code == "SCENARIO_PARTICIPANT_INACTIVE"


def test_scenarios_api_endpoints(client, auth_headers_factory, tmp_path: Path) -> None:
    registry = ScenarioRegistry(_library_path())
    agents = _StubAgentsService(tmp_path / "scenario_threads")
    engine = ScenarioEngine(
        registry=registry,
        agents_service=agents,
        memory_store=agents.memory_store,
        tts_service=None,
    )
    app = client.app
    app.dependency_overrides[get_scenario_engine] = lambda: engine

    list_headers = auth_headers_factory(
        scopes=["agents:read"],
        roles=["ResearchAnalyst"],
        audience=["co-counsel.agents"],
    )
    response = client.get("/scenarios", headers=list_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["scenarios"]

    scenario_id = "cross_examination_smith"
    detail_headers = auth_headers_factory(
        scopes=["agents:read"],
        roles=["ResearchAnalyst"],
        audience=["co-counsel.agents"],
    )
    detail_response = client.get(f"/scenarios/{scenario_id}", headers=detail_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["scenario_id"] == scenario_id

    run_headers = auth_headers_factory(
        scopes=["agents:run"],
        roles=["ResearchAnalyst"],
        audience=["co-counsel.agents"],
    )
    run_payload = {
        "scenario_id": scenario_id,
        "case_id": "case-777",
        "participants": [participant["id"] for participant in detail["participants"]],
        "variables": {
            "issue": "Authentication failure",
            "witness_fact": "Logs show dual access",
            "timeframe": "January 12 2025 21:00-21:15",
        },
        "evidence": {
            "primary_document": {"value": "Exhibit Alpha", "document_id": "doc-alpha"},
            "timeline_event": {"value": "Timeline marker"},
        },
        "enable_tts": False,
    }
    run_response = client.post("/scenarios/run", headers=run_headers, json=run_payload)
    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["run_id"]
    assert len(run_data["transcript"]) == len(detail["beats"])

    tts_response = client.post("/tts/speak", headers=run_headers, json={"text": "Hello"})
    assert tts_response.status_code == 503

    app.dependency_overrides.pop(get_scenario_engine, None)
