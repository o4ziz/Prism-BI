"""Background job orchestration (UI-thread safe via callbacks)."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

from prism_bi_sdk.dto.job import JobHandle, JobProgress, JobState

_LOGGER = logging.getLogger("prism_bi.jobs")

ProgressCallback = Callable[[JobProgress], None]
CancelCheck = Callable[[], bool]
Worker = Callable[[ProgressCallback, CancelCheck], None]
StateCallback = Callable[[JobHandle], None]

_MAX_RETAINED_JOBS = 50


@dataclass
class _JobRecord:
    id: uuid.UUID
    name: str
    state: JobState = JobState.PENDING
    error: str | None = None
    progress_percent: float = 0.0
    progress_message: str = ""
    cancel_event: threading.Event = field(default_factory=threading.Event)
    future: Future[None] | None = None


class JobOrchestrator:
    """Runs workers off the UI thread with progress and cancel support."""

    def __init__(
        self,
        *,
        max_workers: int = 2,
        on_state_change: StateCallback | None = None,
    ) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="prism-job")
        self._jobs: dict[uuid.UUID, _JobRecord] = {}
        self._order: list[uuid.UUID] = []
        self._lock = threading.Lock()
        self._on_state_change = on_state_change

    def set_on_state_change(self, callback: StateCallback | None) -> None:
        """Register a listener for job state transitions (e.g. Qt signal bridge)."""
        self._on_state_change = callback

    def submit(self, name: str, worker: Worker) -> JobHandle:
        """Submit a background job."""
        job_id = uuid.uuid4()
        record = _JobRecord(id=job_id, name=name)
        with self._lock:
            self._jobs[job_id] = record
            self._order.append(job_id)
            self._prune_locked()

        handle = self._handle(record)
        self._emit(handle)
        _LOGGER.info("job_id=%s submitted name=%s", job_id, name)

        def _run() -> None:
            with self._lock:
                record.state = JobState.RUNNING
            self._emit(self._handle(record))

            def progress(update: JobProgress) -> None:
                with self._lock:
                    record.progress_percent = max(0.0, min(100.0, float(update.percent)))
                    record.progress_message = update.message
                _LOGGER.debug(
                    "job_id=%s progress %.1f%% %s",
                    job_id,
                    update.percent,
                    update.message,
                )
                self._emit(self._handle(record))

            def cancelled() -> bool:
                return record.cancel_event.is_set()

            try:
                worker(progress, cancelled)
                with self._lock:
                    if record.cancel_event.is_set():
                        record.state = JobState.CANCELLED
                    else:
                        record.state = JobState.COMPLETED
                        record.progress_percent = 100.0
            except Exception as exc:  # noqa: BLE001 — surface to job state
                _LOGGER.exception("job_id=%s failed", job_id)
                with self._lock:
                    record.state = JobState.FAILED
                    record.error = str(exc)
            finally:
                self._emit(self._handle(record))

        record.future = self._executor.submit(_run)
        return handle

    def cancel(self, job_id: uuid.UUID) -> bool:
        """Request cancellation; returns True if the job was known."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return False
            record.cancel_event.set()
            _LOGGER.info("job_id=%s cancel requested", job_id)
            return True

    def get(self, job_id: uuid.UUID) -> JobHandle | None:
        """Return current handle snapshot."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            return self._handle(record)

    def has_running(self) -> bool:
        with self._lock:
            return any(r.state in {JobState.PENDING, JobState.RUNNING} for r in self._jobs.values())

    def shutdown(self, *, wait: bool = True) -> None:
        """Stop the executor."""
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _prune_locked(self) -> None:
        """Drop oldest terminal jobs beyond retention limit."""
        while len(self._order) > _MAX_RETAINED_JOBS:
            oldest = self._order[0]
            record = self._jobs.get(oldest)
            if record is None:
                self._order.pop(0)
                continue
            if record.state in {JobState.PENDING, JobState.RUNNING}:
                break
            self._order.pop(0)
            del self._jobs[oldest]

    def _handle(self, record: _JobRecord) -> JobHandle:
        return JobHandle(
            id=record.id,
            name=record.name,
            state=record.state,
            progress_percent=record.progress_percent,
            progress_message=record.progress_message,
            error=record.error,
        )

    def _emit(self, handle: JobHandle) -> None:
        if self._on_state_change is not None:
            try:
                self._on_state_change(handle)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("job state callback failed")


def demo_sleep_worker(
    progress: ProgressCallback,
    cancelled: CancelCheck,
    *,
    steps: int = 10,
    step_seconds: float = 0.05,
) -> None:
    """Demo worker used to prove the UI stays responsive."""
    import time

    for index in range(steps):
        if cancelled():
            return
        progress(JobProgress(percent=((index + 1) / steps) * 100.0, message=f"step {index + 1}"))
        time.sleep(step_seconds)
