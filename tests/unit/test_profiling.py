"""Profiling service tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa

from prism_bi.application.use_cases.import_data import import_materialize
from prism_bi.application.use_cases.profile_data import profile_revision
from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.bootstrap.container import build_container
from prism_bi.domain.profiling import infer_logical_type_from_name_and_samples
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.schema import ColumnDescriptor, LogicalType


class _Src:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        yield self._table.to_batches()[0]


def test_infer_types() -> None:
    assert infer_logical_type_from_name_and_samples("amount", ["1", "2"]) == LogicalType.INTEGER
    assert (
        infer_logical_type_from_name_and_samples("flag", ["true", "false"]) == LogicalType.BOOLEAN
    )


def test_profile_report(tmp_path: Path) -> None:
    container = build_container(
        user_data_dir=tmp_path / "user",
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    try:
        assert create_project(container.workspace, tmp_path / "p.prism", "P").success
        table = pa.table({"id": [1, 2, 2], "city": ["A", "B", None]})
        plan = MaterializePlan(
            columns=(
                ColumnDescriptor("id", LogicalType.INTEGER),
                ColumnDescriptor("city", LogicalType.TEXT),
            ),
            source=_Src(table),
            suggested_alias="people",
            provenance={"entity_id": "x"},
        )
        result = import_materialize(
            container.workspace, plugin_id="test", plan=plan, alias="people"
        )
        assert result.success and result.value
        from uuid import UUID

        profile = profile_revision(container.workspace, UUID(result.value))
        assert profile.success and profile.value is not None
        assert profile.value.row_count == 3
        assert len(profile.value.columns) == 2
    finally:
        container.workspace.close()
        container.plugins.deactivate_all()
        container.jobs.shutdown(wait=False)
