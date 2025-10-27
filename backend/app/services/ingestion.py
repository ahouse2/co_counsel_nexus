from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException, status
from qdrant_client.http import models as qmodels

from ..config import get_settings
from ..models.api import IngestionRequest, IngestionSource
from ..storage.document_store import DocumentStore
from ..storage.job_store import JobStore
from ..storage.timeline_store import TimelineEvent, TimelineStore
from ..utils.credentials import CredentialRegistry
from ..utils.text import chunk_text, find_dates, hashed_embedding, read_text
from ..utils.triples import (
    EntitySpan,
    Triple,
    extract_entities,
    extract_triples,
    normalise_entity_id,
)
from .forensics import ForensicsService
from .graph import GraphService, get_graph_service
from .ingestion_sources import MaterializedSource, build_connector
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

    def ingest(self, request: IngestionRequest) -> str:
        if not request.sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one source must be provided",
            )
        job_id = str(uuid4())
        submitted_at = datetime.now(timezone.utc)
        job_record = self._initialise_job_record(job_id, submitted_at, request.sources)
        self.job_store.write_job(job_id, job_record)
        self._transition_job(job_record, "running")
        self.job_store.write_job(job_id, job_record)

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
                documents, events, skipped, mutation = self._ingest_materialized_source(materialized)
                all_documents.extend(documents)
                all_events.extend(events)
                graph_nodes.update(mutation.nodes)
                graph_edges.update(mutation.edges)
                triple_count += mutation.triples

                job_record["documents"].extend(doc.to_dict() for doc in documents)
                job_record["status_details"]["ingestion"]["documents"] += len(documents)
                job_record["status_details"]["ingestion"]["skipped"].extend(skipped)
                job_record["status_details"]["timeline"]["events"] += len(events)
                job_record["status_details"]["forensics"]["artifacts"].extend(
                    {"document_id": doc.id, "type": doc.type} for doc in documents
                )
                job_record["status_details"]["graph"]["nodes"] = len(graph_nodes)
                job_record["status_details"]["graph"]["edges"] = len(graph_edges)
                job_record["status_details"]["graph"]["triples"] = triple_count
                self._touch_job(job_record)
                self.job_store.write_job(job_id, job_record)
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
        return job_id

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
    ]:
        root = materialized.root
        if not root.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source path {root} not found")
        documents: List[IngestedDocument] = []
        events: List[TimelineEvent] = []
        skipped: List[Dict[str, str]] = []
        graph_mutation = GraphMutation()
        origin = materialized.origin or str(root)
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in _TEXT_EXTENSIONS:
                document, timeline_events, mutation = self._ingest_text(path, origin)
                documents.append(document)
                events.extend(timeline_events)
                graph_mutation.merge(mutation)
            elif suffix in _IMAGE_EXTENSIONS:
                doc_meta = self._register_document(path, doc_type="image", origin=origin)
                self.forensics_service.build_image_artifact(doc_meta.id, path)
                documents.append(doc_meta)
                mutation = GraphMutation()
                mutation.record_node(doc_meta.id)
                graph_mutation.merge(mutation)
            elif suffix in _FINANCIAL_EXTENSIONS:
                doc_meta = self._register_document(path, doc_type="financial", origin=origin)
                self.forensics_service.build_financial_artifact(doc_meta.id, path)
                documents.append(doc_meta)
                mutation = GraphMutation()
                mutation.record_node(doc_meta.id)
                graph_mutation.merge(mutation)
            else:
                skipped.append({"path": str(path), "reason": "unsupported_extension"})
                self.logger.debug(
                    "Skipping unsupported file",
                    extra={"job_source": materialized.source.type, "path": str(path)},
                )
        return documents, events, skipped, graph_mutation

    def _ingest_text(self, path: Path, origin: str) -> Tuple[IngestedDocument, List[TimelineEvent], GraphMutation]:
        document = self._register_document(path, doc_type="text", origin=origin)
        mutation = GraphMutation()
        mutation.record_node(document.id)

        text = read_text(path)
        chunks = chunk_text(text, self.settings.ingestion_chunk_size, self.settings.ingestion_chunk_overlap)
        points: List[qmodels.PointStruct] = []
        for idx, chunk in enumerate(chunks):
            vector = hashed_embedding(chunk, self.settings.qdrant_vector_size)
            payload = {
                "doc_id": document.id,
                "chunk_index": idx,
                "text": chunk,
                "uri": document.uri,
                "origin": origin,
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

        entity_spans = extract_entities(text)
        for span in entity_spans:
            self._commit_entity(document.id, span, mutation)

        triples = extract_triples(text)
        if triples:
            self._commit_triples(document.id, triples, mutation)

        timeline_events = self._build_timeline_events(document.id, text)
        self.forensics_service.build_document_artifact(document.id, path)
        return document, timeline_events, mutation

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

    def _register_document(self, path: Path, doc_type: str, origin: str) -> IngestedDocument:
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
        }
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

    def _build_timeline_events(self, doc_id: str, text: str) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        for idx, ts_str in enumerate(find_dates(text)):
            timestamp = parse_timestamp(ts_str)
            if not timestamp:
                continue
            event = TimelineEvent(
                id=f"{doc_id}::event::{idx}",
                ts=timestamp,
                title=f"Event from {doc_id}",
                summary=f"Evidence mentions {ts_str}",
                citations=[doc_id],
            )
            events.append(event)
        return events

    # endregion

    # region job manifest helpers

    def _initialise_job_record(
        self, job_id: str, submitted_at: datetime, sources: List[IngestionSource]
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
                "forensics": {"artifacts": []},
                "graph": {"nodes": 0, "edges": 0, "triples": 0},
            },
        }

    def _transition_job(self, job_record: Dict[str, object], status_value: str) -> None:
        job_record["status"] = status_value
        self._touch_job(job_record)

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
    return IngestionService()
