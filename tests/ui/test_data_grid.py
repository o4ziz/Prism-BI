"""Virtual grid can address 100k rows via windowed fetches."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pytest

from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi.presentation.views.data_workspace.table_model import RevisionTableModel
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor, LogicalType


class _Src:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        for start in range(0, self._table.num_rows, batch_size):
            yield self._table.slice(
                start, min(batch_size, self._table.num_rows - start)
            ).to_batches()[0]


@pytest.mark.qt_no_exception_capture
def test_model_window_100k(qtbot, tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "w.duckdb")
    try:
        n = 100_000
        table = pa.table({"id": list(range(n)), "label": [f"r{i}" for i in range(n)]})
        rev = uuid4()
        store.materialize_revision(
            rev,
            MaterializePlan(
                columns=(
                    ColumnDescriptor("id", LogicalType.INTEGER),
                    ColumnDescriptor("label", LogicalType.TEXT),
                ),
                source=_Src(table),
                suggested_alias="big",
                provenance={},
            ),
            chunk_rows=20_000,
        )
        model = RevisionTableModel(store, rev, window_size=500)
        assert model.rowCount() == n
        # Probe first, middle, last windows
        idx_mid = model.index(50_000, 0)
        assert model.data(idx_mid) == "50000"
        idx_last = model.index(n - 1, 0)
        assert model.data(idx_last) == str(n - 1)
    finally:
        store.close()
