"""Build ExportArtifacts from project data without exposing DuckDB to plugins."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from prism_bi.application.ports.analytics import IAnalyticsStore
from prism_bi.application.ports.chart_data import IChartDataProvider
from prism_bi.application.ports.chart_image import IChartImageRenderer
from prism_bi.domain.entities.project import Project
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi_sdk.dto.export_artifact import ExportArtifact, ExportSection
from prism_bi_sdk.dto.report import ReportTemplate


class ExportArtifactBuilder:
    """Materializes tabular / image / document artifacts via application ports."""

    def __init__(
        self,
        store: IAnalyticsStore,
        chart_data: IChartDataProvider,
        *,
        project_provider: Callable[[], Project | None],
        image_renderer: IChartImageRenderer | None = None,
        max_export_rows: int = 1_000_000,
    ) -> None:
        self._store = store
        self._chart_data = chart_data
        self._project_provider = project_provider
        self._image_renderer = image_renderer
        self._max_export_rows = max_export_rows

    def set_image_renderer(self, renderer: IChartImageRenderer) -> None:
        self._image_renderer = renderer

    def dataset_tabular(self, dataset_id: UUID, *, title: str | None = None) -> ExportArtifact:
        project = self._require_project()
        dataset = project.get_dataset(dataset_id)
        if dataset is None or dataset.current_revision_id is None:
            raise DomainError("Dataset revision not found", code="dataset_missing")
        relation = self._store.relation_sql(dataset.current_revision_id)
        table = self._store.execute_arrow(f"SELECT * FROM {relation} LIMIT {self._max_export_rows}")
        return ExportArtifact(
            kind="tabular",
            title=title or dataset.alias,
            table=table,
            metadata={
                "dataset_id": str(dataset_id),
                "row_count": table.num_rows,
                "truncated": table.num_rows >= self._max_export_rows,
            },
        )

    def chart_image(self, chart_id: UUID) -> ExportArtifact:
        project = self._require_project()
        chart = project.get_chart(chart_id)
        if chart is None:
            raise ValidationError("Chart not found", code="chart_missing")
        png = self._render_chart_png(chart.id)
        return ExportArtifact(
            kind="image",
            title=chart.title,
            image_png=png,
            metadata={"chart_id": str(chart_id), "chart_type": chart.chart_type},
        )

    def dashboard_document(self, dashboard_id: UUID) -> ExportArtifact:
        project = self._require_project()
        dashboard = project.get_dashboard(dashboard_id)
        if dashboard is None:
            raise ValidationError("Dashboard not found", code="dashboard_missing")
        sections: list[ExportSection] = [
            ExportSection(kind="heading", title=dashboard.title),
        ]
        notes = str(dashboard.options.get("notes", "") or "")
        if notes:
            sections.append(ExportSection(kind="text", title="Notes", text=notes))
        for widget in dashboard.widgets:
            chart = project.get_chart(widget.chart_id)
            if chart is None:
                continue
            try:
                png = self._render_chart_png(chart.id)
            except Exception as exc:  # noqa: BLE001
                sections.append(
                    ExportSection(
                        kind="text",
                        title=chart.title,
                        text=f"(Chart render failed: {exc})",
                    )
                )
                continue
            sections.append(ExportSection(kind="image", title=chart.title, image_png=png))
        return ExportArtifact(
            kind="document",
            title=dashboard.title,
            sections=tuple(sections),
            metadata={"dashboard_id": str(dashboard_id)},
        )

    def report_document(self, template: ReportTemplate) -> ExportArtifact:
        """Materialize a report template through viz/tabular ports (no DuckDB in plugins)."""
        project = self._require_project()
        sections: list[ExportSection] = [
            ExportSection(kind="heading", title=template.title),
        ]
        if template.notes:
            sections.append(ExportSection(kind="text", title="Notes", text=template.notes))
        for spec in template.sections:
            if spec.kind == "heading":
                sections.append(ExportSection(kind="heading", title=spec.title or spec.body))
            elif spec.kind == "notes":
                sections.append(ExportSection(kind="text", title=spec.title, text=spec.body))
            elif spec.kind == "chart":
                if spec.chart_id is None or project.get_chart(spec.chart_id) is None:
                    sections.append(
                        ExportSection(
                            kind="text",
                            title=spec.title or "Chart",
                            text="(Missing chart reference)",
                        )
                    )
                    continue
                chart = project.get_chart(spec.chart_id)
                assert chart is not None
                png = self._render_chart_png(chart.id)
                sections.append(
                    ExportSection(
                        kind="image",
                        title=spec.title or chart.title,
                        image_png=png,
                    )
                )
            elif spec.kind == "dataset":
                if spec.dataset_id is None:
                    continue
                tabular = self.dataset_tabular(spec.dataset_id, title=spec.title or "Data")
                assert tabular.table is not None
                # Cap preview rows in document tables for PDF readability
                preview = tabular.table.slice(0, min(200, tabular.table.num_rows))
                sections.append(
                    ExportSection(
                        kind="table",
                        title=spec.title or tabular.title,
                        table=preview,
                    )
                )
            else:
                sections.append(
                    ExportSection(
                        kind="text",
                        title=spec.title,
                        text=spec.body or f"(Unknown section kind: {spec.kind})",
                    )
                )
        return ExportArtifact(
            kind="document",
            title=template.title,
            sections=tuple(sections),
            metadata={"report_id": str(template.id)},
        )

    def _render_chart_png(self, chart_id: UUID) -> bytes:
        if self._image_renderer is None:
            raise DomainError(
                "Chart image renderer is not configured", code="image_renderer_missing"
            )
        project = self._require_project()
        chart = project.get_chart(chart_id)
        if chart is None:
            raise ValidationError("Chart not found", code="chart_missing")
        data = self._chart_data.query(chart)
        return self._image_renderer.to_png(chart, data)

    def _require_project(self) -> Project:
        project = self._project_provider()
        if project is None:
            raise DomainError("No project open", code="no_project")
        return project
