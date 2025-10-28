from __future__ import annotations

import atexit
import logging
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException, status
from qdrant_client.http import models as qmodels

from ..config import get_settings
from ..models.api import IngestionRequest, IngestionSource
from ..security.authz import Principal
from ..storage.document_store import DocumentStore
from ..storage.job_store import JobStore
from ..storage.timeline_store import TimelineEvent, TimelineStore
from ..utils.audit import AuditEvent, get_audit_trail
from ..utils.credentials import CredentialRegistry
from ..utils.text import (
    chunk_text,
    find_dates,
    hashed_embedding,
    read_text,
    sentence_containing,
)
from ..utils.triples import (
    EntitySpan,
    Triple,
    extract_entities,
    extract_triples,
    normalise_entity_id,
)
from .forensics import ForensicsReport, ForensicsService
from .graph import GraphService, get_graph_service
from .ingestion_sources import MaterializedSource, build_connector
from .ingestion_worker import (
    IngestionJobAlreadyQueued,
    IngestionQueueFull,
    IngestionTask,
    IngestionWorker,
)
from .vector import VectorService, get_vector_service

_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".log", ".rtf"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
_FINANCIAL_EXTENSIONS = {".csv"}

LOGGER = logging.getLogger("backend.services.ingestion")


@dataclass
class IngestedDocument:
    id: str
    uri: str
    type: str
    title: str
    metadata: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "uri": self.uri,
            "type": self.type,
            "title": self.title,
            "metadata": self.metadata,
        }


@dataclass
class GraphMutation:
    nodes: Set[str] = field(default_factory=set)
    edges: Set[Tuple[str, str, str, str | None]] = field(default_factory=set)
    triples: int = 0

    def record_node(self, node_id: str) -> None:
        self.nodes.add(node_id)

    def record_edge(
        self, source: str, relation: str, target: str, doc_id: str | None
    ) -> None:
        self.edges.add((source, relation, target, doc_id))

    def merge(self, other: "GraphMutation") -> None:
        self.nodes.update(other.nodes)
        self.edges.update(other.edges)
        self.triples += other.triples


class IngestionService:
    def __init__(
        self,
        vector_service: VectorService | None = None,
        graph_service: GraphService | None = None,
        timeline_store: TimelineStore | None = None,
        job_store: JobStore | None = None,
        document_store: DocumentStore | None = None,
        forensics_service: ForensicsService | None = None,
        worker: IngestionWorker | None = None,
    ) -> None:
        self.logger = LOGGER
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.graph_service = graph_service or get_graph_service()
        self.timeline_store = timeline_store or TimelineStore(self.settings.timeline_path)
        self.job_store = job_store or JobStore(self.settings.job_store_dir)
        self.document_store = document_store or DocumentStore(self.settings.document_store_dir)
        self.forensics_service = forensics_service or ForensicsService()
        self.credential_registry = CredentialRegistry(self.settings.credentials_registry_path)
        self.worker = worker
        self.audit = get_audit_trail()

    def ingest(self, request: IngestionRequest, principal: Principal | None = None) -> str:
        if not request.sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one source must be provided",
            )

        job_id = str(uuid4())
        submitted_at = datetime.now(timezone.utc)
        actor = self._actor_from_principal(principal)
        job_record = self._initialise_job_record(job_id, submitted_at, request.sources, actor)
        self.job_store.write_job(job_id, job_record)
        self._audit_job_event(
            job_id,
            action="ingest.job.accepted",
            outcome="accepted",
            metadata={
                "source_count": len(request.sources),
                "sources": sorted({source.type for source in request.sources}),
            },
            actor=actor,
        )

        worker = self.worker or get_ingestion_worker()
        payload = request.model_dump(mode="json")
        try:
            worker.enqueue(job_id, payload)
        except IngestionJobAlreadyQueued:
            self.logger.info("Job already queued", extra={"job_id": job_id})
            self._audit_job_event(
                job_id,
                action="ingest.queue.duplicate",
                outcome="ignored",
                metadata={"reason": "already_queued"},
                actor=actor,
                severity="warning",
            )
        except IngestionQueueFull as exc:
            self._record_error(
                job_record,
                {
                    "code": "QUEUE_SATURATED",
                    "message": "Ingestion queue capacity reached",
                    "source": "queue",
                },
            )
            self._transition_job(job_record, "failed")
            self.job_store.write_job(job_id, job_record)
            self._audit_job_event(
                job_id,
                action="ingest.queue.saturated",
                outcome="rejected",
                metadata={"queue_max": self.settings.ingestion_queue_maxsize},
                actor=actor,
                severity="warning",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ingestion queue is full",
            ) from exc
        else:
            self._touch_job(job_record)
            self.job_store.write_job(job_id, job_record)
            self._audit_job_event(
                job_id,
                action="ingest.queue.enqueued",
                outcome="success",
                metadata={"worker_concurrency": self.settings.ingestion_worker_concurrency},
                actor=actor,
            )
        return job_id

    def process_job(self, job_id: str, request: IngestionRequest) -> None:
        try:
            job_record = self.job_store.read_job(job_id)
        except FileNotFoundError:
            submitted_at = datetime.now(timezone.utc)
            job_record = self._initialise_job_record(
                job_id,
                submitted_at,
                request.sources,
                actor=self._system_actor(),
            )
        else:
            self._ensure_job_defaults(job_record, request.sources)

        status_value = job_record.get("status", "queued")
        self._audit_job_event(
            job_id,
            action="ingest.worker.claimed",
            outcome="success",
            metadata={"status": status_value},
            actor=self._job_actor(job_record),
        )
        if status_value in {"succeeded", "failed", "cancelled"}:
            self.logger.info(
                "Skipping ingestion job with terminal status",
                extra={"job_id": job_id, "status": status_value},
            )
            self._audit_job_event(
                job_id,
                action="ingest.worker.skipped",
                outcome="ignored",
                metadata={"status": status_value},
                actor=self._job_actor(job_record),
            )
            return

        self._transition_job(job_record, "running")
        self.job_store.write_job(job_id, job_record)
        self._execute_job(job_id, request, job_record)

    def _execute_job(
        self,
        job_id: str,
        request: IngestionRequest,
        job_record: Dict[str, object],
    ) -> None:
        all_documents: List[IngestedDocument] = []
        all_events: List[TimelineEvent] = []
        graph_nodes: Set[str] = set()
        graph_edges: Set[Tuple[str, str, str, str | None]] = set()
        triple_count = 0
        current_source_type: str | None = None

        try:
            for index, source in enumerate(request.sources):
                current_source_type = source.type
                self.logger.info(
                    "Processing ingestion source",
                    extra={"job_id": job_id, "source_type": source.type, "index": index},
                )
                connector = build_connector(source.type, self.settings, self.credential_registry, self.logger)
                materialized = connector.materialize(job_id, index, source)
                documents, events, skipped, mutation, reports = self._ingest_materialized_source(materialized)
                all_documents.extend(documents)
                all_events.extend(events)
                graph_nodes.update(mutation.nodes)
                graph_edges.update(mutation.edges)
                triple_count += mutation.triples

                job_record.setdefault("documents", [])
                job_record["documents"].extend(doc.to_dict() for doc in documents)
                job_record["status_details"]["ingestion"]["documents"] += len(documents)
                job_record["status_details"]["ingestion"]["skipped"].extend(skipped)
                job_record["status_details"]["timeline"]["events"] += len(events)
                job_record["status_details"]["forensics"]["artifacts"].extend(
                    self._format_forensics_status(report) for report in reports
                )
                if reports:
                    job_record["status_details"]["forensics"]["last_run_at"] = reports[-1].generated_at
                job_record["status_details"]["graph"]["nodes"] = len(graph_nodes)
                job_record["status_details"]["graph"]["edges"] = len(graph_edges)
                job_record["status_details"]["graph"]["triples"] = triple_count
                self._touch_job(job_record)
                self.job_store.write_job(job_id, job_record)
                self._audit_job_event(
                    job_id,
                    action="ingest.source.processed",
                    outcome="success",
                    metadata={
                        "source_type": source.type,
                        "index": index,
                        "documents": len(documents),
                        "timeline_events": len(events),
                        "skipped": len(skipped),
                        "graph_nodes": len(graph_nodes),
                        "graph_edges": len(graph_edges),
                        "triples": triple_count,
                    },
                    actor=self._job_actor(job_record),
                )
        except HTTPException as exc:
            self._record_error(
                job_record,
                {
                    "code": str(exc.status_code),
                    "message": exc.detail,
                    "source": current_source_type or "unknown",
                },
            )
            self._transition_job(job_record, "failed")
            self.job_store.write_job(job_id, job_record)
            self.logger.warning(
                "Ingestion failed with HTTP error",
                extra={"job_id": job_id, "status_code": exc.status_code},
            )
            self._audit_job_event(
                job_id,
                action="ingest.job.failed",
                outcome="error",
                metadata={"status_code": exc.status_code, "detail": exc.detail},
                actor=self._job_actor(job_record),
                severity="error",
            )
            raise
        except Exception as exc:  # pylint: disable=broad-except
            self._record_error(
                job_record,
                {
                    "code": "INGESTION_ERROR",
                    "message": str(exc),
                    "source": current_source_type or "unknown",
                },
            )
            self._transition_job(job_record, "failed")
            self.job_store.write_job(job_id, job_record)
            self.logger.exception("Unexpected ingestion failure", extra={"job_id": job_id})
            self._audit_job_event(
                job_id,
                action="ingest.job.failed",
                outcome="error",
                metadata={"error": str(exc)},
                actor=self._job_actor(job_record),
                severity="error",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ingestion failed unexpectedly",
            ) from exc

        if all_events:
            self.timeline_store.append(all_events)
        self._transition_job(job_record, "succeeded")
        self.job_store.write_job(job_id, job_record)
        self.logger.info(
            "Ingestion completed",
            extra={"job_id": job_id, "documents": len(all_documents), "events": len(all_events)},
        )

        self._audit_job_event(
            job_id,
            action="ingest.job.completed",
            outcome="success",
            metadata={
                "documents": len(all_documents),
                "timeline_events": len(all_events),
                "graph_nodes": len(graph_nodes),
                "graph_edges": len(graph_edges),
                "triples": triple_count,
            },
            actor=self._job_actor(job_record),
        )

    def _ensure_job_defaults(
        self, job_record: Dict[str, object], sources: List[IngestionSource]
    ) -> None:
        job_record.setdefault("status", "queued")
        job_record.setdefault("submitted_at", self._now_iso())
        job_record.setdefault("updated_at", self._now_iso())
        job_record.setdefault(
            "sources", [source.model_dump(exclude_none=True) for source in sources]
        )
        job_record.setdefault("documents", [])
        job_record.setdefault("errors", [])
        details = job_record.setdefault("status_details", {})
        ingestion = details.setdefault("ingestion", {"documents": 0, "skipped": []})
        ingestion.setdefault("documents", 0)
        ingestion.setdefault("skipped", [])
        timeline = details.setdefault("timeline", {"events": 0})
        timeline.setdefault("events", 0)
        forensics = details.setdefault(
            "forensics", {"artifacts": [], "last_run_at": None}
        )
        forensics.setdefault("artifacts", [])
        forensics.setdefault("last_run_at", None)
        graph = details.setdefault("graph", {"nodes": 0, "edges": 0, "triples": 0})
        graph.setdefault("nodes", 0)
        graph.setdefault("edges", 0)
        graph.setdefault("triples", 0)
        job_record.setdefault("requested_by", self._system_actor())

    def _system_actor(self) -> Dict[str, Any]:
        return {"id": "ingestion-worker", "type": "system", "roles": ["System"]}

    def _actor_from_principal(self, principal: Principal | None) -> Dict[str, Any]:
        if principal is None:
            return self._system_actor()
        actor = {
            "id": principal.client_id,
            "subject": principal.subject,
            "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles),
            "scopes": sorted(principal.scopes),
            "case_admin": principal.case_admin,
            "token_roles": sorted(principal.token_roles),
            "certificate_roles": sorted(principal.certificate_roles),
        }
        fingerprint = principal.attributes.get("fingerprint") or principal.attributes.get("certificate_fingerprint")
        if fingerprint:
            actor["fingerprint"] = fingerprint
        if principal.attributes:
            lineage_hint = principal.attributes.get("lineage")
            if lineage_hint:
                actor["lineage"] = lineage_hint
        return actor

    def _job_actor(self, job_record: Dict[str, object]) -> Dict[str, Any]:
        stored = job_record.get("requested_by")
        if isinstance(stored, dict):
            return stored
        return self._system_actor()

    def _audit_job_event(
        self,
        job_id: str,
        *,
        action: str,
        outcome: str,
        metadata: Dict[str, Any] | None = None,
        actor: Dict[str, Any] | None = None,
        severity: str = "info",
    ) -> None:
        if not job_id:
            return
        event = AuditEvent(
            category="ingestion",
            action=action,
            actor=actor or self._system_actor(),
            subject={"job_id": job_id},
            outcome=outcome,
            severity=severity,
            correlation_id=job_id,
            metadata=metadata or {},
        )
        self._safe_audit(event)

    def _safe_audit(self, event: AuditEvent) -> None:
        try:
            self.audit.append(event)
        except Exception:  # pragma: no cover - audit failures must never break ingestion
            self.logger.exception(
                "Failed to append audit event",
                extra={"category": event.category, "action": event.action},
            )

    def get_job(self, job_id: str) -> Dict[str, object]:
        record = self.job_store.read_job(job_id)
        record.setdefault("job_id", job_id)
        return record

    # region ingestion helpers

    def _ingest_materialized_source(
        self, materialized: MaterializedSource
    ) -> Tuple[
        List[IngestedDocument],
        List[TimelineEvent],
        List[Dict[str, str]],
        GraphMutation,
        List[ForensicsReport],
    ]:
        root = materialized.root
        if not root.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source path {root} not found")
        documents: List[IngestedDocument] = []
        events: List[TimelineEvent] = []
        skipped: List[Dict[str, str]] = []
        graph_mutation = GraphMutation()
        reports: List[ForensicsReport] = []
        origin = materialized.origin or str(root)
        source_type = materialized.source.type.lower()
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in _TEXT_EXTENSIONS:
                document, timeline_events, mutation, report = self._ingest_text(
                    path, origin, source_type
                )
                documents.append(document)
                events.extend(timeline_events)
                graph_mutation.merge(mutation)
                reports.append(report)
            elif suffix in _IMAGE_EXTENSIONS:
                doc_meta = self._register_document(
                    path, doc_type="image", origin=origin, source_type=source_type
                )
                report = self.forensics_service.build_image_artifact(doc_meta.id, path)
                documents.append(doc_meta)
                mutation = GraphMutation()
                mutation.record_node(doc_meta.id)
                graph_mutation.merge(mutation)
                reports.append(report)
            elif suffix in _FINANCIAL_EXTENSIONS:
                doc_meta = self._register_document(
                    path, doc_type="financial", origin=origin, source_type=source_type
                )
                report = self.forensics_service.build_financial_artifact(doc_meta.id, path)
                documents.append(doc_meta)
                mutation = GraphMutation()
                mutation.record_node(doc_meta.id)
                graph_mutation.merge(mutation)
                reports.append(report)
            else:
                skipped.append({"path": str(path), "reason": "unsupported_extension"})
                self.logger.debug(
                    "Skipping unsupported file",
                    extra={"job_source": materialized.source.type, "path": str(path)},
                )
        return documents, events, skipped, graph_mutation, reports

    def _ingest_text(
        self, path: Path, origin: str, source_type: str
    ) -> Tuple[IngestedDocument, List[TimelineEvent], GraphMutation, ForensicsReport]:
        document = self._register_document(
            path, doc_type="text", origin=origin, source_type=source_type
        )
        mutation = GraphMutation()
        mutation.record_node(document.id)

        text = read_text(path)
        chunks = chunk_text(
            text, self.settings.ingestion_chunk_size, self.settings.ingestion_chunk_overlap
        )
        entity_spans = extract_entities(text)
        entity_pairs: List[Tuple[str, str]] = []
        seen_pairs: Set[Tuple[str, str]] = set()
        for span in entity_spans:
            label = span.label.strip()
            if not label:
                continue
            normalised = normalise_entity_id(label)
            key = (normalised, label)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            entity_pairs.append(key)
        entity_pairs.sort(key=lambda item: (item[0] or item[1].lower(), item[1].lower()))
        entity_ids = [pair[0] for pair in entity_pairs if pair[0]]
        entity_labels = [pair[1] for pair in entity_pairs]

        points: List[qmodels.PointStruct] = []
        for idx, chunk in enumerate(chunks):
            vector = hashed_embedding(chunk, self.settings.qdrant_vector_size)
            payload = {
                "doc_id": document.id,
                "chunk_index": idx,
                "text": chunk,
                "uri": document.uri,
                "origin": origin,
                "source_type": source_type,
                "doc_type": "document",
                "entity_ids": entity_ids,
                "entity_labels": entity_labels,
            }
            points.append(
                qmodels.PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )
        if points:
            self.vector_service.upsert(points)

        for span in entity_spans:
            self._commit_entity(document.id, span, mutation)

        triples = extract_triples(text)
        if triples:
            self._commit_triples(document.id, triples, mutation)

        timeline_events = self._build_timeline_events(document.id, text)
        metadata_updates: Dict[str, object] = {
            "entity_ids": entity_ids,
            "entity_labels": entity_labels,
            "chunk_count": len(chunks),
        }
        document.metadata.update(metadata_updates)
        self._update_document_metadata(document.id, metadata_updates)
        report = self.forensics_service.build_document_artifact(document.id, path)
        return document, timeline_events, mutation, report

    def _commit_entity(self, doc_id: str, span: EntitySpan, mutation: GraphMutation) -> None:
        entity_id = normalise_entity_id(span.label)
        properties: Dict[str, object] = {
            "label": span.label,
            "type": span.entity_type,
        }
        self.graph_service.upsert_entity(entity_id, span.entity_type, properties)
        self.graph_service.merge_relation(
            doc_id,
            "MENTIONS",
            entity_id,
            {
                "doc_id": doc_id,
                "label": span.label,
                "type": span.entity_type,
            },
        )
        mutation.record_node(entity_id)
        mutation.record_edge(doc_id, "MENTIONS", entity_id, doc_id)

    def _commit_triples(
        self, doc_id: str, triples: List[Triple], mutation: GraphMutation
    ) -> None:
        for triple in triples:
            subject_id = normalise_entity_id(triple.subject.label)
            object_id = normalise_entity_id(triple.obj.label)
            self.graph_service.upsert_entity(
                subject_id,
                triple.subject.entity_type,
                {
                    "label": triple.subject.label,
                    "type": triple.subject.entity_type,
                },
            )
            self.graph_service.upsert_entity(
                object_id,
                triple.obj.entity_type,
                {
                    "label": triple.obj.label,
                    "type": triple.obj.entity_type,
                },
            )
            self.graph_service.merge_relation(
                subject_id,
                triple.predicate,
                object_id,
                {
                    "doc_id": doc_id,
                    "predicate": triple.predicate_text,
                    "relation": triple.predicate,
                    "evidence": [triple.evidence],
                    "sentence_index": triple.sentence_index,
                },
            )
            mutation.record_node(subject_id)
            mutation.record_node(object_id)
            mutation.record_edge(subject_id, triple.predicate, object_id, doc_id)
            mutation.triples += 1

    def _register_document(
        self,
        path: Path,
        doc_type: str,
        origin: str,
        source_type: str,
        extra_metadata: Dict[str, object] | None = None,
    ) -> IngestedDocument:
        doc_id = sha256_id(path)
        title = path.stem.replace("_", " ").title()
        uri = str(path.resolve())
        mime_type, _ = mimetypes.guess_type(path.name)
        size_bytes = path.stat().st_size
        checksum = sha256_file(path)
        metadata: Dict[str, object] = {
            "name": path.name,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "origin_uri": origin,
            "ingested_uri": uri,
            "type": doc_type,
            "checksum_sha256": checksum,
            "source_type": source_type,
            "doc_type": doc_type,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        self.graph_service.upsert_document(doc_id, title, metadata)
        self.document_store.write_document(
            doc_id,
            {
                "id": doc_id,
                "title": title,
                **metadata,
            },
        )
        return IngestedDocument(id=doc_id, uri=uri, type=doc_type, title=title, metadata=metadata)

    def _update_document_metadata(self, doc_id: str, updates: Dict[str, object]) -> None:
        try:
            record = self.document_store.read_document(doc_id)
        except FileNotFoundError:
            record = {"id": doc_id}
        merged = {**record, **updates}
        self.document_store.write_document(doc_id, merged)
        title = str(merged.get("title", doc_id))
        metadata = {key: value for key, value in merged.items() if key not in {"id", "title"}}
        self.graph_service.upsert_document(doc_id, title, metadata)

    def _build_timeline_events(self, doc_id: str, text: str) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        for idx, ts_str in enumerate(find_dates(text)):
            timestamp = parse_timestamp(ts_str)
            if not timestamp:
                continue
            sentence = sentence_containing(text, ts_str)
            summary = sentence or f"Evidence mentions {ts_str}"
            title = summary.split(".")[0].strip()
            if len(title) > 80:
                title = f"{title[:77].rstrip()}..."
            event = TimelineEvent(
                id=f"{doc_id}::event::{idx}",
                ts=timestamp,
                title=title or f"Event from {doc_id}",
                summary=summary,
                citations=[doc_id],
            )
            events.append(event)
        return events

    # endregion

    # region job manifest helpers

    def _format_forensics_status(self, report: ForensicsReport) -> Dict[str, object]:
        return {
            "document_id": report.file_id,
            "type": report.artifact_type,
            "schema_version": report.schema_version,
            "generated_at": report.generated_at,
            "report_path": str(report.report_path) if report.report_path else str(self.forensics_service.base_dir / report.file_id / "report.json"),
            "fallback_applied": report.fallback_applied,
        }

    def _initialise_job_record(
        self,
        job_id: str,
        submitted_at: datetime,
        sources: List[IngestionSource],
        actor: Dict[str, Any] | None = None,
    ) -> Dict[str, object]:
        iso = submitted_at.isoformat()
        return {
            "job_id": job_id,
            "status": "queued",
            "submitted_at": iso,
            "updated_at": iso,
            "sources": [source.model_dump(exclude_none=True) for source in sources],
            "documents": [],
            "errors": [],
            "status_details": {
                "ingestion": {"documents": 0, "skipped": []},
                "timeline": {"events": 0},
                "forensics": {"artifacts": [], "last_run_at": None},
                "graph": {"nodes": 0, "edges": 0, "triples": 0},
            },
            "requested_by": actor or self._system_actor(),
        }

    def _transition_job(self, job_record: Dict[str, object], status_value: str) -> None:
        previous = job_record.get("status")
        job_record["status"] = status_value
        self._touch_job(job_record)
        if previous == status_value:
            return
        severity = "info"
        outcome = "success"
        if status_value == "failed":
            severity = "error"
            outcome = "error"
        elif status_value == "cancelled":
            severity = "warning"
            outcome = "warning"
        self._audit_job_event(
            str(job_record.get("job_id", "")),
            action="ingest.status.transition",
            outcome=outcome,
            metadata={"from": previous, "to": status_value},
            actor=self._job_actor(job_record),
            severity=severity,
        )

    def _touch_job(self, job_record: Dict[str, object]) -> None:
        job_record["updated_at"] = self._now_iso()

    def _record_error(self, job_record: Dict[str, object], error: Dict[str, object]) -> None:
        job_record.setdefault("errors", []).append(error)
        self.logger.error(
            "Recorded ingestion error: %s",
            error.get("message"),
            extra={
                "ingestion_error_code": error.get("code"),
                "ingestion_error_source": error.get("source"),
            },
        )

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # endregion


_WORKER_LOCK = Lock()
_WORKER_INSTANCE: IngestionWorker | None = None


def _handle_ingestion_task(task: IngestionTask) -> None:
    service = IngestionService(worker=None)
    request = IngestionRequest.model_validate(task.payload)
    try:
        service.process_job(task.job_id, request)
    except HTTPException:
        # Job manifest already records failure details; suppress to avoid worker crash logs.
        return


def get_ingestion_worker() -> IngestionWorker:
    global _WORKER_INSTANCE
    with _WORKER_LOCK:
        if _WORKER_INSTANCE is None:
            settings = get_settings()
            worker = IngestionWorker(
                handler=_handle_ingestion_task,
                maxsize=settings.ingestion_queue_maxsize,
                concurrency=settings.ingestion_worker_concurrency,
            )
            worker.start()
            _WORKER_INSTANCE = worker
    return _WORKER_INSTANCE


def shutdown_ingestion_worker(timeout: float | None = None) -> None:
    global _WORKER_INSTANCE
    with _WORKER_LOCK:
        if _WORKER_INSTANCE is None:
            return
        _WORKER_INSTANCE.stop(timeout=timeout)
        _WORKER_INSTANCE = None


atexit.register(shutdown_ingestion_worker)


def sha256_id(path: Path) -> str:
    value = str(path.resolve()).encode("utf-8")
    return sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_timestamp(raw: str) -> datetime | None:
    try:
        if "-" in raw:
            return datetime.fromisoformat(raw)
        if "/" in raw:
            month, day, year = raw.split("/")
            return datetime(int(year), int(month), int(day))
    except ValueError:
        return None
    return None


def get_ingestion_service() -> IngestionService:
    return IngestionService(worker=get_ingestion_worker())
