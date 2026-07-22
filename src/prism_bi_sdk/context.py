"""Host-facing services exposed to plugins (no warehouse handles)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from prism_bi_sdk.dto.job import JobHandle, JobProgress


@runtime_checkable
class PluginContext(Protocol):
    """Services a plugin may use after activation.

    Never exposes DuckDB connections or direct warehouse writers.
    """

    def log(self, level: str, message: str, **fields: Any) -> None:
        """Emit a structured log line via the host logger."""

    def get_config(self, namespace: str) -> Mapping[str, Any]:
        """Read a configuration namespace (read-only mapping)."""

    def get_secret(self, key: str) -> str | None:
        """Read a secret from the OS-backed store."""

    def set_secret(self, key: str, value: str) -> None:
        """Write a secret to the OS-backed store."""

    def submit_job(
        self,
        name: str,
        worker: Callable[[Callable[[JobProgress], None], Callable[[], bool]], None],
    ) -> JobHandle:
        """Submit background work; worker receives progress callback and cancel check."""

    def list_dataset_summaries(self) -> tuple[Mapping[str, Any], ...]:
        """Return read-only dataset catalog summaries for the open project (may be empty)."""
