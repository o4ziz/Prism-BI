"""Chart data provider port — visualization stays warehouse-agnostic."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData
from prism_bi_sdk.dto.schema import ColumnDescriptor


@runtime_checkable
class IChartDataProvider(Protocol):
    """Resolves ``ChartSpec`` into aggregated ``ChartData``.

    Implementations may use ``IAnalyticsStore`` internally. Chart plugins and
    presentation widgets must depend only on this port (or ``ChartData``), never
    on DuckDB or datasource plugins.
    """

    def query(self, spec: ChartSpec) -> ChartData:
        """Execute aggregations for the chart and return capped series data."""

    def list_fields(self, dataset_id: UUID) -> tuple[ColumnDescriptor, ...]:
        """Return columns available for encodings on the dataset's current revision."""
