"""CSV / XLSX / JSON exporters — SDK + stdlib/openpyxl only (no DuckDB)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pyarrow as pa

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.dto.export_artifact import ExportArtifact

_FORMATS = ("csv", "xlsx", "json")


class TabularExporterPlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.exporter.tabular",
            name="Tabular Exporters",
            version="1.0.0",
            api_version=1,
            entry_module="prism_exporter_tabular.plugin",
            entry_class="TabularExporterPlugin",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.EXPORTERS,
                contribution_id="prism.exporter.tabular",
                factory=self,
                display_name="Tabular",
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
        return format_id in _FORMATS and artifact.kind == "tabular" and artifact.table is not None

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
        assert artifact.table is not None
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if format_id == "csv":
            _write_csv(artifact.table, destination)
        elif format_id == "json":
            _write_json(artifact.table, destination)
        elif format_id == "xlsx":
            _write_xlsx(artifact.table, destination, title=artifact.title)
        else:
            raise ValueError(f"Unsupported format: {format_id}")
        return destination.resolve()


def _rows(table: pa.Table) -> list[dict[str, Any]]:
    names = list(table.column_names)
    result: list[dict[str, Any]] = []
    for i in range(table.num_rows):
        result.append({name: table.column(name)[i].as_py() for name in names})
    return result


def _write_csv(table: pa.Table, path: Path) -> None:
    rows = _rows(table)
    fieldnames = list(table.column_names)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(table: pa.Table, path: Path) -> None:
    payload = _rows(table)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
        handle.write("\n")


def _write_xlsx(table: pa.Table, path: Path, *, title: str) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = (title or "Data")[:31] or "Data"
    names = list(table.column_names)
    ws.append(names)
    for row in _rows(table):
        ws.append([row.get(name) for name in names])
    wb.save(path)
