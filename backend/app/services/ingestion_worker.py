from __future__ import annotations

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
            with self._active_lock:
                self._active = 0
            self._queue = queue.Queue(self._queue.maxsize)

    def enqueue(self, job_id: str, payload: dict[str, object]) -> None:
        """Queue a job for asynchronous processing."""

        with self._lock:
            if job_id in self._pending:
                raise IngestionJobAlreadyQueued(f"Job {job_id} already pending")
            self._pending.add(job_id)
            if not self._started:
                self.start()
        task = IngestionTask(job_id=job_id, payload=payload)
        try:
            self._queue.put_nowait(task)
        except queue.Full as exc:
            with self._lock:
                self._pending.discard(job_id)
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
            try:
                self._handler(task)
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unhandled ingestion task error", extra={"job_id": task.job_id})
            finally:
                with self._lock:
                    self._pending.discard(task.job_id)
                with self._active_lock:
                    self._active -= 1
                self._queue.task_done()
        # Drain stop signal; let queue finish naturally
        LOGGER.debug("Ingestion worker thread exiting")
