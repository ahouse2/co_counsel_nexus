from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

LOGGER = logging.getLogger("backend.services.ingestion_worker")


class IngestionQueueError(RuntimeError):
    """Base exception for ingestion queue failures."""


class IngestionQueueFull(IngestionQueueError):
    """Raised when the ingestion queue is saturated."""


class IngestionJobAlreadyQueued(IngestionQueueError):
    """Raised when attempting to enqueue a job that is already pending or running."""


class IngestionTaskRetry(IngestionQueueError):
    """Signal that a task should be retried with backoff."""


@dataclass
class IngestionTask:
    job_id: str
    payload: dict[str, object]


_HandlerT = TypeVar("_HandlerT", bound=Callable[[IngestionTask], None])


class IngestionWorker(Generic[_HandlerT]):
    """Threaded worker processing ingestion tasks asynchronously."""

    def __init__(
        self,
        handler: _HandlerT,
        *,
        maxsize: int = 128,
        concurrency: int = 1,
        name: str = "ingestion-worker",
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self._handler = handler
        self._queue: queue.Queue[IngestionTask] = queue.Queue(maxsize)
        self._concurrency = concurrency
        self._name = name
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._pending: set[str] = set()
        self._active = 0
        self._active_lock = threading.Lock()
        self._started = False
        self._payload_digests: dict[str, str] = {}
        self._processed_digests: set[str] = set()
        self._attempts: dict[str, int] = {}
        self._max_retries = max(0, max_retries)
        self._retry_backoff = max(0.0, retry_backoff)

    def start(self) -> None:
        """Start worker threads if not already running."""

        with self._lock:
            if self._started:
                return
            self._stop_event.clear()
            self._threads = [
                threading.Thread(target=self._run, name=f"{self._name}-{idx}", daemon=True)
                for idx in range(self._concurrency)
            ]
            for thread in self._threads:
                thread.start()
            self._started = True

    def stop(self, timeout: Optional[float] = None) -> None:
        """Signal worker threads to stop and wait for completion."""

        with self._lock:
            if not self._started:
                return
            self._stop_event.set()
            threads = list(self._threads)
        deadline = time.monotonic() + timeout if timeout is not None else None
        for thread in threads:
            remaining = None
            if deadline is not None:
                remaining = max(0.0, deadline - time.monotonic())
            thread.join(remaining)
        with self._lock:
            self._threads.clear()
            self._started = False
            self._stop_event = threading.Event()
            self._pending.clear()
            self._payload_digests.clear()
            self._processed_digests.clear()
            self._attempts.clear()
            with self._active_lock:
                self._active = 0
            self._queue = queue.Queue(self._queue.maxsize)

    def enqueue(self, job_id: str, payload: dict[str, object]) -> None:
        """Queue a job for asynchronous processing."""

        fingerprint = self._payload_fingerprint(job_id, payload)
        with self._lock:
            if job_id in self._pending and self._payload_digests.get(job_id) == fingerprint:
                raise IngestionJobAlreadyQueued(f"Job {job_id} already pending")
            if fingerprint in self._processed_digests:
                raise IngestionJobAlreadyQueued(f"Job payload for {job_id} already processed")
            self._pending.add(job_id)
            self._payload_digests[job_id] = fingerprint
            self._attempts[job_id] = 0
            if not self._started:
                self.start()
        task = IngestionTask(job_id=job_id, payload=payload)
        try:
            self._queue.put_nowait(task)
        except queue.Full as exc:
            with self._lock:
                self._pending.discard(job_id)
                self._payload_digests.pop(job_id, None)
                self._attempts.pop(job_id, None)
            raise IngestionQueueFull("Ingestion queue is full") from exc

    def wait_for_idle(self, timeout: Optional[float] = None) -> bool:
        """Block until all tasks complete or timeout reached."""

        start = time.monotonic()
        while True:
            if self._queue.unfinished_tasks == 0 and self.active_count == 0:
                return True
            if timeout is not None and time.monotonic() - start >= timeout:
                return False
            time.sleep(0.05)

    @property
    def active_count(self) -> int:
        with self._active_lock:
            return self._active

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                task = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            with self._active_lock:
                self._active += 1
            requeue = False
            try:
                self._handler(task)
            except IngestionTaskRetry:
                attempts = self._attempts.get(task.job_id, 0) + 1
                if attempts <= self._max_retries:
                    self._attempts[task.job_id] = attempts
                    backoff = self._retry_backoff * attempts
                    if backoff:
                        time.sleep(backoff)
                    LOGGER.warning(
                        "Retrying ingestion task",
                        extra={"job_id": task.job_id, "attempt": attempts},
                    )
                    self._queue.put(task)
                    requeue = True
                else:
                    LOGGER.error(
                        "Retry limit exceeded for ingestion task",
                        extra={"job_id": task.job_id, "attempts": attempts},
                    )
                    self._processed_digests.discard(self._payload_digests.get(task.job_id, ""))
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unhandled ingestion task error", extra={"job_id": task.job_id})
                self._processed_digests.discard(self._payload_digests.get(task.job_id, ""))
            else:
                digest = self._payload_digests.get(task.job_id)
                if digest:
                    self._processed_digests.add(digest)
            finally:
                if not requeue:
                    with self._lock:
                        self._pending.discard(task.job_id)
                        self._payload_digests.pop(task.job_id, None)
                        self._attempts.pop(task.job_id, None)
                with self._active_lock:
                    self._active -= 1
                self._queue.task_done()
        # Drain stop signal; let queue finish naturally
        LOGGER.debug("Ingestion worker thread exiting")

    def _payload_fingerprint(self, job_id: str, payload: dict[str, object]) -> str:
        envelope = {"job_id": job_id, "payload": payload}
        serialised = json.dumps(envelope, sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest()
