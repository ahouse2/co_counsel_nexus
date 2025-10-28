"""Telemetry bootstrap helpers for the Co-Counsel backend."""

from __future__ import annotations

from threading import Lock
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor, SpanExporter
try:  # pragma: no cover - optional import for testing hooks
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter as SDKInMemorySpanExporter
except ImportError:  # pragma: no cover
    SDKInMemorySpanExporter = None

from ..config import Settings


__all__ = ["setup_telemetry", "reset_telemetry"]


_lock = Lock()
_configured = False


def setup_telemetry(settings: Settings) -> None:
    """Initialise global OpenTelemetry providers based on runtime settings."""

    global _configured
    with _lock:
        if _configured:
            return

        resource = _create_resource(settings)
        tracer_provider = TracerProvider(resource=resource)
        span_exporter = _create_span_exporter(settings)
        if span_exporter is not None:
            processor = _select_span_processor(span_exporter)
            tracer_provider.add_span_processor(processor)
        trace._set_tracer_provider(tracer_provider, log=False)  # type: ignore[attr-defined]

        metric_readers: list[MetricReader] = []
        metric_reader = _create_metric_reader(settings)
        if metric_reader is not None:
            metric_readers.append(metric_reader)
        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics._internal._set_meter_provider(meter_provider, log=False)  # type: ignore[attr-defined]

        _configured = True


def reset_telemetry() -> None:
    """Reset global providers so tests can configure telemetry deterministically."""

    global _configured
    with _lock:
        trace._set_tracer_provider(TracerProvider(), log=False)  # type: ignore[attr-defined]
        metrics._internal._set_meter_provider(MeterProvider(), log=False)  # type: ignore[attr-defined]
        _configured = False


def _create_resource(settings: Settings) -> Resource:
    attributes = {
        "service.name": settings.telemetry_service_name,
        "service.version": settings.app_version,
        "deployment.environment": settings.telemetry_environment,
    }
    return Resource.create(attributes)


def _create_span_exporter(settings: Settings) -> Optional[SpanExporter]:
    if not settings.telemetry_enabled:
        return None
    if settings.telemetry_otlp_endpoint:
        return OTLPSpanExporter(
            endpoint=settings.telemetry_otlp_endpoint,
            insecure=settings.telemetry_otlp_insecure,
        )
    if settings.telemetry_console_fallback:
        return ConsoleSpanExporter()
    return None


def _select_span_processor(exporter: SpanExporter) -> SimpleSpanProcessor | BatchSpanProcessor:
    if isinstance(exporter, ConsoleSpanExporter) or (
        SDKInMemorySpanExporter is not None and isinstance(exporter, SDKInMemorySpanExporter)
    ):
        return SimpleSpanProcessor(exporter)
    return BatchSpanProcessor(exporter)


def _create_metric_reader(settings: Settings) -> Optional[MetricReader]:
    if not settings.telemetry_enabled or not settings.telemetry_otlp_endpoint:
        return None
    exporter = OTLPMetricExporter(
        endpoint=settings.telemetry_otlp_endpoint,
        insecure=settings.telemetry_otlp_insecure,
    )
    interval_ms = int(settings.telemetry_metrics_interval * 1000)
    return PeriodicExportingMetricReader(exporter=exporter, export_interval_millis=interval_ms)

