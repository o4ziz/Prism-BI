"""Lightweight report templates (V1 — not a full report designer)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReportSectionSpec:
    """Template section — references charts/datasets by id, not raw SQL."""

    kind: str  # heading | notes | chart | dataset
    title: str = ""
    body: str = ""
    chart_id: UUID | None = None
    dataset_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ReportTemplate:
    """Serializable report definition composed of reusable sections.

    Materialization goes through the visualization / tabular export ports so
    templates never touch DuckDB or datasource plugins directly.
    """

    id: UUID
    title: str
    notes: str = ""
    sections: tuple[ReportSectionSpec, ...] = ()
    options: dict[str, Any] = field(default_factory=dict)
