"""Report template helpers (domain facade over SDK DTOs)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from prism_bi_sdk.dto.report import ReportSectionSpec, ReportTemplate

__all__ = [
    "ReportSectionSpec",
    "ReportTemplate",
    "report_from_dict",
    "report_to_dict",
]


def report_to_dict(template: ReportTemplate) -> dict[str, Any]:
    return {
        "id": str(template.id),
        "title": template.title,
        "notes": template.notes,
        "sections": [
            {
                "kind": section.kind,
                "title": section.title,
                "body": section.body,
                "chart_id": str(section.chart_id) if section.chart_id else None,
                "dataset_id": str(section.dataset_id) if section.dataset_id else None,
            }
            for section in template.sections
        ],
        "options": dict(template.options),
    }


def report_from_dict(data: dict[str, Any]) -> ReportTemplate:
    sections = tuple(
        ReportSectionSpec(
            kind=str(item.get("kind", "notes")),
            title=str(item.get("title", "")),
            body=str(item.get("body", "")),
            chart_id=UUID(str(item["chart_id"])) if item.get("chart_id") else None,
            dataset_id=UUID(str(item["dataset_id"])) if item.get("dataset_id") else None,
        )
        for item in data.get("sections", [])
    )
    return ReportTemplate(
        id=UUID(str(data["id"])),
        title=str(data.get("title", "")),
        notes=str(data.get("notes", "")),
        sections=sections,
        options=dict(data.get("options") or {}),
    )
