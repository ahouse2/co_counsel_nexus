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


__all__ = ["record_pipeline_metrics", "record_node_yield", "record_document_yield"]
