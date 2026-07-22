"""Exporter registry — format_id → IExporterPlugin without hardcoding engines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.dto.export_artifact import ExportArtifact
from prism_bi_sdk.exporters import IExporterPlugin


class ExporterRegistry:
    """Looks up exporter plugins by format id from the contribution registry."""

    def __init__(self, contribution_registry: Any) -> None:
        self._contributions = contribution_registry

    def available_formats(self) -> list[str]:
        formats: list[str] = []
        for reg in self._contributions.list_by_kind(ContributionKind.EXPORTERS):
            plugin = reg.factory
            formats.extend(self._format_ids(plugin))
        return sorted(set(formats))

    def get_plugin(self, format_id: str) -> IExporterPlugin | None:
        for reg in self._contributions.list_by_kind(ContributionKind.EXPORTERS):
            plugin = reg.factory
            if format_id in self._format_ids(plugin):
                return plugin  # type: ignore[no-any-return]
        return None

    def export(
        self,
        format_id: str,
        artifact: ExportArtifact,
        destination: Path,
        *,
        options: dict[str, Any] | None = None,
    ) -> Path:
        plugin = self.get_plugin(format_id)
        if plugin is None:
            raise KeyError(f"No exporter for format: {format_id}")
        if not plugin.supports(artifact, format_id):
            raise ValueError(f"Exporter {format_id} does not support artifact kind={artifact.kind}")
        return plugin.export(artifact, destination, format_id=format_id, options=options)

    @staticmethod
    def _format_ids(plugin: Any) -> tuple[str, ...]:
        fn = getattr(plugin, "format_ids", None)
        if callable(fn):
            return tuple(fn())
        fmt = getattr(plugin, "format_id", None)
        if isinstance(fmt, str):
            return (fmt,)
        return ()
