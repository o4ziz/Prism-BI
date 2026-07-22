"""PNG exporter — writes pre-rendered image bytes from ExportArtifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.dto.export_artifact import ExportArtifact

_FORMATS = ("png",)


class ImageExporterPlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.exporter.image",
            name="Image Exporters",
            version="1.0.0",
            api_version=1,
            entry_module="prism_exporter_image.plugin",
            entry_class="ImageExporterPlugin",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.EXPORTERS,
                contribution_id="prism.exporter.image",
                factory=self,
                display_name="Image",
                metadata={"formats": list(_FORMATS)},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context

    def deactivate(self) -> None:
        self._context = None

    def format_ids(self) -> tuple[str, ...]:
        return _FORMATS

    def supports(self, artifact: ExportArtifact, format_id: str) -> bool:
        return format_id == "png" and artifact.kind == "image" and artifact.image_png is not None

    def export(
        self,
        artifact: ExportArtifact,
        destination: Path,
        *,
        format_id: str,
        options: dict[str, Any] | None = None,
    ) -> Path:
        _ = options
        if not self.supports(artifact, format_id):
            raise ValueError(f"Cannot export kind={artifact.kind} as {format_id}")
        assert artifact.image_png is not None
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(artifact.image_png)
        return destination.resolve()
