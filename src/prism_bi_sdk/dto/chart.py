"""Visualization document shapes shared by host and chart plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChartEncoding:
    """Field-role binding for a chart."""

    role: str
    field: str
    aggregation: str | None = None


@dataclass(frozen=True, slots=True)
class ChartSpec:
    """Serializable chart definition (viz-as-data)."""

    id: UUID
    chart_type: str
    dataset_id: UUID
    title: str
    encodings: tuple[ChartEncoding, ...]
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DashboardWidget:
    """Widget placement on a dashboard canvas."""

    id: UUID
    chart_id: UUID
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class DashboardSpec:
    """Serializable dashboard layout."""

    id: UUID
    title: str
    widgets: tuple[DashboardWidget, ...]
    options: dict[str, Any] = field(default_factory=dict)
