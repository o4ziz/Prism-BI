"""Project aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from prism_bi.domain.entities.dataset import Dataset
from prism_bi_sdk.dto.chart import ChartSpec, DashboardSpec
from prism_bi_sdk.dto.report import ReportTemplate


@dataclass
class Project:
    """Root aggregate for a Prism workspace."""

    name: str
    format_version: int = 1
    id: UUID = field(default_factory=uuid4)
    datasets: list[Dataset] = field(default_factory=list)
    pipelines: dict[str, Any] = field(default_factory=dict)
    profiles: dict[str, Any] = field(default_factory=dict)
    charts: list[ChartSpec] = field(default_factory=list)
    dashboards: list[DashboardSpec] = field(default_factory=list)
    reports: list[ReportTemplate] = field(default_factory=list)

    def add_dataset(self, dataset: Dataset) -> None:
        """Attach a dataset to this project."""
        self.datasets.append(dataset)

    def get_dataset(self, dataset_id: UUID) -> Dataset | None:
        """Lookup dataset by id."""
        for dataset in self.datasets:
            if dataset.id == dataset_id:
                return dataset
        return None

    def get_chart(self, chart_id: UUID) -> ChartSpec | None:
        for chart in self.charts:
            if chart.id == chart_id:
                return chart
        return None

    def upsert_chart(self, chart: ChartSpec) -> None:
        for index, existing in enumerate(self.charts):
            if existing.id == chart.id:
                self.charts[index] = chart
                return
        self.charts.append(chart)

    def remove_chart(self, chart_id: UUID) -> bool:
        before = len(self.charts)
        self.charts = [c for c in self.charts if c.id != chart_id]
        return len(self.charts) < before

    def get_dashboard(self, dashboard_id: UUID) -> DashboardSpec | None:
        for dashboard in self.dashboards:
            if dashboard.id == dashboard_id:
                return dashboard
        return None

    def upsert_dashboard(self, dashboard: DashboardSpec) -> None:
        for index, existing in enumerate(self.dashboards):
            if existing.id == dashboard.id:
                self.dashboards[index] = dashboard
                return
        self.dashboards.append(dashboard)

    def remove_dashboard(self, dashboard_id: UUID) -> bool:
        before = len(self.dashboards)
        self.dashboards = [d for d in self.dashboards if d.id != dashboard_id]
        return len(self.dashboards) < before

    def get_report(self, report_id: UUID) -> ReportTemplate | None:
        for report in self.reports:
            if report.id == report_id:
                return report
        return None

    def upsert_report(self, report: ReportTemplate) -> None:
        for index, existing in enumerate(self.reports):
            if existing.id == report.id:
                self.reports[index] = report
                return
        self.reports.append(report)

    def remove_report(self, report_id: UUID) -> bool:
        before = len(self.reports)
        self.reports = [r for r in self.reports if r.id != report_id]
        return len(self.reports) < before

    def dataset_summaries(self) -> tuple[dict[str, Any], ...]:
        """Read-only catalog summaries for PluginContext / UI."""
        rows: list[dict[str, Any]] = []
        for dataset in self.datasets:
            rows.append(
                {
                    "id": str(dataset.id),
                    "alias": dataset.alias,
                    "revision_id": (
                        str(dataset.current_revision_id) if dataset.current_revision_id else None
                    ),
                    "source_plugin_id": dataset.source_plugin_id,
                }
            )
        return tuple(rows)
