"""Chart plugin contract — replaceable chart engines."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData
from prism_bi_sdk.plugin import IPlugin


@runtime_checkable
class IChartPlugin(IPlugin, Protocol):
    """Renders a ``ChartSpec`` + ``ChartData`` into a host view.

    Chart engines (QtCharts, pyqtgraph, web, …) implement this protocol.
    They must not import DuckDB, datasource plugins, or project stores.
    Application logic depends on this contract, never on a concrete engine.
    """

    def chart_types(self) -> tuple[str, ...]:
        """Stable chart type ids this engine can render (e.g. ``bar``, ``line``)."""

    def create_view(self, spec: ChartSpec, data: ChartData, parent: Any) -> Any:
        """Return a view widget for the host to embed (opaque to the SDK)."""

    def supports_export_image(self) -> bool:
        """Return True if ``export_image`` is implemented."""

    def export_image(self, view: Any, destination: str) -> None:
        """Optional PNG/raster export of an existing view (path as str)."""
