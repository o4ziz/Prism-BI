"""Excel (.xlsx) batch_import datasource using python-calamine."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa
from python_calamine import CalamineWorkbook

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


def _sheet_to_table(path: Path, sheet: str) -> pa.Table:
    workbook = CalamineWorkbook.from_path(str(path))
    rows = workbook.get_sheet_by_name(sheet).to_python(skip_empty_area=False)
    if not rows:
        return pa.table({"_empty": pa.array([], type=pa.null())})
    header = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(rows[0])]
    # Deduplicate headers
    seen: dict[str, int] = {}
    names: list[str] = []
    for name in header:
        if name in seen:
            seen[name] += 1
            names.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            names.append(name)
    data_rows = rows[1:]
    columns: dict[str, list[Any]] = {name: [] for name in names}
    for row in data_rows:
        for idx, name in enumerate(names):
            columns[name].append(row[idx] if idx < len(row) else None)
    return pa.Table.from_pydict(columns)


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


class _ExcelBatchSource:
    def __init__(self, path: Path, sheet: str) -> None:
        self._path = path
        self._sheet = sheet

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        table = _sheet_to_table(self._path, self._sheet)
        if table.num_rows == 0:
            yield pa.RecordBatch.from_arrays(
                [pa.array([], type=f.type) for f in table.schema],
                schema=table.schema,
            )
            return
        for start in range(0, table.num_rows, batch_size):
            yield table.slice(start, min(batch_size, table.num_rows - start)).to_batches()[0]


class ExcelDataSourcePlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.datasource.excel",
            name="Excel Data Source",
            version="1.0.0",
            api_version=1,
            entry_module="prism_datasource_excel.plugin",
            entry_class="ExcelDataSourcePlugin",
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
                contribution_id="prism.datasource.excel",
                factory=self,
                display_name="Excel",
                metadata={"extensions": [".xlsx"]},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context

    def deactivate(self) -> None:
        self._context = None

    def discover(self, connection_or_path: str) -> list[EntityHandle]:
        path = Path(connection_or_path)
        workbook = CalamineWorkbook.from_path(str(path))
        return [
            EntityHandle(
                id=f"{path.resolve()}::{sheet}",
                display_name=sheet,
                kind="sheet",
                metadata={"path": str(path), "sheet": sheet},
            )
            for sheet in workbook.sheet_names
        ]

    def preview(self, entity: EntityHandle, options: dict[str, Any] | None = None) -> PreviewResult:
        options = options or {}
        meta = entity.metadata or {}
        path = Path(str(meta["path"]))
        sheet = str(meta["sheet"])
        table = _sheet_to_table(path, sheet).slice(0, int(options.get("preview_rows", 200)))
        columns = tuple(
            ColumnDescriptor(name=f.name, logical_type=_logical(f), nullable=True)
            for f in table.schema
        )
        batch = (
            table.to_batches()[0] if table.num_rows else pa.record_batch([], schema=table.schema)
        )
        return PreviewResult(columns=columns, batch=batch)

    def materialize(
        self, entity: EntityHandle, options: dict[str, Any] | None = None
    ) -> MaterializePlan:
        meta = entity.metadata or {}
        path = Path(str(meta["path"]))
        sheet = str(meta["sheet"])
        preview = self.preview(entity, options)
        return MaterializePlan(
            columns=preview.columns,
            source=_ExcelBatchSource(path, sheet),
            suggested_alias=sheet,
            provenance={
                "plugin_id": self._manifest.id,
                "entity_id": entity.id,
                "path": str(path),
                "sheet": sheet,
            },
        )
