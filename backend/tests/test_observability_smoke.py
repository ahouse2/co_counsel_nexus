import importlib
import json
from pathlib import Path
from typing import Iterable

import pytest


_MODULE_INSTRUMENTS: list[tuple[str, Iterable[tuple[str, str]], bool]] = [
    (
        "backend.app.services.agents",
        (
            ("_agents_runs_counter", "add"),
            ("_agents_run_duration", "record"),
            ("_agents_failure_counter", "add"),
        ),
        False,
    ),
    (
        "backend.app.services.knowledge",
        (
            ("_knowledge_search_counter", "add"),
            ("_knowledge_lessons_counter", "add"),
            ("_knowledge_bookmarks_counter", "add"),
            ("_knowledge_progress_counter", "add"),
        ),
        False,
    ),
    (
        "backend.app.services.scenarios",
        (
            ("_scenario_runs_counter", "add"),
            ("_scenario_run_duration", "record"),
            ("_scenario_beats_counter", "add"),
        ),
        False,
    ),
    (
        "backend.app.services.voice.service",
        (
            ("_voice_sessions_counter", "add"),
            ("_voice_session_duration", "record"),
            ("_voice_transcription_latency", "record"),
        ),
        True,
    ),
    (
        "backend.app.services.ingestion",
        (
            ("_ingestion_jobs_counter", "add"),
            ("_ingestion_job_duration", "record"),
        ),
        True,
    ),
]


def test_metric_instruments_register() -> None:
    validated_modules: list[str] = []
    skipped_modules: list[str] = []

    for module_name, instruments, optional in _MODULE_INSTRUMENTS:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if optional:
                skipped_modules.append(module_name)
                continue
            pytest.skip(f"Required instrumentation module {module_name} missing dependency: {exc}")

        for attribute, method in instruments:
            instrument = getattr(module, attribute, None)
            assert instrument is not None, f"{attribute} missing on {module_name}"
            assert callable(
                getattr(instrument, method, None)
            ), f"Instrument {attribute} on {module_name} lacks {method}()"
        validated_modules.append(module_name)

    assert validated_modules, "No instrumentation modules were validated"


def test_grafana_dashboards_present() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dashboards_dir = repo_root / "infra" / "grafana" / "dashboards"
    expected_files = {
        "customer_health.json": "customer-health",
        "pipeline_latency.json": "pipeline-latency",
        "agent_success.json": "agent-success",
        "cost_observability.json": "cost-observability",
    }
    for filename, uid in expected_files.items():
        dashboard_path = dashboards_dir / filename
        assert dashboard_path.exists(), f"Dashboard {filename} missing"
        payload = json.loads(dashboard_path.read_text())
        assert payload.get("uid") == uid
        assert payload.get("panels"), "Dashboard should define panels"

    provisioning_path = repo_root / "infra" / "grafana" / "provisioning" / "dashboards" / "dashboard.yaml"
    provisioning_text = provisioning_path.read_text()
    assert "/var/lib/grafana/dashboards" in provisioning_text
