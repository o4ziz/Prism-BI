"""Exporter plugin contract — replaceable export formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from prism_bi_sdk.dto.export_artifact import ExportArtifact
from prism_bi_sdk.plugin import IPlugin


@runtime_checkable
class IExporterPlugin(IPlugin, Protocol):
    """Serializes an ``ExportArtifact`` to disk.

    All formats (CSV, Excel, JSON, PNG, PDF, …) implement this contract.
    Application logic resolves exporters by ``format_id`` and never imports a
    concrete engine. Plugins must not access DuckDB or datasources.
    """

    def format_ids(self) -> tuple[str, ...]:
        """Stable format ids this plugin can write (e.g. ``csv``, ``pdf``)."""

    def supports(self, artifact: ExportArtifact, format_id: str) -> bool:
        """Return True if this plugin can export ``artifact`` as ``format_id``."""

    def export(
        self,
        artifact: ExportArtifact,
        destination: Path,
        *,
        format_id: str,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Write ``artifact`` to ``destination`` and return the written path."""
