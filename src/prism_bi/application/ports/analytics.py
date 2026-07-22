"""Analytics warehouse port — implemented by DuckDB adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

import pyarrow as pa

from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor


@runtime_checkable
class IAnalyticsStore(Protocol):
    """Schema-agnostic tabular store. Physical table names stay internal."""

    def open(self, warehouse_path: Path, *, memory_limit_mb: int | None = None) -> None:
        """Open or create the warehouse file."""

    def close(self) -> None:
        """Release connections."""

    def materialize_revision(
        self,
        revision_id: UUID,
        plan: MaterializePlan,
        *,
        chunk_rows: int,
    ) -> None:
        """Write a new revision table from a plugin materialize plan."""

    def create_revision_as_table(
        self,
        revision_id: UUID,
        *,
        sql_select: str,
    ) -> None:
        """Materialize ``CREATE TABLE … AS <sql_select>`` for a cleaning result."""

    def drop_revision(self, revision_id: UUID) -> None:
        """Drop a physical revision if present."""

    def row_count(self, revision_id: UUID) -> int:
        """Return row count for a revision."""

    def columns(self, revision_id: UUID) -> tuple[ColumnDescriptor, ...]:
        """Return column descriptors inferred from the physical table."""

    def fetch_window(
        self,
        revision_id: UUID,
        *,
        offset: int,
        limit: int,
        order_by: str | None = None,
        descending: bool = False,
    ) -> pa.RecordBatch:
        """Return a window of rows as an Arrow batch."""

    def execute_arrow(self, sql: str) -> pa.Table:
        """Run read-only SQL and return an Arrow table (profiling/aggregates)."""

    def relation_sql(self, revision_id: UUID) -> str:
        """Return a SQL relation identifier for the revision (quoted)."""
