"""QtCharts plugin + chart host integration."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pytest

from prism_bi.application.visualization import AnalyticsChartDataProvider, ChartRendererRegistry
from prism_bi.bootstrap.container import build_container
from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.domain.entities.project import Project
from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi.presentation.widgets.chart_host import ChartHostWidget
from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec
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


@pytest.fixture
def container(tmp_path: Path):
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    yield container
    container.plugins.deactivate_all()
    container.workspace.close()
    container.jobs.shutdown(wait=False)


def test_qtcharts_plugin_loaded(container) -> None:
    charts = container.plugins.registry.list_by_kind(ContributionKind.CHARTS)
    assert any(c.contribution_id == "prism.chart.qtcharts" for c in charts)
    types = container.chart_renderers.available_types()
    for expected in ("bar", "line", "area", "pie", "scatter", "histogram", "table"):
        assert expected in types


def test_chart_host_renders_and_exports_png(qtbot, container, tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "warehouse.duckdb")
    try:
        table = pa.table({"region": ["N", "S"], "amount": [1.0, 2.0]})
        revision = uuid4()
        store.materialize_revision(
            revision,
            MaterializePlan(
                columns=(
                    ColumnDescriptor("region", LogicalType.TEXT),
                    ColumnDescriptor("amount", LogicalType.FLOAT),
                ),
                source=_ListSource(table),
                suggested_alias="t",
                provenance={},
            ),
            chunk_rows=100,
        )
        dataset = Dataset(
            alias="t",
            id=uuid4(),
            source_plugin_id="x",
            source_entity_id="y",
            revisions=[
                DatasetRevision(
                    id=revision,
                    parent_id=None,
                    created_at=datetime.now(UTC),
                    label="raw",
                    columns=(),
                )
            ],
            current_revision_id=revision,
        )
        project = Project(name="p", datasets=[dataset])
        provider = AnalyticsChartDataProvider(store, project_provider=lambda: project)
        registry = ChartRendererRegistry(container.plugins.registry)
        host = ChartHostWidget(provider, registry)
        qtbot.addWidget(host)
        host.show()
        spec = ChartSpec(
            id=uuid4(),
            chart_type="bar",
            dataset_id=dataset.id,
            title="Regions",
            encodings=(
                ChartEncoding(role="x", field="region"),
                ChartEncoding(role="y", field="amount", aggregation="sum"),
            ),
        )
        host.bind(spec)
        assert host.current_view is not None
        out = tmp_path / "chart.png"
        host.export_png(str(out))
        assert out.is_file()
        assert out.stat().st_size > 0
    finally:
        store.close()
