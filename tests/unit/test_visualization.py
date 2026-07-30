"""Chart / dashboard persistence and visualization unit tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pytest

from prism_bi.application.use_cases.manage_visualization import save_chart, save_dashboard
from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.application.visualization.chart_data_provider import AnalyticsChartDataProvider
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.domain.errors import ValidationError
from prism_bi.domain.visualization import (
    chart_from_dict,
    chart_to_dict,
    dashboard_from_dict,
    dashboard_to_dict,
)
from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi.infrastructure.persistence.project_store import PrismProjectStore
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec, DashboardSpec, DashboardWidget
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


def test_chart_spec_round_trip() -> None:
    chart = ChartSpec(
        id=uuid4(),
        chart_type="bar",
        dataset_id=uuid4(),
        title="Sales",
        encodings=(
            ChartEncoding(role="x", field="region"),
            ChartEncoding(role="y", field="amount", aggregation="sum"),
        ),
        options={"filters": [{"field": "region", "op": "eq", "value": "West"}]},
    )
    restored = chart_from_dict(chart_to_dict(chart))
    assert restored == chart


def test_dashboard_spec_round_trip() -> None:
    dash = DashboardSpec(
        id=uuid4(),
        title="Ops",
        widgets=(DashboardWidget(id=uuid4(), chart_id=uuid4(), x=0, y=0, width=4, height=3),),
        options={"filters": []},
    )
    assert dashboard_from_dict(dashboard_to_dict(dash)) == dash


def test_project_persists_charts_and_dashboards(tmp_path: Path) -> None:
    store = PrismProjectStore()
    root = tmp_path / "viz.prism"
    project = store.create(root, "Viz")
    dataset_id = uuid4()
    chart = ChartSpec(
        id=uuid4(),
        chart_type="line",
        dataset_id=dataset_id,
        title="Trend",
        encodings=(ChartEncoding(role="x", field="month"),),
    )
    dash = DashboardSpec(
        id=uuid4(),
        title="Board",
        widgets=(DashboardWidget(id=uuid4(), chart_id=chart.id, x=0, y=0, width=6, height=4),),
    )
    project.upsert_chart(chart)
    project.upsert_dashboard(dash)
    store.save(root, project)
    loaded = store.open(root)
    assert loaded.get_chart(chart.id) == chart
    assert loaded.get_dashboard(dash.id) == dash


def test_chart_data_provider_aggregates_and_caps(tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "w.duckdb")
    try:
        table = pa.table(
            {
                "region": ["A", "A", "B", "B", "C"],
                "amount": [10.0, 20.0, 5.0, 15.0, 100.0],
            }
        )
        revision = uuid4()
        plan = MaterializePlan(
            columns=(
                ColumnDescriptor("region", LogicalType.TEXT),
                ColumnDescriptor("amount", LogicalType.FLOAT),
            ),
            source=_ListSource(table),
            suggested_alias="sales",
            provenance={},
        )
        store.materialize_revision(revision, plan, chunk_rows=100)

        from datetime import UTC, datetime

        from prism_bi.domain.entities.project import Project

        dataset = Dataset(
            alias="sales",
            id=uuid4(),
            source_plugin_id="test",
            source_entity_id="t",
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

        provider = AnalyticsChartDataProvider(
            store,
            project_provider=lambda: project,
            max_points=10,
            max_categories=2,
        )
        spec = ChartSpec(
            id=uuid4(),
            chart_type="bar",
            dataset_id=dataset.id,
            title="By region",
            encodings=(
                ChartEncoding(role="x", field="region"),
                ChartEncoding(role="y", field="amount", aggregation="sum"),
            ),
        )
        data = provider.query(spec)
        assert data.category_column == "category"
        assert data.batch.num_rows == 2  # capped
        assert data.truncated is True

        filtered = ChartSpec(
            id=uuid4(),
            chart_type="bar",
            dataset_id=dataset.id,
            title="West-ish",
            encodings=(
                ChartEncoding(role="x", field="region"),
                ChartEncoding(role="y", field="amount", aggregation="sum"),
            ),
            options={"filters": [{"field": "region", "op": "eq", "value": "A"}]},
        )
        fdata = provider.query(filtered)
        assert fdata.batch.num_rows == 1
        assert fdata.batch.column("value")[0].as_py() == pytest.approx(30.0)

        hist_provider = AnalyticsChartDataProvider(
            store,
            project_provider=lambda: project,
            max_categories=50,
        )
        hist = ChartSpec(
            id=uuid4(),
            chart_type="histogram",
            dataset_id=dataset.id,
            title="Amounts",
            encodings=(ChartEncoding(role="x", field="amount"),),
        )
        hdata = hist_provider.query(hist)
        assert hdata.category_column == "category"
        assert hdata.batch.num_rows >= 1
        assert sum(hdata.batch.column("value").to_pylist()) == 5

        with pytest.raises(ValidationError, match="numeric"):
            hist_provider.query(
                ChartSpec(
                    id=uuid4(),
                    chart_type="histogram",
                    dataset_id=dataset.id,
                    title="Bad",
                    encodings=(ChartEncoding(role="x", field="region"),),
                )
            )
    finally:
        store.close()


def test_save_chart_and_dashboard_use_cases(tmp_path: Path) -> None:
    store = PrismProjectStore()
    analytics = DuckDBAnalyticsStore()
    session = WorkspaceSession(
        project_store=store,
        analytics=analytics,
        recent_file=tmp_path / "recent.json",
    )
    root = tmp_path / "proj.prism"
    result = create_project(session, root, "Demo")
    assert result.success
    assert session.project is not None

    dataset_id = uuid4()
    session.project.add_dataset(
        Dataset(
            alias="d",
            id=dataset_id,
            source_plugin_id="x",
            source_entity_id="y",
        )
    )
    chart = ChartSpec(
        id=uuid4(),
        chart_type="pie",
        dataset_id=dataset_id,
        title="Share",
        encodings=(ChartEncoding(role="x", field="cat"),),
    )
    assert save_chart(session, chart).success
    dash = DashboardSpec(
        id=uuid4(),
        title="Main",
        widgets=(DashboardWidget(id=uuid4(), chart_id=chart.id, x=0, y=0, width=4, height=3),),
    )
    assert save_dashboard(session, dash).success
    reopened = store.open(root)
    assert reopened.get_chart(chart.id) is not None
    assert reopened.get_dashboard(dash.id) is not None
    session.close()
