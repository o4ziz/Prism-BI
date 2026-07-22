"""Chart registry — maps chart_type → IChartPlugin without hardcoding engines."""

from __future__ import annotations

from typing import Any

from prism_bi_sdk.charts import IChartPlugin
from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData


class ChartRendererRegistry:
    """Looks up chart plugins by ``chart_type`` from the contribution registry."""

    def __init__(self, contribution_registry: Any) -> None:
        self._contributions = contribution_registry

    def available_types(self) -> list[str]:
        types: list[str] = []
        for reg in self._contributions.list_by_kind(ContributionKind.CHARTS):
            plugin = reg.factory
            types_fn = getattr(plugin, "chart_types", None)
            if callable(types_fn):
                types.extend(list(types_fn()))
            else:
                chart_type = getattr(plugin, "chart_type", None)
                if isinstance(chart_type, str):
                    types.append(chart_type)
        return sorted(set(types))

    def get_plugin(self, chart_type: str) -> IChartPlugin | None:
        for reg in self._contributions.list_by_kind(ContributionKind.CHARTS):
            plugin = reg.factory
            types_fn = getattr(plugin, "chart_types", None)
            if callable(types_fn) and chart_type in types_fn():
                return plugin  # type: ignore[no-any-return]
            if getattr(plugin, "chart_type", None) == chart_type:
                return plugin  # type: ignore[no-any-return]
        return None

    def create_view(self, spec: ChartSpec, data: ChartData, parent: Any) -> Any:
        plugin = self.get_plugin(spec.chart_type)
        if plugin is None:
            raise KeyError(f"No chart plugin for type: {spec.chart_type}")
        return plugin.create_view(spec, data, parent)

    def export_image(self, spec: ChartSpec, view: Any, destination: str) -> None:
        plugin = self.get_plugin(spec.chart_type)
        if plugin is None:
            raise KeyError(f"No chart plugin for type: {spec.chart_type}")
        if not plugin.supports_export_image():
            raise RuntimeError(f"Chart type {spec.chart_type} does not support image export")
        plugin.export_image(view, destination)
