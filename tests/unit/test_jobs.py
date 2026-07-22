"""Job orchestrator cancel and completion (Phase 1.5)."""

from __future__ import annotations

import time
from collections.abc import Callable

from prism_bi.application.jobs import JobOrchestrator, demo_sleep_worker
from prism_bi_sdk.dto.job import JobProgress, JobState


def test_demo_job_completes() -> None:
    orch = JobOrchestrator(max_workers=1)
    try:
        handle = orch.submit(
            "demo",
            lambda progress, cancelled: demo_sleep_worker(
                progress, cancelled, steps=5, step_seconds=0.01
            ),
        )
        deadline = time.time() + 2.0
        while time.time() < deadline:
            current = orch.get(handle.id)
            assert current is not None
            if current.state in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
                break
            time.sleep(0.02)
        final = orch.get(handle.id)
        assert final is not None
        assert final.state == JobState.COMPLETED
    finally:
        orch.shutdown(wait=True)


def test_job_cancel() -> None:
    orch = JobOrchestrator(max_workers=1)

    def slow(
        progress: Callable[[JobProgress], None],
        cancelled: Callable[[], bool],
    ) -> None:
        for index in range(100):
            if cancelled():
                return
            progress(JobProgress(percent=float(index), message="x"))
            time.sleep(0.02)

    try:
        handle = orch.submit("slow", slow)
        time.sleep(0.05)
        assert orch.cancel(handle.id) is True
        deadline = time.time() + 2.0
        while time.time() < deadline:
            current = orch.get(handle.id)
            assert current is not None
            if current.state in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
                break
            time.sleep(0.02)
        final = orch.get(handle.id)
        assert final is not None
        assert final.state == JobState.CANCELLED
    finally:
        orch.shutdown(wait=True)
