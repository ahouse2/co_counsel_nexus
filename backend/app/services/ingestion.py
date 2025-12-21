from __future__ import annotations

import asyncio
import atexit
import logging
import mimetypes
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Dict, List, Sequence, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException, status
from qdrant_client.http import models as qmodels
import numpy as np

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..config import get_settings
import zipfile
import shutil
from ..models.api import IngestionRequest, IngestionSource, IngestionResponse
from ..security.authz import Principal
from ..storage.document_store import DocumentStore
from ..storage.job_store import JobStore
from ..storage.timeline_store import TimelineEvent, TimelineStore
from ..utils.audit import AuditEvent, get_audit_trail
from ..utils.credentials import CredentialRegistry
from ..utils.text import find_dates, sentence_containing
from ..utils.triples import EntitySpan, Triple, normalise_entity_id
from .forensics import ForensicsReport, ForensicsService
from .graph import GraphService, get_graph_service
from .ingestion_sources import MaterializedSource, build_connector
from .ingestion_worker import (
    IngestionJobAlreadyQueued,
    IngestionQueueFull,
    IngestionTask,
    IngestionWorker,
)
from .timeline import EnrichmentStats, TimelineService
from .vector import VectorService, get_vector_service
from backend.ingestion.metrics import record_job_transition, record_queue_event
from backend.ingestion.loader_registry import LoaderRegistry
from backend.ingestion.ocr import OcrEngine
from backend.ingestion.pipeline import run_ingestion_pipeline
from backend.app.services.autonomous_orchestrator import get_orchestrator, SystemEvent, EventType
from backend.ingestion.settings import build_runtime_config

_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".log", ".rtf", ".html", ".htm"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
_FINANCIAL_EXTENSIONS = {".csv"}
_EMAIL_EXTENSIONS = {".eml", ".msg"}

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


_DEFAULT_EXECUTOR = ThreadPoolExecutor(max_workers=4)


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)

_ingestion_jobs_counter = _meter.create_counter(
    "ingestion_jobs_total",
    unit="1",
    description="Ingestion job lifecycle events",
)
_ingestion_job_duration = _meter.create_histogram(
    "ingestion_job_duration_ms",
    unit="ms",
    description="Total duration of ingestion jobs",
)
_ingestion_source_duration = _meter.create_histogram(
    "ingestion_source_duration_ms",
    unit="ms",
    description="Duration to process each ingestion source",
)
_ingestion_documents_counter = _meter.create_counter(
    "ingestion_documents_total",
    unit="1",
    description="Documents processed during ingestion",
)
_ingestion_errors_counter = _meter.create_counter(
    "ingestion_job_errors_total",
    unit="1",
    description="Ingestion jobs ending in failure",
)


class IngestionService:
    def __init__(
        self,
        vector_service: VectorService | None = None,
        graph_service: GraphService | None = None,
        timeline_store: TimelineStore | None = None,
        job_store: JobStore | None = None,
        document_store: DocumentStore | None = None,
        forensics_service: ForensicsService | None = None,
        executor: ThreadPoolExecutor | None = None,
        worker: IngestionWorker | None = None,
    ) -> None:
        self.logger = LOGGER
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.graph_service = graph_service or get_graph_service()
        self.timeline_store = timeline_store or TimelineStore(self.settings.timeline_path)
        self.job_store = job_store or JobStore(self.settings.job_store_dir)
        self.document_store = document_store or DocumentStore(self.settings.document_storage_path, self.settings.encryption_key)
        self.forensics_service = forensics_service or ForensicsService()
        self.credential_registry = CredentialRegistry(self.settings.credentials_registry_path)
        self.executor = executor or _DEFAULT_EXECUTOR
        self.worker = worker
        self.audit = get_audit_trail()
        self.runtime_config = build_runtime_config(self.settings)
        self.ocr_engine = OcrEngine(self.runtime_config.ocr, self.logger.getChild("ocr"))
        self.loader_registry = LoaderRegistry(
            self.runtime_config,
            self.ocr_engine,
            logger=self.logger.getChild("loader"),
            credential_resolver=self._resolve_credentials,
        )

    def ingest(self, request: IngestionRequest, principal: Principal | None = None) -> str:
        if not request.sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one source must be provided",
            )

        actor = self._actor_from_principal(principal)
        connectors = [
            (
                build_connector(source.type, self.settings, self.credential_registry, self.logger),
                source,
            )
            for source in request.sources
        ]

        job_id = str(uuid4())
        submitted_at = datetime.now(timezone.utc)
        job_record = self._initialise_job_record(job_id, submitted_at, request.sources, actor)
        self.job_store.write_job(job_id, job_record)

        sources_attribute = ",".join(sorted({source.type for source in request.sources}))
        with _tracer.start_as_current_span("ingestion.enqueue") as span:
            span.set_attribute("ingestion.job_id", job_id)
            span.set_attribute("ingestion.source_count", len(request.sources))
            span.set_attribute("ingestion.sources", sources_attribute)
            _ingestion_jobs_counter.add(1, attributes={"state": "accepted"})

            for index, (connector, source) in enumerate(connectors):
                try:
                    connector.preflight(source)
                except HTTPException as exc:
                    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, description=message))
                    _ingestion_errors_counter.add(
                        1,
                        attributes={"phase": "preflight", "source_type": source.type},
                    )
                    error_payload = {
                        "code": str(getattr(exc, "status_code", "INGESTION_ERROR")),
                        "message": message,
                        "source": f"preflight::{source.type.lower()}",
                    }
                    self._record_error(job_record, error_payload)
                    job_record.setdefault("status_details", {}).setdefault("ingestion", {}).setdefault("skipped", []).append(
                        {"index": index, "source": source.type, "reason": message}
                    )
                    self._transition_job(job_record, "failed")
                    self.job_store.write_job(job_id, job_record)
                    self._audit_job_event(
                        job_id,
                        action="ingest.queue.preflight_failed",
                        outcome="error",
                        metadata={"source_type": source.type, "index": index},
                        actor=actor,
                        severity="error",
                    )
                    severity = "error" if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR else "warning"
                    self._audit_job_event(
                        job_id,
                        action="ingest.job.preflight_failed",
                        outcome="error",
                        metadata={"source_type": source.type, "status_code": exc.status_code},
                        actor=actor,
                        severity=severity,
                    )
                    return job_id

            try:
                request_copy = request.model_copy(deep=True)
                future = self.executor.submit(self._run_job, job_id, request_copy, job_record)
                future.add_done_callback(self._log_job_failure(job_id))
            finally:
                span.set_status(Status(StatusCode.OK))
            _ingestion_jobs_counter.add(1, attributes={"state": "enqueued"})
        return job_id


    def get_job(self, job_id: str) -> Dict[str, object]:
        record = self.job_store.read_job(job_id)
        record.setdefault("job_id", job_id)
        return record

    async def ingest_document(
        self, principal: Principal, document_id: str, file: UploadFile
    ) -> IngestionResponse:
        temp_dir = Path(self.settings.ingestion_temp_dir) / document_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as buffer:
            while content := await file.read(1024):
                buffer.write(content)

        source = IngestionSource(type="file", path=str(file_path))
        request = IngestionRequest(sources=[source])
        job_id = self.ingest(request, principal)
        return IngestionResponse(job_id=job_id, status="queued")

    async def ingest_text(
        self, principal: Principal, document_id: str, text: str
    ) -> IngestionResponse:
        temp_dir = Path(self.settings.ingestion_temp_dir) / document_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{document_id}.txt"
        with open(file_path, "w", encoding="utf-8") as buffer:
            buffer.write(text)

        source = IngestionSource(type="text", path=str(file_path))
        request = IngestionRequest(sources=[source])
        job_id = self.ingest(request, principal)
        return IngestionResponse(job_id=job_id, status="queued")

    async def ingest_directory(
        self, principal: Principal, document_id: str, file: UploadFile
    ) -> IngestionResponse:
        if not file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .zip files are supported for directory uploads",
            )

        temp_zip_path = Path(self.settings.ingestion_temp_dir) / f"{document_id}.zip"
        temp_extract_dir = Path(self.settings.ingestion_temp_dir) / document_id

        # Save the uploaded zip file with intelligent timeout handling
        # No hard size limit, but timeout scales with file size
        try:
            import time
            total_size = 0
            start_time = time.time()
            base_timeout = 30  # 30 seconds base timeout
            
            with open(temp_zip_path, "wb") as buffer:
                while content := await file.read(65536):  # 64KB chunks
                    total_size += len(content)
                    elapsed = time.time() - start_time
                    
                    # Intelligent timeout: 60s base + 30s per 100MB
                    # Very generous for enterprise-scale uploads
                    # e.g., 1GB = 60s + 307s = 367s (~6 min)
                    # e.g., 10GB = 60s + 3072s = 3132s (~52 min)
                    size_mb = total_size / (1024 * 1024)
                    dynamic_timeout = 60 + (size_mb / 100) * 30
                    
                    if elapsed > dynamic_timeout:
                        # Upload is taking too long (network issue, not file size)
                        temp_zip_path.unlink(missing_ok=True)
                        self.logger.warning(
                            f"Upload timeout: {elapsed:.1f}s elapsed for {size_mb:.1f}MB "
                            f"(timeout: {dynamic_timeout:.1f}s)"
                        )
                        raise HTTPException(
                            status_code=status.HTTP_408_REQUEST_TIMEOUT,
                            detail=f"Upload timed out after {elapsed:.1f}s. "
                                   f"Please check your connection and try again."
                        )
                    
                    buffer.write(content)
            
            # Log successful upload
            final_size_mb = total_size / (1024 * 1024)
            upload_time = time.time() - start_time
            self.logger.info(
                f"Successfully uploaded {final_size_mb:.2f}MB in {upload_time:.1f}s "
                f"({final_size_mb/upload_time:.2f} MB/s)"
            )
            
        except HTTPException:
            raise
        except Exception as exc:
            temp_zip_path.unlink(missing_ok=True)
            self.logger.error(f"Error saving zip file: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded file: {str(exc)}"
            )

        # Check zip file size and auto-batch if > 1GB
        zip_size_mb = temp_zip_path.stat().st_size / (1024 * 1024)
        
        if zip_size_mb > 1024:  # > 1GB
            self.logger.info(
                f"Large zip detected ({zip_size_mb:.1f}MB), auto-batching into 1GB chunks"
            )
            
            # Split into batches
            batch_zips = await self._split_large_zip(temp_zip_path, max_size_mb=1024)
            
            # Process each batch
            all_sources: List[IngestionSource] = []
            
            for batch_zip in batch_zips:
                batch_extract_dir = Path(self.settings.ingestion_temp_dir) / f"{document_id}_{batch_zip.stem}"
                batch_extract_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    with zipfile.ZipFile(batch_zip, "r") as zip_ref:
                        zip_ref.extractall(batch_extract_dir)
                except zipfile.BadZipFile as exc:
                    self.logger.error(f"Invalid batch zip: {batch_zip.name}")
                    continue
                finally:
                    batch_zip.unlink()  # Clean up batch zip
                
                # Collect sources from this batch
                for path in batch_extract_dir.rglob("*"):
                    if path.is_file():
                        all_sources.append(IngestionSource(type="file", path=str(path)))
            
            # Clean up original zip
            temp_zip_path.unlink(missing_ok=True)
            
            if not all_sources:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files found in the uploaded directory (after batching)",
                )
            
            request = IngestionRequest(sources=all_sources)
            job_id = self.ingest(request, principal)
            
            return IngestionResponse(
                job_id=job_id, 
                status="queued",
                message=f"Large zip auto-batched: {len(batch_zips)} batches, {len(all_sources)} files"
            )
        
        # Standard processing for files < 1GB
        # Unzip the file
        try:
            with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_extract_dir)
        except zipfile.BadZipFile as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid zip file provided",
            ) from exc
        finally:
            temp_zip_path.unlink() # Clean up the zip file

        sources: List[IngestionSource] = []
        for path in temp_extract_dir.rglob("*"):
            if path.is_file():
                sources.append(IngestionSource(type="file", path=str(path)))
        
        if not sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files found in the uploaded directory",
            )

        request = IngestionRequest(sources=sources)
        job_id = self.ingest(request, principal)

        # Note: We cannot clean up the extracted directory here because the ingestion job
        # runs asynchronously and needs access to these files.
        # The cleanup should ideally be handled by a periodic task or the worker itself
        # after processing is complete.
        # shutil.rmtree(temp_extract_dir)

        return IngestionResponse(job_id=job_id, status="queued")

    async def ingest_local_path(
        self, principal: Principal, document_id: str, source_path: str, recursive: bool = True, sync: bool = False
    ) -> IngestionResponse:
        """
        Ingest files from local file system or network share.
        No upload required - direct access!
        
        Args:
            sync: If True, skips files that have already been ingested (matching path and hash).
        """
        path = Path(source_path)
        
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not found: {source_path}"
            )
        
        sources: List[IngestionSource] = []
        
        if path.is_file():
            sources.append(IngestionSource(
                source_id=path.name,
                type="file", 
                path=str(path)
            ))
        elif path.is_dir():
            if recursive:
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        sources.append(IngestionSource(
                            source_id=file_path.name,
                            type="file", 
                            path=str(file_path)
                        ))
            else:
                for file_path in path.glob("*"):
                    if file_path.is_file():
                        sources.append(IngestionSource(
                            source_id=file_path.name,
                            type="file", 
                            path=str(file_path)
                        ))
        
        if not sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files found at specified path"
            )
            
        # Sync Logic
        if sync:
            from backend.app.database import SessionLocal
            from backend.app.models.document import Document
            
            self.logger.info(f"Sync mode enabled. Checking {len(sources)} files against database...")
            
            # We need to calculate hashes for local files to compare
            # This can be slow for many large files, but it's necessary for true sync
            # Optimization: Check by path first? 
            # If we check by path, we might miss updates. 
            # Let's check by path AND hash if possible, or just path if hash is too expensive.
            # For now, let's do a quick check by path first to filter candidates, then hash?
            # Actually, the requirement is usually "don't re-ingest if unchanged".
            
            # Let's get all document paths for this case (or all docs if case unknown)
            # Since we don't have case_id here easily without looking it up, 
            # we might have to query by path.
            
            db = SessionLocal()
            try:
                # Get all existing paths
                existing_docs = db.query(Document.path, Document.hash_sha256).all()
                existing_map = {doc.path: doc.hash_sha256 for doc in existing_docs if doc.path}
                
                filtered_sources = []
                skipped_count = 0
                
                for source in sources:
                    file_path = str(source.path)
                    if file_path in existing_map:
                        # File exists in DB. Check hash.
                        # Calculate hash of local file
                        try:
                            with open(file_path, "rb") as f:
                                file_hash = sha256(f.read()).hexdigest()
                            
                            if existing_map[file_path] == file_hash:
                                # Match! Skip.
                                skipped_count += 1
                                continue
                        except Exception as e:
                            self.logger.warning(f"Could not hash file {file_path}: {e}")
                            # If we can't hash, maybe re-ingest to be safe? Or skip?
                            # Let's re-ingest.
                            pass
                    
                    filtered_sources.append(source)
                
                self.logger.info(f"Sync complete. Skipped {skipped_count} unchanged files. Queuing {len(filtered_sources)} files.")
                sources = filtered_sources
                
            finally:
                db.close()
        
        if not sources:
             return IngestionResponse(
                job_id="skipped", 
                status="completed",
                message="All files were skipped (sync mode)"
            )

        total_size = sum(Path(s.path).stat().st_size for s in sources)
        self.logger.info(
            f"Direct FS ingestion: {len(sources)} files, "
            f"{total_size / (1024*1024):.2f}MB from {source_path}"
        )
        
        request = IngestionRequest(sources=sources)
        job_id = self.ingest(request, principal)
        
        return IngestionResponse(job_id=job_id, status="queued")

    async def _split_large_zip(self, zip_path: Path, max_size_mb: int = 1024) -> List[Path]:
        """Split large zip into smaller batches."""
        import zipfile
        
        max_size = max_size_mb * 1024 * 1024
        batch_zips = []
        
        with zipfile.ZipFile(zip_path, 'r') as source_zip:
            file_list = source_zip.namelist()
            current_batch = []
            current_size = 0
            batch_num = 0
            
            for filename in file_list:
                file_info = source_zip.getinfo(filename)
                file_size = file_info.file_size
                
                if file_size > max_size:
                    # Single large file batch
                    if current_batch:
                        batch_path = self._create_batch_zip(source_zip, current_batch, zip_path, batch_num)
                        batch_zips.append(batch_path)
                        batch_num += 1
                        current_batch = []
                        current_size = 0
                    
                    batch_path = self._create_batch_zip(source_zip, [filename], zip_path, batch_num)
                    batch_zips.append(batch_path)
                    batch_num += 1
                    continue
                
                if current_size + file_size > max_size and current_batch:
                    batch_path = self._create_batch_zip(source_zip, current_batch, zip_path, batch_num)
                    batch_zips.append(batch_path)
                    batch_num += 1
                    current_batch = []
                    current_size = 0
                
                current_batch.append(filename)
                current_size += file_size
            
            if current_batch:
                batch_path = self._create_batch_zip(source_zip, current_batch, zip_path, batch_num)
                batch_zips.append(batch_path)
        
        self.logger.info(f"Split {zip_path.name} into {len(batch_zips)} batches (max {max_size_mb}MB each)")
        return batch_zips

    def _create_batch_zip(self, source_zip: zipfile.ZipFile, filenames: List[str], 
                          original_path: Path, batch_num: int) -> Path:
        """Create batch zip from selected files."""
        import zipfile
        
        batch_path = original_path.parent / f"{original_path.stem}_batch_{batch_num:03d}.zip"
        
        with zipfile.ZipFile(batch_path, 'w', zipfile.ZIP_DEFLATED) as batch_zip:
            for filename in filenames:
                data = source_zip.read(filename)
                batch_zip.writestr(filename, data)
        
        return batch_path

    # region async execution

    def _log_job_failure(self, job_id: str):
        def _callback(future: Future) -> None:
            try:
                future.result()
            except HTTPException:
                # Already logged inside the worker
                return
            except Exception:  # pylint: disable=broad-except
                self.logger.exception("Unhandled ingestion worker failure", extra={"job_id": job_id})

        return _callback

    def _run_job(self, job_id: str, request: IngestionRequest, job_record: Dict[str, object]) -> None:
        actor = self._job_actor(job_record)
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
            record_queue_event(job_id, "duplicate")
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
            record_queue_event(job_id, "rejected", reason="queue_full")
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
            record_queue_event(job_id, "enqueued")
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
        record_queue_event(job_id, "claimed")
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
        job_started = perf_counter()

        with _tracer.start_as_current_span("ingestion.execute") as span:
            span.set_attribute("ingestion.job_id", job_id)
            span.set_attribute("ingestion.source_count", len(request.sources))
            try:
                for index, source in enumerate(request.sources):
                    current_source_type = source.type
                    source_started = perf_counter()
                    self.logger.info(
                        "Processing ingestion source",
                        extra={"job_id": job_id, "source_type": source.type, "index": index},
                    )
                    connector = build_connector(source.type, self.settings, self.credential_registry, self.logger)
                    materialized = connector.materialize(job_id, index, source)
                    with _tracer.start_as_current_span(
                        "ingestion.source",
                        attributes={"ingestion.source_type": source.type, "ingestion.job_id": job_id},
                    ):
                        documents, events, skipped, mutation, reports = self._ingest_materialized_source(
                            job_id, materialized
                        )
                    source_duration = (perf_counter() - source_started) * 1000.0
                    _ingestion_source_duration.record(
                        source_duration,
                        attributes={"source_type": source.type},
                    )
                    if documents:
                        _ingestion_documents_counter.add(
                            len(documents), attributes={"source_type": source.type}
                        )
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
                _ingestion_errors_counter.add(
                    1,
                    attributes={"phase": "execute", "source_type": current_source_type or "unknown"},
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc.detail)))
                _ingestion_jobs_counter.add(
                    1, attributes={"state": "completed", "status": "failed"}
                )
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
                _ingestion_errors_counter.add(
                    1,
                    attributes={"phase": "execute", "source_type": current_source_type or "unknown"},
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                _ingestion_jobs_counter.add(
                    1, attributes={"state": "completed", "status": "failed"}
                )
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
            else:
                duration_ms = (perf_counter() - job_started) * 1000.0
                _ingestion_job_duration.record(duration_ms, attributes={"status": "succeeded"})
                _ingestion_jobs_counter.add(1, attributes={"state": "completed", "status": "succeeded"})
                span.set_status(Status(StatusCode.OK))

        if all_events:
            self.timeline_store.append(all_events)
        enrichment_stats = self._refresh_timeline_enrichments()
        community_summary = self.graph_service.compute_community_summary(graph_nodes)
        job_record["status_details"].setdefault("graph", {})["communities"] = community_summary.to_dict()
        timeline_details = job_record["status_details"].setdefault("timeline", {"events": 0})
        timeline_details["highlights"] = enrichment_stats.highlights
        timeline_details["relations"] = enrichment_stats.relations
        timeline_details["enriched"] = enrichment_stats.mutated
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
        
        # Cleanup temporary directories created during ingestion
        self._cleanup_temp_directories(job_id, job_record)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # AUTONOMOUS RESEARCH SWARM TRIGGER (Phase 1 KG Connectivity)
        # After successful ingestion, trigger the ResearchSwarm to autonomously
        # search for relevant case law and statutes, then upsert findings to KG
        # ═══════════════════════════════════════════════════════════════════════════
        self._trigger_autonomous_research(job_id, all_documents, job_record)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # AUTONOMOUS ORCHESTRATOR TRIGGER (Full Intelligence Pipeline)
        # Dispatch BATCH_INGESTION_COMPLETE event to trigger the 6-stage autonomous
        # pipeline: Narrative → Research → Trial Prep → Forensics → Drafting → Simulation
        # ═══════════════════════════════════════════════════════════════════════════
        self._trigger_autonomous_pipeline(job_id, all_documents, job_record)

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

    def _refresh_timeline_enrichments(self) -> EnrichmentStats:
        service = TimelineService(store=self.timeline_store, graph_service=self.graph_service)
        return service.refresh_enrichments()

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

    def _resolve_credentials(self, reference: str) -> Dict[str, str]:
        try:
            return self.credential_registry.get(reference)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential {reference} not found",
            ) from exc

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

    def _cleanup_temp_directories(self, job_id: str, job_record: Dict[str, object]) -> None:
        """Clean up temporary directories created during folder upload ingestion."""
        temp_dir = Path(self.settings.ingestion_temp_dir) / job_id
        
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                self.logger.info(
                    "Cleaned up temporary ingestion directory",
                    extra={"job_id": job_id, "path": str(temp_dir)}
                )
            except Exception as exc:  # pylint: disable=broad-except
                # Don't fail the job if cleanup fails, just log it
                self.logger.warning(
                    "Failed to cleanup temporary directory",
                    extra={"job_id": job_id, "path": str(temp_dir), "error": str(exc)}
                )

    def _trigger_autonomous_research(
        self,
        job_id: str,
        documents: List[IngestedDocument],
        job_record: Dict[str, object],
    ) -> None:
        """
        Trigger the ResearchSwarm to autonomously research relevant case law
        and statutes for ingested documents. Runs as a background task.
        
        This is the key integration point for Phase 1 KG Connectivity:
        - Each document's content and metadata is passed to the research swarm
        - The swarm searches CourtListener, CA Codes, and Federal Codes
        - Findings are automatically upserted into the Knowledge Graph
        """
        if not documents:
            return
        
        # Get case_id from job record or first document metadata
        sources = job_record.get("sources", [])
        case_id = None
        if sources and isinstance(sources[0], dict):
            case_id = sources[0].get("metadata", {}).get("case_id")
        
        if not case_id:
            # Try to extract from first document
            if documents and documents[0].metadata:
                case_id = documents[0].metadata.get("case_id")
        
        if not case_id:
            case_id = f"case_{job_id[:8]}"  # Fallback case ID
        
        def run_research_in_thread():
            """Execute async research swarm in a new event loop."""
            try:
                from backend.app.agents.swarms.research_swarm import get_research_swarm
                
                swarm = get_research_swarm()
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    for doc in documents[:5]:  # Limit to first 5 docs to prevent overload
                        doc_text = str(doc.metadata.get("text", ""))[:2000]  # Truncate
                        doc_metadata = {
                            "doc_id": doc.id,
                            "doc_type": doc.type,
                            "title": doc.title,
                            **{k: v for k, v in doc.metadata.items() if k != "text"}
                        }
                        
                        self.logger.info(
                            "Triggering autonomous research for document",
                            extra={"doc_id": doc.id, "case_id": case_id}
                        )
                        
                        loop.run_until_complete(
                            swarm.research_for_document(
                                doc_id=doc.id,
                                doc_text=doc_text,
                                metadata=doc_metadata,
                                case_id=case_id
                            )
                        )
                finally:
                    loop.close()
                    
                self.logger.info(
                    "Autonomous research completed for ingestion job",
                    extra={"job_id": job_id, "documents_researched": min(len(documents), 5)}
                )
                
                self._audit_job_event(
                    job_id,
                    action="ingest.autonomous_research.completed",
                    outcome="success",
                    metadata={
                        "documents_researched": min(len(documents), 5),
                        "case_id": case_id,
                    },
                    actor=self._job_actor(job_record),
                )
                
            except Exception as exc:
                self.logger.warning(
                    "Autonomous research failed (non-blocking)",
                    extra={"job_id": job_id, "error": str(exc)}
                )
                self._audit_job_event(
                    job_id,
                    action="ingest.autonomous_research.failed",
                    outcome="error",
                    metadata={"error": str(exc)},
                    actor=self._job_actor(job_record),
                    severity="warning",
                )
        
        # Schedule research in background thread (non-blocking)
        self.executor.submit(run_research_in_thread)
        
        self.logger.info(
            "Autonomous research swarm triggered",
            extra={"job_id": job_id, "document_count": len(documents)}
        )

    def _trigger_autonomous_pipeline(
        self,
        job_id: str,
        documents: List[IngestedDocument],
        job_record: Dict[str, object],
    ) -> None:
        """
        Trigger the full autonomous intelligence pipeline via the Orchestrator.
        
        This dispatches the BATCH_INGESTION_COMPLETE event which triggers:
        Stage 1: NarrativeSwarm - Build timeline & detect contradictions
        Stage 2: LegalResearchSwarm - Find relevant precedents
        Stage 3: TrialPrepSwarm - Prepare trial materials
        Stage 4: ForensicsSwarm - Scan evidence integrity
        Stage 5: DraftingSwarm - Generate initial briefs
        Stage 6: SimulationSwarm - Predict outcomes
        """
        if not documents:
            return
        
        # Get case_id from job record or first document metadata
        sources = job_record.get("sources", [])
        case_id = None
        if sources and isinstance(sources[0], dict):
            case_id = sources[0].get("metadata", {}).get("case_id")
        
        if not case_id:
            if documents and documents[0].metadata:
                case_id = documents[0].metadata.get("case_id")
        
        if not case_id:
            case_id = f"case_{job_id[:8]}"
        
        def run_pipeline_in_thread():
            """Execute autonomous pipeline in a new event loop."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    orchestrator = get_orchestrator()
                    
                    # Publish the batch completion event
                    event = SystemEvent(
                        event_type=EventType.BATCH_INGESTION_COMPLETE,
                        case_id=case_id,
                        source_service="IngestionService",
                        payload={
                            "job_id": job_id,
                            "doc_count": len(documents),
                            "document_ids": [doc.id for doc in documents],
                            "case_id": case_id,
                        }
                    )
                    
                    # Start orchestrator if not already running
                    loop.run_until_complete(orchestrator.start())
                    loop.run_until_complete(orchestrator.publish(event))
                    
                    self.logger.info(
                        "[AUTONOMOUS] BATCH_INGESTION_COMPLETE event dispatched",
                        extra={
                            "job_id": job_id,
                            "case_id": case_id,
                            "doc_count": len(documents)
                        }
                    )
                    
                finally:
                    loop.close()
                    
                self._audit_job_event(
                    job_id,
                    action="ingest.autonomous_pipeline.triggered",
                    outcome="success",
                    metadata={
                        "documents": len(documents),
                        "case_id": case_id,
                        "pipeline_stages": 6,
                    },
                    actor=self._job_actor(job_record),
                )
                
            except Exception as exc:
                self.logger.warning(
                    "Autonomous pipeline trigger failed (non-blocking)",
                    extra={"job_id": job_id, "error": str(exc)}
                )
                self._audit_job_event(
                    job_id,
                    action="ingest.autonomous_pipeline.failed",
                    outcome="error",
                    metadata={"error": str(exc)},
                    actor=self._job_actor(job_record),
                    severity="warning",
                )
        
        # Schedule pipeline in background thread (non-blocking)
        self.executor.submit(run_pipeline_in_thread)
        
        self.logger.info(
            "[AUTONOMOUS] Intelligence pipeline triggered",
            extra={"job_id": job_id, "document_count": len(documents), "case_id": case_id}
        )

    # endregion


    # region ingestion helpers

    def _ingest_materialized_source(
        self, job_id: str, materialized: MaterializedSource
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
        origin = materialized.origin or str(root)
        source_type = materialized.source.type.lower()
        pipeline_result = run_ingestion_pipeline(
            job_id,
            root,
            materialized.source,
            origin,
            registry=self.loader_registry,
            runtime_config=self.runtime_config,
        )

        documents: List[IngestedDocument] = []
        events: List[TimelineEvent] = []
        skipped: List[Dict[str, str]] = []
        graph_mutation = GraphMutation()
        reports: List[ForensicsReport] = []

        for doc_result in pipeline_result.documents:
            path = doc_result.loaded.path
            checksum = doc_result.loaded.checksum
            doc_id = sha256_id(path)
            if self._document_checksum_matches(doc_id, checksum):
                skipped.append(
                    {
                        "path": str(path),
                        "reason": "unchanged_checksum",
                    }
                )
                self.logger.info(
                    "Skipping document with unchanged checksum",
                    extra={"doc_id": doc_id, "path": str(path)},
                )
                continue

            doc_type = self._infer_doc_type(path)
            metadata = dict(doc_result.loaded.metadata)
            metadata.update(
                {
                    "checksum_sha256": checksum,
                    "chunk_count": len(doc_result.nodes),
                    "embedding_model": self.runtime_config.embedding.model,
                    "embedding_provider": self.runtime_config.embedding.provider.value,
                    "ocr_engine": doc_result.loaded.ocr.engine if doc_result.loaded.ocr else None,
                    "ocr_confidence": doc_result.loaded.ocr.confidence if doc_result.loaded.ocr else None,
                }
            )

            document = self._register_document(
                path,
                doc_type=doc_type,
                origin=origin,
                source_type=source_type,
                extra_metadata=metadata,
            )
            graph_mutation.record_node(document.id)

            entity_pairs = self._entity_pairs(doc_result.entities)
            metadata_updates: Dict[str, object] = {
                "entity_ids": [entity_id for entity_id, _ in entity_pairs],
                "entity_labels": [label for _, label in entity_pairs],
                "chunk_count": len(doc_result.nodes),
                "checksum_sha256": checksum,
            }

            points: List[qmodels.PointStruct] = []
            node_snapshots: List[Dict[str, Any]] = []
            for node in doc_result.nodes:
                payload = {
                    **node.metadata,
                    "doc_id": document.id,
                    "chunk_index": node.chunk_index,
                    "text": node.text,
                    "origin": origin,
                    "source_type": source_type,
                    "doc_type": doc_type,
                }
                embedding_norm = float(np.linalg.norm(node.embedding)) if node.embedding else 0.0
                payload["embedding_norm"] = embedding_norm
                points.append(
                    qmodels.PointStruct(
                        id=str(uuid4()),
                        vector=list(node.embedding),
                        payload=payload,
                    )
                )
                node_snapshots.append(
                    {
                        "node_id": node.node_id,
                        "chunk_index": node.chunk_index,
                        "text": node.text,
                        "metadata": node.metadata,
                        "embedding": list(node.embedding),
                    }
                )

            if points:
                self.vector_service.upsert(points)

            for span in doc_result.entities:
                self._commit_entity(document.id, span, graph_mutation)

            self._commit_triples(document.id, doc_result.triples, graph_mutation)
            timeline_events = self._build_timeline_events(document.id, doc_result.loaded.text)
            events.extend(timeline_events)
            metadata_updates["timeline_events"] = len(timeline_events)

            if doc_result.loaded.ocr and doc_result.loaded.ocr.tokens:
                metadata_updates["ocr_token_count"] = len(doc_result.loaded.ocr.tokens)

            self._update_document_metadata(document.id, metadata_updates)

            report = self._build_forensics_report(
                doc_type,
                document.id,
                path,
                nodes=node_snapshots,
                ingestion_metadata=metadata,
            )
            if report is not None:
                reports.append(report)

            documents.append(document)

        documents.sort(
            key=lambda item: (
                item.metadata.get("ocr_confidence") is not None,
                float(item.metadata.get("ocr_confidence") or 0.0),
            ),
            reverse=True,
        )
        return documents, events, skipped, graph_mutation, reports

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

    def _document_checksum_matches(self, doc_id: str, checksum: str) -> bool:
        try:
            record = self.document_store.read_document(doc_id)
        except FileNotFoundError:
            return False
        stored = record.get("checksum_sha256")
        return stored == checksum and stored is not None

    def _infer_doc_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in _IMAGE_EXTENSIONS:
            return "image"
        if suffix in _FINANCIAL_EXTENSIONS:
            return "financial"
        if suffix in _EMAIL_EXTENSIONS:
            return "email"
        if suffix == ".pdf":
            return "pdf"
        return "text"

    def _entity_pairs(self, entities: Sequence[EntitySpan]) -> List[Tuple[str, str]]:
        seen: Set[str] = set()
        pairs: List[Tuple[str, str]] = []
        for span in entities:
            label = span.label.strip()
            if not label:
                continue
            entity_id = normalise_entity_id(label)
            if entity_id in seen:
                continue
            seen.add(entity_id)
            pairs.append((entity_id, label))
        return pairs

    def _build_forensics_report(
        self,
        doc_type: str,
        doc_id: str,
        path: Path,
        *,
        nodes: List[Dict[str, Any]] | None = None,
        ingestion_metadata: Dict[str, Any] | None = None,
    ) -> ForensicsReport | None:
        if doc_type == "image":
            return self.forensics_service.build_image_artifact(doc_id, path)
        if doc_type == "financial":
            return self.forensics_service.build_financial_artifact(doc_id, path)
        return self.forensics_service.build_document_artifact(
            doc_id,
            path,
            nodes=nodes,
            ingestion_metadata=ingestion_metadata,
        )

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
        record_job_transition(str(job_record.get("job_id", "")), previous, status_value)
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
