"""DuckDB analytics store integration tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pyarrow as pa

from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor, LogicalType


class _ListSource:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        for start in range(0, self._table.num_rows, batch_size):
            yield self._table.slice(
                start, min(batch_size, self._table.num_rows - start)
            ).to_batches()[0]


def test_materialize_and_window(tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "warehouse.duckdb")
    try:
        table = pa.table({"id": list(range(1000)), "name": [f"r{i}" for i in range(1000)]})
        revision = uuid4()
        plan = MaterializePlan(
            columns=(
                ColumnDescriptor("id", LogicalType.INTEGER),
                ColumnDescriptor("name", LogicalType.TEXT),
            ),
            source=_ListSource(table),
            suggested_alias="t",
            provenance={},
        )
        store.materialize_revision(revision, plan, chunk_rows=250)
        assert store.row_count(revision) == 1000
        batch = store.fetch_window(revision, offset=100, limit=50)
        assert batch.num_rows == 50
        assert batch.column("id")[0].as_py() == 100
    finally:
        store.close()


def test_internal_relation_not_user_alias(tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "w.duckdb")
    try:
        revision = uuid4()
        assert "Sales" not in store.relation_sql(revision)
        assert "rev_" in store.relation_sql(revision)
    finally:
        store.close()
