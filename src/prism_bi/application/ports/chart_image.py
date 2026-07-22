"""Chart image renderer port — PNG bytes without exporter coupling."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData


@runtime_checkable
class IChartImageRenderer(Protocol):
    """Renders a chart to PNG bytes using the active chart engine."""

    def to_png(self, spec: ChartSpec, data: ChartData) -> bytes:
        """Return PNG bytes for the given spec + aggregated data."""
