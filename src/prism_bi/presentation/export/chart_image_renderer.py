"""Qt-backed chart → PNG renderer (presentation adapter for IChartImageRenderer)."""

from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QApplication, QWidget

from prism_bi.application.visualization.registry import ChartRendererRegistry
from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData


class QtChartImageRenderer:
    """Renders charts via the active IChartPlugin and grabs PNG bytes."""

    def __init__(self, chart_renderers: ChartRendererRegistry) -> None:
        self._chart_renderers = chart_renderers

    def to_png(self, spec: ChartSpec, data: ChartData) -> bytes:
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication required for chart PNG rendering")
        view = self._chart_renderers.create_view(spec, data, None)
        if not isinstance(view, QWidget):
            raise TypeError("Chart plugin must return a QWidget for PNG export")
        view.resize(960, 540)
        view.show()
        app.processEvents()
        pixmap = view.grab()
        view.hide()
        view.deleteLater()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not pixmap.save(buffer, "PNG"):
            raise RuntimeError("Failed to encode chart PNG")
        raw: QByteArray = buffer.data()
        return bytes(raw.data())
