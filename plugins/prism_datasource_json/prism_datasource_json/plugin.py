"""JSON array-of-objects batch_import datasource."""

from __future__ import annotations

import json
from collections.abc import Iterator
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
from prism_bi_sdk.datasources import DataSourceCapability
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.preview import PreviewResult
from prism_bi_sdk.dto.schema import ColumnDescriptor, EntityHandle, LogicalType


def _load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict):
        # single object or keyed lists — prefer "data" / "records" / first list value
        for key in ("data", "records", "items", "rows"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON root must be an array of objects")
    return [row if isinstance(row, dict) else {"value": row} for row in data]


def _flatten(row: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        name = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, name))
        else:
            flat[name] = value
    return flat


def _to_table(records: list[dict[str, Any]]) -> pa.Table:
    flat = [_flatten(row) for row in records]
    if not flat:
        return pa.table({"_empty": pa.array([], type=pa.null())})
    return pa.Table.from_pylist(flat)


def _logical(field: pa.Field) -> LogicalType:
    t = field.type
    if pa.types.is_integer(t):
        return LogicalType.INTEGER
    if pa.types.is_floating(t):
        return LogicalType.FLOAT
    if pa.types.is_boolean(t):
        return LogicalType.BOOLEAN
    return LogicalType.TEXT


class _JsonBatchSource:
    def __init__(self, path: Path) -> None:
        self._path = path

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        table = _to_table(_load_records(self._path))
        for start in range(0, max(table.num_rows, 1), batch_size):
            chunk = table.slice(start, min(batch_size, max(table.num_rows - start, 0)))
            if chunk.num_rows == 0 and start == 0:
                yield pa.RecordBatch.from_arrays(
                    [pa.array([], type=f.type) for f in chunk.schema],
                    schema=chunk.schema,
                )
                return
            if chunk.num_rows:
                yield chunk.to_batches()[0]


class JsonDataSourcePlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.datasource.json",
            name="JSON Data Source",
            version="1.0.0",
            api_version=1,
            entry_module="prism_datasource_json.plugin",
            entry_class="JsonDataSourcePlugin",
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
                contribution_id="prism.datasource.json",
                factory=self,
                display_name="JSON",
                metadata={"extensions": [".json"]},
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
        table = _to_table(_load_records(path)).slice(0, int(options.get("preview_rows", 200)))
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
        path = Path(entity.metadata.get("path") if entity.metadata else entity.id)
        preview = self.preview(entity, options)
        return MaterializePlan(
            columns=preview.columns,
            source=_JsonBatchSource(path),
            suggested_alias=path.stem,
            provenance={"plugin_id": self._manifest.id, "entity_id": entity.id, "path": str(path)},
        )
