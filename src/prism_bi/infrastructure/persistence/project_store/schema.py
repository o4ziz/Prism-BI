"""Project JSON serialization and migrations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.domain.entities.project import Project
from prism_bi.domain.errors import ValidationError
from prism_bi.domain.reporting import report_from_dict, report_to_dict
from prism_bi.domain.value_objects.column_schema import ColumnSchema
from prism_bi.domain.visualization import (
    chart_from_dict,
    chart_to_dict,
    dashboard_from_dict,
    dashboard_to_dict,
)
from prism_bi_sdk.dto.schema import LogicalType

CURRENT_FORMAT_VERSION = 1


def project_to_dict(project: Project) -> dict[str, Any]:
    """Serialize a project aggregate to a JSON-compatible dict."""
    return {
        "format_version": project.format_version,
        "id": str(project.id),
        "name": project.name,
        "datasets": [_dataset_to_dict(dataset) for dataset in project.datasets],
        "pipelines": project.pipelines,
        "profiles": project.profiles,
        "charts": [chart_to_dict(chart) for chart in project.charts],
        "dashboards": [dashboard_to_dict(dashboard) for dashboard in project.dashboards],
        "reports": [report_to_dict(report) for report in project.reports],
    }


def project_from_dict(data: dict[str, Any]) -> Project:
    """Deserialize a project aggregate."""
    version = int(data.get("format_version", 0))
    if version < 1:
        raise ValidationError(f"Unsupported format_version: {version}", code="format_unsupported")
    if version > CURRENT_FORMAT_VERSION:
        raise ValidationError(
            f"Project format_version {version} is newer than supported {CURRENT_FORMAT_VERSION}",
            code="format_too_new",
        )
    data = migrate(data)
    datasets = [_dataset_from_dict(item) for item in data.get("datasets", [])]
    charts = [chart_from_dict(item) for item in data.get("charts", [])]
    dashboards = [dashboard_from_dict(item) for item in data.get("dashboards", [])]
    reports = [report_from_dict(item) for item in data.get("reports", [])]
    return Project(
        name=str(data["name"]),
        format_version=int(data["format_version"]),
        id=UUID(str(data["id"])),
        datasets=datasets,
        pipelines=dict(data.get("pipelines") or {}),
        profiles=dict(data.get("profiles") or {}),
        charts=charts,
        dashboards=dashboards,
        reports=reports,
    )


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Apply additive forward migrations within CURRENT_FORMAT_VERSION.

    Versions below 1 are rejected in ``project_from_dict`` (never shipped).
    Within v1, missing optional keys (charts/dashboards/reports) are filled.
    """
    version = int(data.get("format_version", 0))
    data.setdefault("charts", [])
    data.setdefault("dashboards", [])
    data.setdefault("reports", [])
    data["format_version"] = version
    return data


def load_project_json(path: Path) -> Project:
    """Load ``project.json`` from disk."""
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValidationError("project.json must be an object", code="format_invalid")
    return project_from_dict(raw)


def save_project_json(path: Path, project: Project) -> None:
    """Write ``project.json`` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = project_to_dict(project)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def _dataset_to_dict(dataset: Dataset) -> dict[str, Any]:
    return {
        "id": str(dataset.id),
        "alias": dataset.alias,
        "source_plugin_id": dataset.source_plugin_id,
        "source_entity_id": dataset.source_entity_id,
        "current_revision_id": (
            str(dataset.current_revision_id) if dataset.current_revision_id else None
        ),
        "revisions": [_revision_to_dict(rev) for rev in dataset.revisions],
    }


def _dataset_from_dict(data: dict[str, Any]) -> Dataset:
    revisions = [_revision_from_dict(item) for item in data.get("revisions", [])]
    current = data.get("current_revision_id")
    return Dataset(
        alias=str(data["alias"]),
        id=UUID(str(data["id"])),
        source_plugin_id=str(data.get("source_plugin_id", "")),
        source_entity_id=str(data.get("source_entity_id", "")),
        revisions=revisions,
        current_revision_id=UUID(str(current)) if current else None,
    )


def _revision_to_dict(revision: DatasetRevision) -> dict[str, Any]:
    return {
        "id": str(revision.id),
        "parent_id": str(revision.parent_id) if revision.parent_id else None,
        "created_at": revision.created_at.isoformat(),
        "label": revision.label,
        "columns": [
            {
                "name": col.name,
                "logical_type": col.logical_type.value,
                "nullable": col.nullable,
                "override": col.override,
            }
            for col in revision.columns
        ],
    }


def _revision_from_dict(data: dict[str, Any]) -> DatasetRevision:
    columns = tuple(
        ColumnSchema(
            name=str(col["name"]),
            logical_type=LogicalType(str(col["logical_type"])),
            nullable=bool(col.get("nullable", True)),
            override=bool(col.get("override", False)),
        )
        for col in data.get("columns", [])
    )
    parent = data.get("parent_id")
    created_raw = str(data.get("created_at", datetime.now(UTC).isoformat()))
    created = datetime.fromisoformat(created_raw)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return DatasetRevision(
        id=UUID(str(data["id"])),
        parent_id=UUID(str(parent)) if parent else None,
        created_at=created,
        label=str(data.get("label", "revision")),
        columns=columns,
    )
