"""CSV batch_import datasource."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.datasources import DataSourceCapability
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.preview import PreviewResult
from prism_bi_sdk.dto.schema import ColumnDescriptor, EntityHandle, LogicalType


def _logical(field: pa.Field) -> LogicalType:
    t = field.type
    if pa.types.is_integer(t):
        return LogicalType.INTEGER
    if pa.types.is_floating(t):
        return LogicalType.FLOAT
    if pa.types.is_boolean(t):
        return LogicalType.BOOLEAN
    if pa.types.is_timestamp(t) or pa.types.is_date(t):
        return LogicalType.DATETIME
    return LogicalType.TEXT


class _CsvBatchSource:
    def __init__(
        self, path: Path, read_options: pacsv.ReadOptions, parse_options: pacsv.ParseOptions
    ) -> None:
        self._path = path
        self._read_options = read_options
        self._parse_options = parse_options

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        reader = pacsv.open_csv(
            self._path,
            read_options=self._read_options,
            parse_options=self._parse_options,
            convert_options=pacsv.ConvertOptions(strings_can_be_null=True),
        )
        while True:
            try:
                batch = reader.read_next_batch()
            except StopIteration:
                break
            if batch.num_rows == 0:
                break
            # Re-chunk if needed
            table = pa.Table.from_batches([batch])
            for start in range(0, table.num_rows, batch_size):
                yield table.slice(start, min(batch_size, table.num_rows - start)).to_batches()[0]


class CsvDataSourcePlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.datasource.csv",
            name="CSV Data Source",
            version="1.0.0",
            api_version=1,
            entry_module="prism_datasource_csv.plugin",
            entry_class="CsvDataSourcePlugin",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    @property
    def capabilities(self) -> DataSourceCapability:
        return DataSourceCapability.BATCH_IMPORT

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.DATA_SOURCES,
                contribution_id="prism.datasource.csv",
                factory=self,
                display_name="CSV",
                metadata={"extensions": [".csv", ".tsv", ".txt"]},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context

    def deactivate(self) -> None:
        self._context = None

    def discover(self, connection_or_path: str) -> list[EntityHandle]:
        path = Path(connection_or_path)
        return [
            EntityHandle(
                id=str(path.resolve()),
                display_name=path.name,
                kind="file",
                metadata={"path": str(path)},
            )
        ]

    def preview(self, entity: EntityHandle, options: dict[str, Any] | None = None) -> PreviewResult:
        options = options or {}
        path = Path(entity.metadata.get("path") if entity.metadata else entity.id)
        delimiter = str(options.get("delimiter") or _detect_delimiter(path))
        read_options = pacsv.ReadOptions(block_size=1 << 20)
        parse_options = pacsv.ParseOptions(delimiter=delimiter)
        table = pacsv.read_csv(
            path,
            read_options=read_options,
            parse_options=parse_options,
            convert_options=pacsv.ConvertOptions(strings_can_be_null=True),
        ).slice(0, int(options.get("preview_rows", 200)))
        columns = tuple(
            ColumnDescriptor(name=f.name, logical_type=_logical(f), nullable=True)
            for f in table.schema
        )
        batch = (
            table.to_batches()[0] if table.num_rows else pa.record_batch([], schema=table.schema)
        )
        return PreviewResult(columns=columns, batch=batch, row_count_estimate=None)

    def materialize(
        self, entity: EntityHandle, options: dict[str, Any] | None = None
    ) -> MaterializePlan:
        options = options or {}
        path = Path(entity.metadata.get("path") if entity.metadata else entity.id)
        delimiter = str(options.get("delimiter") or _detect_delimiter(path))
        preview = self.preview(entity, options)
        source = _CsvBatchSource(
            path,
            pacsv.ReadOptions(block_size=1 << 20),
            pacsv.ParseOptions(delimiter=delimiter),
        )
        return MaterializePlan(
            columns=preview.columns,
            source=source,
            suggested_alias=path.stem,
            provenance={"plugin_id": self._manifest.id, "entity_id": entity.id, "path": str(path)},
        )


def _detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="replace")[:4096]
    if sample.count("\t") > sample.count(","):
        return "\t"
    if sample.count(";") > sample.count(","):
        return ";"
    return ","
