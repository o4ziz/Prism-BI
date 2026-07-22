"""Visualization document helpers (domain facade over SDK DTOs)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from prism_bi_sdk.dto.chart import (
    ChartEncoding,
    ChartSpec,
    DashboardSpec,
    DashboardWidget,
)

__all__ = [
    "ChartEncoding",
    "ChartSpec",
    "DashboardSpec",
    "DashboardWidget",
    "chart_from_dict",
    "chart_to_dict",
    "dashboard_from_dict",
    "dashboard_to_dict",
]


def chart_to_dict(spec: ChartSpec) -> dict[str, Any]:
    return {
        "id": str(spec.id),
        "chart_type": spec.chart_type,
        "dataset_id": str(spec.dataset_id),
        "title": spec.title,
        "encodings": [
            {
                "role": enc.role,
                "field": enc.field,
                "aggregation": enc.aggregation,
            }
            for enc in spec.encodings
        ],
        "options": dict(spec.options),
    }


def chart_from_dict(data: dict[str, Any]) -> ChartSpec:
    encodings = tuple(
        ChartEncoding(
            role=str(item["role"]),
            field=str(item["field"]),
            aggregation=item.get("aggregation"),
        )
        for item in data.get("encodings", [])
    )
    return ChartSpec(
        id=UUID(str(data["id"])),
        chart_type=str(data["chart_type"]),
        dataset_id=UUID(str(data["dataset_id"])),
        title=str(data.get("title", "")),
        encodings=encodings,
        options=dict(data.get("options") or {}),
    )


def dashboard_to_dict(spec: DashboardSpec) -> dict[str, Any]:
    return {
        "id": str(spec.id),
        "title": spec.title,
        "widgets": [
            {
                "id": str(w.id),
                "chart_id": str(w.chart_id),
                "x": w.x,
                "y": w.y,
                "width": w.width,
                "height": w.height,
            }
            for w in spec.widgets
        ],
        "options": dict(spec.options),
    }


def dashboard_from_dict(data: dict[str, Any]) -> DashboardSpec:
    widgets = tuple(
        DashboardWidget(
            id=UUID(str(item["id"])),
            chart_id=UUID(str(item["chart_id"])),
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            width=int(item.get("width", 4)),
            height=int(item.get("height", 3)),
        )
        for item in data.get("widgets", [])
    )
    return DashboardSpec(
        id=UUID(str(data["id"])),
        title=str(data.get("title", "")),
        widgets=widgets,
        options=dict(data.get("options") or {}),
    )
