"""DuckDB analytics store — serialized access facade (ADR-001)."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from uuid import UUID

import duckdb
import pyarrow as pa

from prism_bi.domain.errors import DomainError
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor, LogicalType

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _relation_name(revision_id: UUID) -> str:
    """Internal physical name — never derived from user aliases."""
    return f"rev_{revision_id.hex}"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _arrow_to_logical(field: pa.Field) -> LogicalType:
    t = field.type
    if pa.types.is_integer(t):
        return LogicalType.INTEGER
    if pa.types.is_floating(t) or pa.types.is_decimal(t):
        return LogicalType.FLOAT
    if pa.types.is_boolean(t):
        return LogicalType.BOOLEAN
    if pa.types.is_timestamp(t) or pa.types.is_date(t):
        return LogicalType.DATETIME
    if pa.types.is_binary(t) or pa.types.is_large_binary(t):
        return LogicalType.BINARY
    if pa.types.is_string(t) or pa.types.is_large_string(t):
        return LogicalType.TEXT
    return LogicalType.UNKNOWN


class DuckDBAnalyticsStore:
    """Single-connection serialized DuckDB facade."""

    def __init__(self) -> None:
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.RLock()
        self._path: Path | None = None

    def open(self, warehouse_path: Path, *, memory_limit_mb: int | None = None) -> None:
        with self._lock:
            self.close()
            warehouse_path.parent.mkdir(parents=True, exist_ok=True)
            self._path = warehouse_path
            self._conn = duckdb.connect(str(warehouse_path))
            # Milestone 5: apply memory budget (ADR-001 single connection retained).
            if memory_limit_mb is not None and memory_limit_mb > 0:
                self._conn.execute(f"SET memory_limit='{int(memory_limit_mb)}MB'")
            self._conn.execute("SET threads TO 2")

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
            self._path = None

    def _require(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            raise DomainError("Analytics store is not open", code="store_closed")
        return self._conn

    def materialize_revision(
        self,
        revision_id: UUID,
        plan: MaterializePlan,
        *,
        chunk_rows: int,
    ) -> None:
        table = _relation_name(revision_id)
        with self._lock:
            conn = self._require()
            conn.execute(f"DROP TABLE IF EXISTS {_quote_ident(table)}")
            first = True
            for batch in plan.source.iter_batches(batch_size=chunk_rows):
                if batch.num_rows == 0 and first:
                    # Create empty table from schema
                    empty = pa.Table.from_batches([], schema=batch.schema)
                    conn.register("_prism_batch", empty)
                    conn.execute(
                        f"CREATE TABLE {_quote_ident(table)} AS SELECT * FROM _prism_batch"
                    )
                    conn.unregister("_prism_batch")
                    first = False
                    continue
                arrow_table = pa.Table.from_batches([batch])
                conn.register("_prism_batch", arrow_table)
                if first:
                    conn.execute(
                        f"CREATE TABLE {_quote_ident(table)} AS SELECT * FROM _prism_batch"
                    )
                    first = False
                else:
                    conn.execute(f"INSERT INTO {_quote_ident(table)} SELECT * FROM _prism_batch")
                conn.unregister("_prism_batch")
            if first:
                # No batches at all — create empty from plan columns
                fields = [
                    pa.field(col.name, _logical_to_arrow(col.logical_type)) for col in plan.columns
                ]
                schema = pa.schema(fields)
                empty = pa.Table.from_batches([], schema=schema)
                conn.register("_prism_batch", empty)
                conn.execute(f"CREATE TABLE {_quote_ident(table)} AS SELECT * FROM _prism_batch")
                conn.unregister("_prism_batch")

    def create_revision_as_table(self, revision_id: UUID, *, sql_select: str) -> None:
        table = _relation_name(revision_id)
        with self._lock:
            conn = self._require()
            conn.execute(f"DROP TABLE IF EXISTS {_quote_ident(table)}")
            conn.execute(f"CREATE TABLE {_quote_ident(table)} AS {sql_select}")

    def drop_revision(self, revision_id: UUID) -> None:
        table = _relation_name(revision_id)
        with self._lock:
            conn = self._require()
            conn.execute(f"DROP TABLE IF EXISTS {_quote_ident(table)}")

    def row_count(self, revision_id: UUID) -> int:
        table = _relation_name(revision_id)
        with self._lock:
            conn = self._require()
            result = conn.execute(f"SELECT COUNT(*) FROM {_quote_ident(table)}").fetchone()
            return int(result[0]) if result else 0

    def fetch_window(
        self,
        revision_id: UUID,
        *,
        offset: int,
        limit: int,
        order_by: str | None = None,
        descending: bool = False,
    ) -> pa.RecordBatch:
        table = _relation_name(revision_id)
        order_sql = ""
        if order_by is not None:
            if not _IDENT.match(order_by):
                raise DomainError("Invalid order_by column", code="invalid_order_by")
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {_quote_ident(order_by)} {direction}"
        sql = (
            f"SELECT * FROM {_quote_ident(table)}{order_sql} "
            f"LIMIT {int(limit)} OFFSET {int(offset)}"
        )
        with self._lock:
            conn = self._require()
            table_arrow = _to_arrow_table(conn.execute(sql))
            if table_arrow.num_rows == 0:
                return pa.RecordBatch.from_arrays(
                    [pa.array([], type=field.type) for field in table_arrow.schema],
                    schema=table_arrow.schema,
                )
            return table_arrow.to_batches()[0]

    def execute_arrow(self, sql: str) -> pa.Table:
        with self._lock:
            conn = self._require()
            return _to_arrow_table(conn.execute(sql))

    def relation_sql(self, revision_id: UUID) -> str:
        return _quote_ident(_relation_name(revision_id))

    def columns(self, revision_id: UUID) -> tuple[ColumnDescriptor, ...]:
        table = _relation_name(revision_id)
        with self._lock:
            conn = self._require()
            arrow = _to_arrow_table(conn.execute(f"SELECT * FROM {_quote_ident(table)} LIMIT 0"))
            return tuple(
                ColumnDescriptor(
                    name=field.name,
                    logical_type=_arrow_to_logical(field),
                    nullable=field.nullable,
                )
                for field in arrow.schema
            )


def _to_arrow_table(result: object) -> pa.Table:
    """Normalize DuckDB query results to a pyarrow Table."""
    to_table = getattr(result, "to_arrow_table", None)
    if callable(to_table):
        table = to_table()
        assert isinstance(table, pa.Table)
        return table
    fetch = getattr(result, "fetch_arrow_table", None)
    if callable(fetch):
        table = fetch()
        assert isinstance(table, pa.Table)
        return table
    arrow = result.arrow()  # type: ignore[attr-defined]
    if isinstance(arrow, pa.Table):
        return arrow
    batches = list(arrow)
    if not batches:
        schema = getattr(arrow, "schema", None)
        if schema is not None:
            return pa.Table.from_batches([], schema=schema)
        return pa.table({})
    return pa.Table.from_batches(batches)


def _logical_to_arrow(logical: LogicalType) -> pa.DataType:
    mapping = {
        LogicalType.INTEGER: pa.int64(),
        LogicalType.FLOAT: pa.float64(),
        LogicalType.BOOLEAN: pa.bool_(),
        LogicalType.DATETIME: pa.timestamp("us"),
        LogicalType.CATEGORICAL: pa.string(),
        LogicalType.TEXT: pa.string(),
        LogicalType.BINARY: pa.binary(),
        LogicalType.UNKNOWN: pa.string(),
    }
    return mapping.get(logical, pa.string())
