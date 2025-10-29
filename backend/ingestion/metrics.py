"""OpenTelemetry metrics for ingestion pipeline observability."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import metrics

_meter = metrics.get_meter("backend.ingestion.pipeline")

_PIPELINE_DURATION = _meter.create_histogram(
    "ingestion.pipeline.duration",
    unit="s",
    description="Time taken to process a single ingestion source",
)

_PIPELINE_NODES = _meter.create_counter(
    "ingestion.pipeline.nodes",
    unit="1",
    description="Total nodes produced by the ingestion pipeline",
)

_PIPELINE_DOCUMENTS = _meter.create_counter(
    "ingestion.pipeline.documents",
    unit="1",
    description="Documents emitted by the ingestion pipeline",
)

_PIPELINE_ERRORS = _meter.create_counter(
    "ingestion.pipeline.errors",
    unit="1",
    description="Pipeline failures",
)

_JOB_STATUS_TRANSITIONS = _meter.create_counter(
    "ingestion.job.status_transitions",
    unit="1",
    description="Lifecycle transitions for ingestion jobs",
)

_JOB_QUEUE_EVENTS = _meter.create_counter(
    "ingestion.job.queue.events",
    unit="1",
    description="Queue operations performed for ingestion jobs",
)


@contextmanager
def record_pipeline_metrics(source_type: str, job_id: str) -> Iterator[None]:
    """Record duration metrics for a pipeline execution."""

    start = time.perf_counter()
    try:
        yield
    except Exception:  # pragma: no cover - metrics instrumentation only
        _PIPELINE_ERRORS.add(1, {"source_type": source_type, "job_id": job_id})
        raise
    finally:
        elapsed = time.perf_counter() - start
        _PIPELINE_DURATION.record(elapsed, {"source_type": source_type, "job_id": job_id})


def record_node_yield(count: int, *, source_type: str, job_id: str) -> None:
    if count:
        _PIPELINE_NODES.add(count, {"source_type": source_type, "job_id": job_id})


def record_document_yield(count: int, *, source_type: str, job_id: str) -> None:
    if count:
        _PIPELINE_DOCUMENTS.add(count, {"source_type": source_type, "job_id": job_id})


def record_job_transition(job_id: str, previous: str | None, new: str) -> None:
    """Count a lifecycle transition for an ingestion job."""

    attributes = {"job_id": job_id or "unknown", "to": new}
    if previous:
        attributes["from"] = previous
    _JOB_STATUS_TRANSITIONS.add(1, attributes)


def record_queue_event(job_id: str, event: str, *, reason: str | None = None) -> None:
    """Emit telemetry for queue-level operations (enqueued, duplicate, rejected)."""

    attributes = {"job_id": job_id or "unknown", "event": event}
    if reason:
        attributes["reason"] = reason
    _JOB_QUEUE_EVENTS.add(1, attributes)


__all__ = [
    "record_pipeline_metrics",
    "record_node_yield",
    "record_document_yield",
    "record_job_transition",
    "record_queue_event",
]
