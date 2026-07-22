"""Chart plugin contract — partner engine against SDK only."""

from __future__ import annotations

from uuid import uuid4

import pyarrow as pa

from prism_bi_sdk import (
    API_VERSION_MAJOR,
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
)
from prism_bi_sdk.contributions import PluginRegistry
from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData


class _FakeRegistry:
    def __init__(self) -> None:
        self.items: list[ContributionRegistration] = []

    def add(self, registration: ContributionRegistration) -> None:
        self.items.append(registration)


class _FakeChartPlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="partner.chart.fake",
            name="Fake Charts",
            version="0.0.1",
            api_version=API_VERSION_MAJOR,
            entry_module="x",
            entry_class="Y",
        )
        self.views: list[object] = []

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.CHARTS,
                contribution_id="partner.chart.fake",
                factory=self,
            )
        )

    def activate(self, context: object) -> None:
        _ = context

    def deactivate(self) -> None:
        return None

    def chart_types(self) -> tuple[str, ...]:
        return ("bar", "line")

    def create_view(self, spec: ChartSpec, data: ChartData, parent: object) -> object:
        view = {"type": spec.chart_type, "rows": data.batch.num_rows, "parent": parent}
        self.views.append(view)
        return view

    def supports_export_image(self) -> bool:
        return False

    def export_image(self, view: object, destination: str) -> None:
        raise NotImplementedError


def test_fake_chart_plugin_registers_and_renders_without_host() -> None:
    plugin = _FakeChartPlugin()
    registry = _FakeRegistry()
    plugin.register(registry)
    assert registry.items[0].kind == ContributionKind.CHARTS
    batch = pa.record_batch({"category": ["a"], "value": [1.0]})
    data = ChartData(batch=batch, category_column="category", value_columns=("value",))
    spec = ChartSpec(
        id=uuid4(),
        chart_type="bar",
        dataset_id=uuid4(),
        title="t",
        encodings=(),
    )
    view = plugin.create_view(spec, data, parent=None)
    assert view["rows"] == 1
    assert "bar" in plugin.chart_types()
