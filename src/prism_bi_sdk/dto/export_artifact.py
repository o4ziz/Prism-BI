"""Neutral export payload shared by all exporter plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa


@dataclass(frozen=True, slots=True)
class ExportSection:
    """One block in a document/report artifact (already materialized)."""

    kind: str  # heading | text | image | table
    title: str = ""
    text: str = ""
    image_png: bytes | None = None
    table: pa.Table | None = None


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    """Engine-agnostic artifact for ``IExporterPlugin``.

    Built by the application (via analytics / visualization ports). Exporter
    plugins must not query DuckDB or datasources — they only serialize this
    payload.
    """

    kind: str  # tabular | image | document
    title: str
    table: pa.Table | None = None
    image_png: bytes | None = None
    sections: tuple[ExportSection, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
