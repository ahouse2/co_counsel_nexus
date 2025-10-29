"""Cost tracking service providing API + telemetry integration."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional
from uuid import uuid4

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..config import Settings, get_settings
from ..security.authz import Principal
from ..storage.cost_store import CostEventRecord, CostStore


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)

_api_counter = _meter.create_counter(
    "cost_api_calls_total",
    unit="1",
    description="API usage events captured for cost attribution",
)
_api_latency = _meter.create_histogram(
    "cost_api_latency_ms",
    unit="ms",
    description="Latency distribution for API calls contributing to spend",
)
_model_counter = _meter.create_counter(
    "cost_model_loads_total",
    unit="1",
    description="Local model load operations captured for spend estimation",
)
_model_duration = _meter.create_histogram(
    "cost_model_load_duration_ms",
    unit="ms",
    description="Duration of local model initialisation routines",
)
_gpu_duration = _meter.create_histogram(
    "cost_gpu_duration_ms",
    unit="ms",
    description="Accumulated GPU usage time attributable to workloads",
)
_gpu_utilisation = _meter.create_histogram(
    "cost_gpu_utilisation_percent",
    unit="percent",
    description="Observed GPU utilisation percentage during workloads",
)


class CostEventCategory(str, Enum):
    API = "api"
    MODEL = "model"
    GPU = "gpu"


@dataclass(slots=True)
class CostSummaryMetric:
    total: float
    unit: str
    breakdown: Dict[str, float]
    average: float | None = None


@dataclass(slots=True)
class CostSummary:
    generated_at: datetime
    window_hours: float
    tenant_id: str | None
    api_calls: CostSummaryMetric
    model_loads: CostSummaryMetric
    gpu_utilisation: CostSummaryMetric


class CostTrackingService:
    """Coordinates persistence and telemetry for cost attribution."""

    def __init__(self, *, settings: Settings | None = None, store: CostStore | None = None) -> None:
        self.settings = settings or get_settings()
        self.store = store or CostStore(self.settings.cost_tracking_path)

    def record_api_usage(
        self,
        *,
        principal: Principal | None,
        endpoint: str,
        method: str,
        latency_ms: float,
        success: bool,
        status_code: int,
        metadata: Dict[str, object] | None = None,
        units: float = 1.0,
    ) -> CostEventRecord:
        tenant_id = principal.tenant_id if principal else None
        attributes = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "tenant_id": tenant_id or "public",
            "success": success,
        }
        _api_counter.add(units, attributes=attributes)
        _api_latency.record(latency_ms, attributes=attributes)
        payload = {
            "latency_ms": round(latency_ms, 2),
            "status_code": status_code,
            "success": success,
        }
        if metadata:
            payload.update(metadata)
        record = self._append_event(
            category=CostEventCategory.API,
            name=endpoint,
            amount=units,
            unit="calls",
            tenant_id=tenant_id,
            metadata=payload,
        )
        return record

    def record_model_load(
        self,
        *,
        model_name: str,
        framework: str,
        device: str | None,
        duration_ms: float,
        size_mb: float | None = None,
        tenant_id: str | None = None,
        metadata: Dict[str, object] | None = None,
    ) -> CostEventRecord:
        attributes = {
            "model_name": model_name,
            "framework": framework,
            "device": device or "unknown",
        }
        _model_counter.add(1, attributes=attributes)
        _model_duration.record(duration_ms, attributes=attributes)
        payload = {
            "duration_ms": round(duration_ms, 2),
            "framework": framework,
            "device": device,
        }
        if size_mb is not None:
            payload["size_mb"] = round(size_mb, 2)
        if metadata:
            payload.update(metadata)
        return self._append_event(
            category=CostEventCategory.MODEL,
            name=model_name,
            amount=size_mb or 0.0,
            unit="MiB",
            tenant_id=tenant_id,
            metadata=payload,
        )

    def record_gpu_utilisation(
        self,
        *,
        tenant_id: str | None,
        device: str,
        duration_ms: float,
        utilisation_percent: float,
        metadata: Dict[str, object] | None = None,
    ) -> CostEventRecord:
        attributes = {
            "device": device,
            "tenant_id": tenant_id or "public",
        }
        _gpu_duration.record(duration_ms, attributes=attributes)
        _gpu_utilisation.record(utilisation_percent, attributes=attributes)
        payload = {
            "duration_ms": round(duration_ms, 2),
            "utilisation_percent": round(utilisation_percent, 2),
        }
        if metadata:
            payload.update(metadata)
        return self._append_event(
            category=CostEventCategory.GPU,
            name=device,
            amount=duration_ms,
            unit="ms",
            tenant_id=tenant_id,
            metadata=payload,
        )

    def summarise(
        self,
        *,
        window_hours: float,
        tenant_id: str | None = None,
    ) -> CostSummary:
        now = datetime.now(timezone.utc)
        window = now - timedelta(hours=window_hours)
        api_total = 0.0
        api_breakdown: Dict[str, float] = defaultdict(float)
        api_latency: List[float] = []

        model_total = 0.0
        model_breakdown: Dict[str, float] = defaultdict(float)
        model_duration: List[float] = []

        gpu_total = 0.0
        gpu_breakdown: Dict[str, float] = defaultdict(float)
        gpu_util_percent: List[float] = []

        for event in self.store.iter_events():
            if tenant_id and event.tenant_id != tenant_id:
                continue
            if event.timestamp < window:
                continue
            if event.category == CostEventCategory.API.value:
                api_total += event.amount
                api_breakdown[event.name] += event.amount
                latency = event.metadata.get("latency_ms")
                if isinstance(latency, (int, float)):
                    api_latency.append(float(latency))
            elif event.category == CostEventCategory.MODEL.value:
                model_total += event.amount
                model_breakdown[event.name] += event.amount
                duration = event.metadata.get("duration_ms")
                if isinstance(duration, (int, float)):
                    model_duration.append(float(duration))
            elif event.category == CostEventCategory.GPU.value:
                gpu_total += event.amount
                gpu_breakdown[event.name] += event.amount
                utilisation = event.metadata.get("utilisation_percent")
                if isinstance(utilisation, (int, float)):
                    gpu_util_percent.append(float(utilisation))

        api_avg = sum(api_latency) / len(api_latency) if api_latency else None
        model_avg = sum(model_duration) / len(model_duration) if model_duration else None
        gpu_avg = sum(gpu_util_percent) / len(gpu_util_percent) if gpu_util_percent else None

        return CostSummary(
            generated_at=now,
            window_hours=window_hours,
            tenant_id=tenant_id,
            api_calls=CostSummaryMetric(
                total=api_total,
                unit="calls",
                breakdown=dict(sorted(api_breakdown.items())),
                average=api_avg,
            ),
            model_loads=CostSummaryMetric(
                total=model_total,
                unit="MiB",
                breakdown=dict(sorted(model_breakdown.items())),
                average=model_avg,
            ),
            gpu_utilisation=CostSummaryMetric(
                total=gpu_total,
                unit="ms",
                breakdown=dict(sorted(gpu_breakdown.items())),
                average=gpu_avg,
            ),
        )

    def list_events(
        self,
        *,
        limit: int = 200,
        tenant_id: str | None = None,
        category: CostEventCategory | None = None,
    ) -> List[CostEventRecord]:
        return self.store.list_events(
            limit=limit,
            tenant_id=tenant_id,
            category=category.value if category else None,
        )

    def _append_event(
        self,
        *,
        category: CostEventCategory,
        name: str,
        amount: float,
        unit: str,
        tenant_id: str | None,
        metadata: Dict[str, object],
    ) -> CostEventRecord:
        with _tracer.start_as_current_span("cost.event") as span:
            span.set_attribute("cost.category", category.value)
            span.set_attribute("cost.name", name)
            span.set_attribute("cost.tenant_id", tenant_id or "public")
            span.set_attribute("cost.amount", amount)
            span.set_attribute("cost.unit", unit)
            record = CostEventRecord(
                event_id=uuid4().hex,
                timestamp=datetime.now(timezone.utc),
                tenant_id=tenant_id,
                category=category.value,
                name=name,
                amount=amount,
                unit=unit,
                metadata=dict(metadata),
            )
            try:
                self.store.append(record)
            except Exception as exc:  # pragma: no cover - persistence errors rare
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise
            else:
                span.set_status(Status(StatusCode.OK))
            return record


@lru_cache(maxsize=1)
def get_cost_tracking_service() -> CostTrackingService:
    return CostTrackingService()


__all__ = [
    "CostEventCategory",
    "CostSummary",
    "CostSummaryMetric",
    "CostTrackingService",
    "get_cost_tracking_service",
]
