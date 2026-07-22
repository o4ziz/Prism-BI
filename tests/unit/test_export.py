"""Export and report template tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pyarrow as pa

from prism_bi.application.export import ExportArtifactBuilder, ExporterRegistry
from prism_bi.application.use_cases.export_data import export_dataset, save_report_template
from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.application.visualization import AnalyticsChartDataProvider
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.bootstrap.container import build_container
from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.domain.reporting import report_from_dict, report_to_dict
from prism_bi.infrastructure.persistence.duckdb import DuckDBAnalyticsStore
from prism_bi.infrastructure.persistence.project_store import PrismProjectStore
from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.dto.export_artifact import ExportArtifact
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.report import ReportSectionSpec, ReportTemplate
from prism_bi_sdk.dto.schema import ColumnDescriptor, LogicalType


class _ListSource:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        for start in range(0, self._table.num_rows, batch_size):
            yield self._table.slice(
                start, min(batch_size, self._table.num_rows - start)
            ).to_batches()[0]


def test_report_template_round_trip() -> None:
    template = ReportTemplate(
        id=uuid4(),
        title="Weekly",
        notes="Ops summary",
        sections=(
            ReportSectionSpec(kind="heading", title="Overview"),
            ReportSectionSpec(kind="chart", title="Sales", chart_id=uuid4()),
            ReportSectionSpec(kind="dataset", title="Raw", dataset_id=uuid4()),
        ),
    )
    assert report_from_dict(report_to_dict(template)) == template


def test_exporters_loaded(tmp_path: Path) -> None:
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    try:
        regs = container.plugins.registry.list_by_kind(ContributionKind.EXPORTERS)
        ids = {r.contribution_id for r in regs}
        assert "prism.exporter.tabular" in ids
        assert "prism.exporter.image" in ids
        assert "prism.exporter.pdf" in ids
        formats = container.exporters.available_formats()
        for expected in ("csv", "xlsx", "json", "png", "pdf"):
            assert expected in formats
    finally:
        container.plugins.deactivate_all()
        container.workspace.close()
        container.jobs.shutdown(wait=False)


def test_tabular_export_csv_xlsx_json(tmp_path: Path) -> None:
    store = DuckDBAnalyticsStore()
    store.open(tmp_path / "w.duckdb")
    project_store = PrismProjectStore()
    session = WorkspaceSession(
        project_store=project_store,
        analytics=store,
        recent_file=tmp_path / "recent.json",
    )
    create_project(session, tmp_path / "p.prism", "Export")
    assert session.project is not None

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
        alias="sales",
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
    session.project.add_dataset(dataset)
    session.save()

    container = build_container(
        user_data_dir=tmp_path / "ud",
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    try:
        # Re-bind session analytics into builder via fresh builder on same store
        chart_data = AnalyticsChartDataProvider(store, project_provider=lambda: session.project)
        builder = ExportArtifactBuilder(store, chart_data, project_provider=lambda: session.project)
        exporters = ExporterRegistry(container.plugins.registry)
        for fmt, suffix in (("csv", ".csv"), ("json", ".json"), ("xlsx", ".xlsx")):
            dest = tmp_path / f"out{suffix}"
            result = export_dataset(
                session,
                builder,
                exporters,
                dataset_id=dataset.id,
                format_id=fmt,
                destination=dest,
            )
            assert result.success, result.message
            assert dest.is_file()
            assert dest.stat().st_size > 0
    finally:
        container.plugins.deactivate_all()
        container.jobs.shutdown(wait=False)
        session.close()


def test_png_and_pdf_export(qtbot, tmp_path: Path) -> None:
    container = build_container(
        user_data_dir=tmp_path / "ud",
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    try:
        from prism_bi.application.use_cases.export_data import (
            export_chart_png,
            export_dashboard_pdf,
        )
        from prism_bi.application.use_cases.project_lifecycle import create_project
        from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec, DashboardSpec, DashboardWidget

        root = tmp_path / "viz.prism"
        assert create_project(container.workspace, root, "Viz").success
        store = container.workspace.analytics
        table = pa.table({"region": ["A", "B"], "amount": [10.0, 20.0]})
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
            alias="sales",
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
        assert container.workspace.project is not None
        container.workspace.project.add_dataset(dataset)
        chart = ChartSpec(
            id=uuid4(),
            chart_type="bar",
            dataset_id=dataset.id,
            title="By region",
            encodings=(
                ChartEncoding(role="x", field="region"),
                ChartEncoding(role="y", field="amount", aggregation="sum"),
            ),
        )
        container.workspace.project.upsert_chart(chart)
        dash = DashboardSpec(
            id=uuid4(),
            title="Board",
            widgets=(DashboardWidget(id=uuid4(), chart_id=chart.id, x=0, y=0, width=4, height=3),),
        )
        container.workspace.project.upsert_dashboard(dash)
        container.workspace.save()

        png = tmp_path / "chart.png"
        result = export_chart_png(
            container.workspace,
            container.export_builder,
            container.exporters,
            chart_id=chart.id,
            destination=png,
        )
        assert result.success, result.message
        assert png.is_file() and png.stat().st_size > 0

        pdf = tmp_path / "dash.pdf"
        result = export_dashboard_pdf(
            container.workspace,
            container.export_builder,
            container.exporters,
            dashboard_id=dash.id,
            destination=pdf,
        )
        assert result.success, result.message
        assert pdf.is_file() and pdf.stat().st_size > 0
    finally:
        container.plugins.deactivate_all()
        container.workspace.close()
        container.jobs.shutdown(wait=False)


def test_save_report_template_persists(tmp_path: Path) -> None:
    store = PrismProjectStore()
    analytics = DuckDBAnalyticsStore()
    session = WorkspaceSession(
        project_store=store,
        analytics=analytics,
        recent_file=tmp_path / "recent.json",
    )
    root = tmp_path / "r.prism"
    assert create_project(session, root, "R").success
    template = ReportTemplate(
        id=uuid4(),
        title="T",
        notes="n",
        sections=(ReportSectionSpec(kind="notes", title="A", body="hello"),),
    )
    assert save_report_template(session, template).success
    loaded = store.open(root)
    assert loaded.get_report(template.id) == template
    session.close()


def test_fake_exporter_contract() -> None:
    from prism_bi_sdk import (
        API_VERSION_MAJOR,
        ContributionKind,
        ContributionRegistration,
        PluginManifest,
    )

    class _Fake:
        def __init__(self) -> None:
            self._manifest = PluginManifest(
                id="partner.exporter.fake",
                name="Fake",
                version="0.0.1",
                api_version=API_VERSION_MAJOR,
                entry_module="x",
                entry_class="Y",
            )

        @property
        def manifest(self) -> PluginManifest:
            return self._manifest

        def register(self, registry: object) -> None:
            registry.add(  # type: ignore[attr-defined]
                ContributionRegistration(
                    kind=ContributionKind.EXPORTERS,
                    contribution_id="partner.exporter.fake",
                    factory=self,
                )
            )

        def activate(self, context: object) -> None:
            _ = context

        def deactivate(self) -> None:
            return None

        def format_ids(self) -> tuple[str, ...]:
            return ("fake",)

        def supports(self, artifact: ExportArtifact, format_id: str) -> bool:
            return format_id == "fake" and artifact.kind == "tabular"

        def export(
            self,
            artifact: ExportArtifact,
            destination: Path,
            *,
            format_id: str,
            options: dict | None = None,
        ) -> Path:
            _ = artifact, format_id, options
            destination.write_text("ok", encoding="utf-8")
            return destination

    class _Reg:
        def __init__(self) -> None:
            self.items: list[ContributionRegistration] = []

        def add(self, registration: ContributionRegistration) -> None:
            self.items.append(registration)

    plugin = _Fake()
    reg = _Reg()
    plugin.register(reg)
    assert reg.items[0].kind == ContributionKind.EXPORTERS
    art = ExportArtifact(kind="tabular", title="t", table=pa.table({"a": [1]}))
    assert plugin.supports(art, "fake")
    assert "fake" in plugin.format_ids()
