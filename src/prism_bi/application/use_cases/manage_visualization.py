"""Chart and dashboard persistence use cases."""

from __future__ import annotations

from uuid import UUID

from prism_bi.application.dto.results import OperationResult
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi_sdk.dto.chart import ChartSpec, DashboardSpec


def save_chart(session: WorkspaceSession, chart: ChartSpec) -> OperationResult[UUID]:
    try:
        project, _ = session.require_project()
        if project.get_dataset(chart.dataset_id) is None:
            raise ValidationError("Chart dataset not found", code="dataset_missing")
        project.upsert_chart(chart)
        session.save()
        return OperationResult.ok(chart.id)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "chart_save_failed"), message=str(exc)
        )


def delete_chart(session: WorkspaceSession, chart_id: UUID) -> OperationResult[bool]:
    try:
        project, _ = session.require_project()
        if not project.remove_chart(chart_id):
            raise ValidationError("Chart not found", code="chart_missing")
        # Drop widgets that referenced the chart
        updated_dashboards: list[DashboardSpec] = []
        for dashboard in project.dashboards:
            widgets = tuple(w for w in dashboard.widgets if w.chart_id != chart_id)
            if len(widgets) != len(dashboard.widgets):
                updated_dashboards.append(
                    DashboardSpec(
                        id=dashboard.id,
                        title=dashboard.title,
                        widgets=widgets,
                        options=dict(dashboard.options),
                    )
                )
            else:
                updated_dashboards.append(dashboard)
        project.dashboards = updated_dashboards
        session.save()
        return OperationResult.ok(True)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "chart_delete_failed"), message=str(exc)
        )


def save_dashboard(session: WorkspaceSession, dashboard: DashboardSpec) -> OperationResult[UUID]:
    try:
        project, _ = session.require_project()
        for widget in dashboard.widgets:
            if project.get_chart(widget.chart_id) is None:
                raise ValidationError(
                    f"Widget references missing chart {widget.chart_id}",
                    code="chart_missing",
                )
        project.upsert_dashboard(dashboard)
        session.save()
        return OperationResult.ok(dashboard.id)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "dashboard_save_failed"), message=str(exc)
        )


def delete_dashboard(session: WorkspaceSession, dashboard_id: UUID) -> OperationResult[bool]:
    try:
        project, _ = session.require_project()
        if not project.remove_dashboard(dashboard_id):
            raise ValidationError("Dashboard not found", code="dashboard_missing")
        session.save()
        return OperationResult.ok(True)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "dashboard_delete_failed"), message=str(exc)
        )
