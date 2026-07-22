"""Cleaning pipeline compile + replay identity."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pyarrow as pa

from prism_bi.domain.cleaning import CleaningPipeline, CleaningStep, compile_pipeline_sql
from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor, LogicalType


class _Src:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        yield self._table.to_batches()[0]


def test_cleaning_replay_identity(tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "w.duckdb")
    try:
        table = pa.table({"name": [" Alice ", "Bob", "Alice "], "value": [1, None, 1]})
        rev = uuid4()
        store.materialize_revision(
            rev,
            MaterializePlan(
                columns=(
                    ColumnDescriptor("name", LogicalType.TEXT),
                    ColumnDescriptor("value", LogicalType.INTEGER),
                ),
                source=_Src(table),
                suggested_alias="t",
                provenance={},
            ),
            chunk_rows=100,
        )
        pipeline = CleaningPipeline(
            steps=[
                CleaningStep("trim_column", {"column": "name"}),
                CleaningStep("fill_null", {"column": "value", "value": 0}),
                CleaningStep("dedupe", {"columns": ["name", "value"]}),
            ]
        )
        sql = compile_pipeline_sql(pipeline, store.relation_sql(rev))
        out1 = uuid4()
        out2 = uuid4()
        store.create_revision_as_table(out1, sql_select=sql)
        store.create_revision_as_table(out2, sql_select=sql)
        t1 = store.execute_arrow(f"SELECT * FROM {store.relation_sql(out1)} ORDER BY name")
        t2 = store.execute_arrow(f"SELECT * FROM {store.relation_sql(out2)} ORDER BY name")
        assert t1.to_pydict() == t2.to_pydict()
        assert store.row_count(out1) == 2
    finally:
        store.close()


def test_compile_drop_columns_sql() -> None:
    pipeline = CleaningPipeline(steps=[CleaningStep("drop_columns", {"columns": ["a"]})])
    sql = compile_pipeline_sql(pipeline, '"rev_abc"')
    assert "EXCLUDE" in sql
    assert "rev_abc" in sql
