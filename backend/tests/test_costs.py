from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.testclient import TestClient

from backend.app.models.api import (
    CostEventModel,
    CostSummaryMetricModel,
    CostSummaryResponse,
)
from backend.app.security.authz import Principal
from backend.app.services.costs import CostEventCategory, CostStore, CostTrackingService


def _principal(tenant: str = "tenant-1") -> Principal:
    return Principal(
        client_id="test-client",
        subject="user-42",
        tenant_id=tenant,
        roles={"PlatformEngineer"},
        scopes={"billing:read"},
    )


@pytest.fixture()
def cost_test_app(tmp_path: Path) -> tuple[CostTrackingService, TestClient]:
    events_dir = tmp_path / "costs"
    events_dir.mkdir()
    events_path = events_dir / "events.jsonl"
    dummy_settings = SimpleNamespace(cost_tracking_path=events_path)
    store = CostStore(events_path)
    service = CostTrackingService(settings=dummy_settings, store=store)

    app = FastAPI()

    @app.get("/costs/summary")
    def cost_summary(
        window_hours: float = Query(24.0, ge=0.5, le=720.0),
        tenant_id: str | None = Query(default=None),
    ) -> CostSummaryResponse:
        summary = service.summarise(window_hours=window_hours, tenant_id=tenant_id)
        return CostSummaryResponse(
            generated_at=summary.generated_at,
            window_hours=summary.window_hours,
            tenant_id=summary.tenant_id,
            api_calls=CostSummaryMetricModel(**asdict(summary.api_calls)),
            model_loads=CostSummaryMetricModel(**asdict(summary.model_loads)),
            gpu_utilisation=CostSummaryMetricModel(**asdict(summary.gpu_utilisation)),
        )

    @app.get("/costs/events")
    def cost_events(
        limit: int = Query(100, ge=1, le=500),
        tenant_id: str | None = Query(default=None),
        category: str | None = Query(default=None),
    ) -> list[CostEventModel]:
        category_value = None
        if category:
            try:
                category_value = CostEventCategory(category)
            except ValueError as exc:  # pragma: no cover - validation
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category") from exc
        records = service.list_events(limit=limit, tenant_id=tenant_id, category=category_value)
        return [
            CostEventModel(
                event_id=record.event_id,
                timestamp=record.timestamp,
                tenant_id=record.tenant_id,
                category=record.category,  # type: ignore[arg-type]
                name=record.name,
                amount=record.amount,
                unit=record.unit,
                metadata=record.metadata,
            )
            for record in records
        ]

    return service, TestClient(app)


def test_cost_summary_and_events(cost_test_app) -> None:
    service, client = cost_test_app
    principal = _principal()

    service.store.clear()
    service.record_api_usage(
        principal=principal,
        endpoint="/query",
        method="GET",
        latency_ms=120.5,
        success=True,
        status_code=200,
        metadata={"model": "gpt-4o-mini"},
        units=3,
    )
    service.record_model_load(
        model_name="whisper-small",
        framework="faster-whisper",
        device="cuda",
        duration_ms=850.2,
        size_mb=512.0,
        tenant_id=principal.tenant_id,
        metadata={"precision": "float16"},
    )
    service.record_gpu_utilisation(
        tenant_id=principal.tenant_id,
        device="gpu-a10",
        duration_ms=600.0,
        utilisation_percent=72.5,
        metadata={"workload": "voice"},
    )
    service.record_api_usage(
        principal=_principal("tenant-2"),
        endpoint="/query",
        method="GET",
        latency_ms=90.0,
        success=True,
        status_code=200,
        units=1,
    )

    summary_response = client.get("/costs/summary")
    assert summary_response.status_code == 200
    summary = CostSummaryResponse(**summary_response.json())
    assert summary.tenant_id is None
    assert summary.api_calls.total == pytest.approx(4.0)
    assert summary.api_calls.breakdown["/query"] == pytest.approx(4.0)
    assert summary.model_loads.total == pytest.approx(512.0)
    assert summary.gpu_utilisation.total == pytest.approx(600.0)
    assert summary.api_calls.average == pytest.approx(105.25, rel=1e-4)

    filtered_summary = client.get("/costs/summary", params={"tenant_id": principal.tenant_id})
    assert filtered_summary.status_code == 200
    scoped = CostSummaryResponse(**filtered_summary.json())
    assert scoped.api_calls.total == pytest.approx(3.0)
    assert scoped.model_loads.total == pytest.approx(512.0)
    assert scoped.gpu_utilisation.total == pytest.approx(600.0)

    events_response = client.get("/costs/events", params={"category": "api"})
    assert events_response.status_code == 200
    events = [CostEventModel(**payload) for payload in events_response.json()]
    assert any(event.tenant_id == principal.tenant_id for event in events)
    assert all(event.category == "api" for event in events)

    invalid_response = client.get("/costs/events", params={"category": "invalid"})
    assert invalid_response.status_code == 400

    limited = client.get("/costs/events", params={"limit": 1})
    assert limited.status_code == 200
    assert len(limited.json()) == 1
