"""Export and report template use cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from prism_bi.application.dto.results import OperationResult
from prism_bi.application.export.artifact_builder import ExportArtifactBuilder
from prism_bi.application.export.registry import ExporterRegistry
from prism_bi.application.workspace import WorkspaceSession
from prism_bi.domain.errors import DomainError, ValidationError
from prism_bi_sdk.dto.export_artifact import ExportArtifact
from prism_bi_sdk.dto.report import ReportTemplate


def run_export(
    exporters: ExporterRegistry,
    *,
    format_id: str,
    artifact: ExportArtifact,
    destination: Path,
    options: dict[str, Any] | None = None,
) -> OperationResult[Path]:
    try:
        path = exporters.export(format_id, artifact, destination, options=options)
        return OperationResult.ok(path)
    except (KeyError, ValueError, OSError, RuntimeError) as exc:
        return OperationResult.fail(
            error_code="export_failed",
            message=str(exc),
        )


def export_dataset(
    session: WorkspaceSession,
    builder: ExportArtifactBuilder,
    exporters: ExporterRegistry,
    *,
    dataset_id: UUID,
    format_id: str,
    destination: Path,
) -> OperationResult[Path]:
    try:
        _ = session.require_project()
        artifact = builder.dataset_tabular(dataset_id)
        return run_export(
            exporters, format_id=format_id, artifact=artifact, destination=destination
        )
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "export_failed"), message=str(exc)
        )


def export_chart_png(
    session: WorkspaceSession,
    builder: ExportArtifactBuilder,
    exporters: ExporterRegistry,
    *,
    chart_id: UUID,
    destination: Path,
) -> OperationResult[Path]:
    try:
        _ = session.require_project()
        artifact = builder.chart_image(chart_id)
        return run_export(exporters, format_id="png", artifact=artifact, destination=destination)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "export_failed"), message=str(exc)
        )


def export_dashboard_pdf(
    session: WorkspaceSession,
    builder: ExportArtifactBuilder,
    exporters: ExporterRegistry,
    *,
    dashboard_id: UUID,
    destination: Path,
) -> OperationResult[Path]:
    try:
        _ = session.require_project()
        artifact = builder.dashboard_document(dashboard_id)
        return run_export(exporters, format_id="pdf", artifact=artifact, destination=destination)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "export_failed"), message=str(exc)
        )


def export_report(
    session: WorkspaceSession,
    builder: ExportArtifactBuilder,
    exporters: ExporterRegistry,
    *,
    template: ReportTemplate,
    format_id: str,
    destination: Path,
) -> OperationResult[Path]:
    try:
        _ = session.require_project()
        artifact = builder.report_document(template)
        return run_export(
            exporters, format_id=format_id, artifact=artifact, destination=destination
        )
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "export_failed"), message=str(exc)
        )


def save_report_template(
    session: WorkspaceSession, template: ReportTemplate
) -> OperationResult[UUID]:
    try:
        project, _ = session.require_project()
        project.upsert_report(template)
        session.save()
        return OperationResult.ok(template.id)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "report_save_failed"), message=str(exc)
        )


def delete_report_template(session: WorkspaceSession, report_id: UUID) -> OperationResult[bool]:
    try:
        project, _ = session.require_project()
        if not project.remove_report(report_id):
            raise ValidationError("Report template not found", code="report_missing")
        session.save()
        return OperationResult.ok(True)
    except (DomainError, ValidationError, RuntimeError, OSError) as exc:
        return OperationResult.fail(
            error_code=getattr(exc, "code", "report_delete_failed"), message=str(exc)
        )
