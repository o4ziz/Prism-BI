"""SQLite batch_import datasource."""

from __future__ import annotations

import sqlite3
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


def _logical(field: pa.Field) -> LogicalType:
    t = field.type
    if pa.types.is_integer(t):
        return LogicalType.INTEGER
    if pa.types.is_floating(t):
        return LogicalType.FLOAT
    if pa.types.is_boolean(t):
        return LogicalType.BOOLEAN
    return LogicalType.TEXT


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class _SqliteBatchSource:
    def __init__(self, db_path: Path, table: str) -> None:
        self._db_path = db_path
        self._table = table

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        conn = sqlite3.connect(self._db_path)
        try:
            offset = 0
            while True:
                cur = conn.execute(
                    f"SELECT * FROM {_quote(self._table)} LIMIT ? OFFSET ?",
                    (batch_size, offset),
                )
                rows = cur.fetchall()
                if not rows and offset == 0:
                    names = [d[0] for d in cur.description] if cur.description else ["_empty"]
                    schema = pa.schema([(n, pa.null()) for n in names])
                    yield pa.RecordBatch.from_arrays(
                        [pa.array([], type=pa.null()) for _ in names], schema=schema
                    )
                    return
                if not rows:
                    return
                names = [d[0] for d in cur.description]
                arrays = []
                for idx, _name in enumerate(names):
                    col = [row[idx] for row in rows]
                    arrays.append(pa.array(col))
                yield pa.RecordBatch.from_arrays(arrays, names=names)
                offset += batch_size
                if len(rows) < batch_size:
                    return
        finally:
            conn.close()


class SqliteDataSourcePlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.datasource.sqlite",
            name="SQLite Data Source",
            version="1.0.0",
            api_version=1,
            entry_module="prism_datasource_sqlite.plugin",
            entry_class="SqliteDataSourcePlugin",
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
                contribution_id="prism.datasource.sqlite",
                factory=self,
                display_name="SQLite",
                metadata={"extensions": [".sqlite", ".db", ".sqlite3"]},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context

    def deactivate(self) -> None:
        self._context = None

    def discover(self, connection_or_path: str) -> list[EntityHandle]:
        path = Path(connection_or_path)
        conn = sqlite3.connect(path)
        try:
            cur = conn.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
            handles: list[EntityHandle] = []
            for name, kind in cur.fetchall():
                handles.append(
                    EntityHandle(
                        id=f"{path.resolve()}::{name}",
                        display_name=str(name),
                        kind=str(kind),
                        metadata={"path": str(path), "table": str(name)},
                    )
                )
            return handles
        finally:
            conn.close()

    def preview(self, entity: EntityHandle, options: dict[str, Any] | None = None) -> PreviewResult:
        options = options or {}
        meta = entity.metadata or {}
        path = Path(str(meta["path"]))
        table = str(meta["table"])
        limit = int(options.get("preview_rows", 200))
        conn = sqlite3.connect(path)
        try:
            cur = conn.execute(f"SELECT * FROM {_quote(table)} LIMIT ?", (limit,))
            rows = cur.fetchall()
            names = [d[0] for d in cur.description] if cur.description else []
            if not names:
                schema = pa.schema([])
                return PreviewResult(columns=(), batch=pa.record_batch([], schema=schema))
            arrays = [pa.array([row[i] for row in rows]) for i in range(len(names))]
            batch = pa.RecordBatch.from_arrays(arrays, names=names)
            columns = tuple(
                ColumnDescriptor(name=f.name, logical_type=_logical(f), nullable=True)
                for f in batch.schema
            )
            return PreviewResult(columns=columns, batch=batch)
        finally:
            conn.close()

    def materialize(
        self, entity: EntityHandle, options: dict[str, Any] | None = None
    ) -> MaterializePlan:
        meta = entity.metadata or {}
        path = Path(str(meta["path"]))
        table = str(meta["table"])
        preview = self.preview(entity, options)
        return MaterializePlan(
            columns=preview.columns,
            source=_SqliteBatchSource(path, table),
            suggested_alias=table,
            provenance={
                "plugin_id": self._manifest.id,
                "entity_id": entity.id,
                "path": str(path),
                "table": table,
            },
        )
