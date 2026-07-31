"""Reusable chart host widget — binds ChartSpec via ports, not DuckDB."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCharts import QChartView
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from prism_bi.presentation.theme.prism_theme import BG, TEXT_MUTED, style_chart_view
from prism_bi_sdk.dto.chart import ChartSpec

if TYPE_CHECKING:
    from prism_bi.application.ports.chart_data import IChartDataProvider
    from prism_bi.application.visualization.registry import ChartRendererRegistry


class ChartHostWidget(QWidget):
    """Modular widget: query via IChartDataProvider, render via ChartRendererRegistry."""

    def __init__(
        self,
        chart_data: IChartDataProvider,
        chart_renderers: ChartRendererRegistry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._chart_data = chart_data
        self._chart_renderers = chart_renderers
        self._spec: ChartSpec | None = None
        self._view: QWidget | None = None
        self.setObjectName("ChartHostWidget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), BG)
        self.setPalette(palette)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel("No chart loaded")
        self._placeholder.setObjectName("EmptyStateLabel")
        self._placeholder.setStyleSheet(f"color: {TEXT_MUTED.name()}; padding: 8px;")
        self._layout.addWidget(self._placeholder)

    @property
    def current_spec(self) -> ChartSpec | None:
        return self._spec

    @property
    def current_view(self) -> QWidget | None:
        return self._view

    def clear(self) -> None:
        self._spec = None
        if self._view is not None:
            self._layout.removeWidget(self._view)
            self._view.deleteLater()
            self._view = None
        self._placeholder.setText("No chart loaded")
        self._placeholder.show()

    def bind(self, spec: ChartSpec) -> None:
        """Load aggregated data and replace the embedded engine view."""
        data = self._chart_data.query(spec)
        view = self._chart_renderers.create_view(spec, data, self)
        if not isinstance(view, QWidget):
            raise TypeError("Chart plugin must return a QWidget")
        if self._view is not None:
            self._layout.removeWidget(self._view)
            self._view.deleteLater()
        self._placeholder.hide()
        self._view = view
        self._spec = spec
        self._layout.addWidget(view, stretch=1)
        if isinstance(view, QChartView):
            style_chart_view(view)
            view.setBackgroundBrush(QBrush(BG))
            view.setRubberBand(QChartView.RubberBand.RectangleRubberBand)
        if data.truncated:
            tip = "Chart data was truncated to the configured point/category limit."
            self.setToolTip(tip)
            self.setAccessibleDescription(tip)
            self._placeholder.setText("Showing aggregated sample (truncated)")
            self._placeholder.show()
        else:
            self.setToolTip("")
            self.setAccessibleDescription(spec.title or "Chart")

    def zoom(self, factor: float) -> None:
        chart = self._chart()
        if chart is not None:
            chart.zoom(factor)

    def fit_to_view(self) -> None:
        chart = self._chart()
        if chart is not None:
            chart.zoomReset()

    def export_png(self, destination: str) -> None:
        if self._spec is None or self._view is None:
            raise RuntimeError("No chart view to export")
        self._chart_renderers.export_image(self._spec, self._view, destination)

    def _chart(self) -> Any:
        if isinstance(self._view, QChartView):
            return self._view.chart()
        return None
