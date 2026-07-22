"""Data source plugin contracts."""

from __future__ import annotations

from enum import Flag, auto
from typing import Any, Protocol, runtime_checkable

from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.preview import PreviewResult
from prism_bi_sdk.dto.schema import EntityHandle
from prism_bi_sdk.plugin import IPlugin


class DataSourceCapability(Flag):
    """Capabilities declared by a data source plugin."""

    BATCH_IMPORT = auto()
    LIVE_QUERY = auto()


@runtime_checkable
class IDataSourcePlugin(IPlugin, Protocol):
    """File/DB/API connector plugin."""

    @property
    def capabilities(self) -> DataSourceCapability:
        """Return supported capability flags."""

    def discover(self, connection_or_path: str) -> list[EntityHandle]:
        """List discoverable entities (sheets, tables, resources)."""

    def preview(self, entity: EntityHandle, options: dict[str, Any] | None = None) -> PreviewResult:
        """Return a capped preview for wizard display."""

    def materialize(
        self, entity: EntityHandle, options: dict[str, Any] | None = None
    ) -> MaterializePlan:
        """Return a plan for the application to write into the warehouse."""


@runtime_checkable
class IQueryableSource(Protocol):
    """Live-query surface for connectors with ``LIVE_QUERY`` capability."""

    def execute(self, query: str, *, limit: int | None = None) -> PreviewResult:
        """Execute a query and return a tabular batch (Arrow-backed)."""

    def estimate_cost(self, query: str) -> float | None:
        """Optional relative cost estimate; ``None`` if unknown."""
