"""QtCharts-backed chart renderer — depends only on prism_bi_sdk + PySide6."""

from __future__ import annotations

from typing import Any

from PySide6.QtCharts import (
    QAreaSeries,
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.dto.chart import ChartSpec
from prism_bi_sdk.dto.chart_data import ChartData

_SUPPORTED = ("bar", "line", "area", "pie", "scatter", "histogram", "table")


class QtChartsPlugin:
    """Single contribution providing all V1 chart types via QtCharts."""

    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.chart.qtcharts",
            name="QtCharts Chart Engine",
            version="1.0.0",
            api_version=1,
            entry_module="prism_chart_qtcharts.plugin",
            entry_class="QtChartsPlugin",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.CHARTS,
                contribution_id="prism.chart.qtcharts",
                factory=self,
                display_name="QtCharts",
                metadata={"engine": "qtcharts", "types": list(_SUPPORTED)},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context

    def deactivate(self) -> None:
        self._context = None

    def chart_types(self) -> tuple[str, ...]:
        return _SUPPORTED

    def supports_export_image(self) -> bool:
        return True

    def create_view(self, spec: ChartSpec, data: ChartData, parent: Any) -> Any:
        if spec.chart_type == "table":
            return _build_table(spec, data, parent)
        chart = _build_chart(spec, data)
        view = QChartView(chart, parent)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setObjectName("PrismChartView")
        return view

    def export_image(self, view: Any, destination: str) -> None:
        if isinstance(view, QChartView):
            pixmap = view.grab()
            if not pixmap.save(destination, "PNG"):
                raise RuntimeError(f"Failed to write PNG: {destination}")
            return
        if isinstance(view, QWidget):
            pixmap = view.grab()
            if not pixmap.save(destination, "PNG"):
                raise RuntimeError(f"Failed to write PNG: {destination}")
            return
        raise TypeError(f"Unsupported view for export: {type(view)!r}")


def _build_table(spec: ChartSpec, data: ChartData, parent: Any) -> QWidget:
    host = QWidget(parent)
    layout = QVBoxLayout(host)
    title = QLabel(spec.title or "Table")
    layout.addWidget(title)
    table = QTableWidget(host)
    batch = data.batch
    table.setColumnCount(batch.num_columns)
    table.setHorizontalHeaderLabels(list(batch.schema.names))
    table.setRowCount(batch.num_rows)
    for row in range(batch.num_rows):
        for col in range(batch.num_columns):
            value = batch.column(col)[row].as_py()
            table.setItem(row, col, QTableWidgetItem("" if value is None else str(value)))
    layout.addWidget(table)
    host.setObjectName("PrismChartTable")
    return host


def _build_chart(spec: ChartSpec, data: ChartData) -> QChart:
    chart = QChart()
    chart.setTitle(spec.title or spec.chart_type)
    chart.legend().setVisible(True)

    chart_type = spec.chart_type
    if chart_type in {"bar", "histogram"}:
        _add_bar(chart, data)
    elif chart_type == "line":
        _add_line(chart, data)
    elif chart_type == "area":
        _add_area(chart, data)
    elif chart_type == "pie":
        _add_pie(chart, data)
    elif chart_type == "scatter":
        _add_scatter(chart, data)
    else:
        chart.setTitle(f"Unsupported type: {chart_type}")
    return chart


def _rows(data: ChartData) -> list[dict[str, Any]]:
    batch = data.batch
    names = list(batch.schema.names)
    rows: list[dict[str, Any]] = []
    for i in range(batch.num_rows):
        rows.append({name: batch.column(name)[i].as_py() for name in names})
    return rows


def _add_bar(chart: QChart, data: ChartData) -> None:
    rows = _rows(data)
    categories: list[str] = []
    if "series" in (data.batch.schema.names if data.batch.num_columns else []):
        # Grouped bars by series
        series_map: dict[str, QBarSet] = {}
        cat_order: list[str] = []
        for row in rows:
            cat = str(row.get("category", ""))
            if cat not in cat_order:
                cat_order.append(cat)
            series_name = str(row.get("series", "value"))
            if series_name not in series_map:
                series_map[series_name] = QBarSet(series_name)
        for series_name, bar_set in series_map.items():
            values = []
            for cat in cat_order:
                match = next(
                    (
                        r
                        for r in rows
                        if str(r.get("category", "")) == cat
                        and str(r.get("series", "value")) == series_name
                    ),
                    None,
                )
                values.append(float(match.get("value") or 0) if match else 0.0)
            for value in values:
                bar_set.append(value)
        bar_series = QBarSeries()
        for bar_set in series_map.values():
            bar_series.append(bar_set)
        chart.addSeries(bar_series)
        axis_x = QBarCategoryAxis()
        axis_x.append(cat_order)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)
        return

    bar_set = QBarSet(data.value_columns[0] if data.value_columns else "value")
    for row in rows:
        categories.append(str(row.get(data.category_column or "category", "")))
        bar_set.append(float(row.get("value") or 0))
    bar_series = QBarSeries()
    bar_series.append(bar_set)
    chart.addSeries(bar_series)
    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    bar_series.attachAxis(axis_x)
    axis_y = QValueAxis()
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    bar_series.attachAxis(axis_y)


def _add_line(chart: QChart, data: ChartData) -> None:
    rows = _rows(data)
    series = QLineSeries()
    series.setName(data.value_columns[0] if data.value_columns else "value")
    categories: list[str] = []
    for index, row in enumerate(rows):
        categories.append(str(row.get(data.category_column or "category", "")))
        series.append(float(index), float(row.get("value") or 0))
    chart.addSeries(series)
    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)
    axis_y = QValueAxis()
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)


def _add_area(chart: QChart, data: ChartData) -> None:
    rows = _rows(data)
    upper = QLineSeries()
    lower = QLineSeries()
    categories: list[str] = []
    for index, row in enumerate(rows):
        categories.append(str(row.get(data.category_column or "category", "")))
        upper.append(float(index), float(row.get("value") or 0))
        lower.append(float(index), 0.0)
    area = QAreaSeries(upper, lower)
    area.setName(data.value_columns[0] if data.value_columns else "value")
    chart.addSeries(area)
    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    area.attachAxis(axis_x)
    axis_y = QValueAxis()
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    area.attachAxis(axis_y)


def _add_pie(chart: QChart, data: ChartData) -> None:
    series = QPieSeries()
    for row in _rows(data):
        label = str(row.get(data.category_column or "category", ""))
        series.append(label, float(row.get("value") or 0))
    chart.addSeries(series)


def _add_scatter(chart: QChart, data: ChartData) -> None:
    series = QScatterSeries()
    series.setName("points")
    series.setMarkerSize(8.0)
    for row in _rows(data):
        series.append(float(row.get("x") or 0), float(row.get("y") or 0))
    chart.addSeries(series)
    axis_x = QValueAxis()
    axis_y = QValueAxis()
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)
