"""Background job DTOs shared with PluginContext."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class JobState(StrEnum):
    """Lifecycle state of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class JobProgress:
    """Progress update emitted by a worker."""

    percent: float
    message: str = ""


@dataclass(frozen=True, slots=True)
class JobHandle:
    """Opaque handle returned when a job is submitted."""

    id: UUID
    name: str
    state: JobState
    progress_percent: float = 0.0
    progress_message: str = ""
    error: str | None = None
