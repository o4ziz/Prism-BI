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
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QBrush
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
from prism_chart_qtcharts.prism_theme import (
    ACCENT,
    BG,
    BORDER,
    SERIES_COLORS,
    TEXT,
    TEXT_MUTED,
    series_colors,
    style_area_series,
    style_bar_series,
    style_bar_set,
    style_category_axis,
    style_chart,
    style_chart_view,
    style_line_series,
    style_scatter_series,
    style_value_axis,
    ui_font,
)

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
        style_chart_view(view)
        view.setObjectName("PrismChartView")
        view.setMinimumSize(320, 240)
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


def _opt(spec: ChartSpec, key: str, default: Any) -> Any:
    return (spec.options or {}).get(key, default)


def _theme_colors(spec: ChartSpec) -> list:
    return series_colors(str(_opt(spec, "color_theme", "orange")))


def _style_chart(chart: QChart, spec: ChartSpec) -> None:
    style_chart(
        chart,
        title=spec.title or spec.chart_type,
        show_legend=bool(_opt(spec, "show_legend", True)),
    )
    left = 56 if str(_opt(spec, "y_axis_title", "") or "").strip() else 36
    bottom = 52 if str(_opt(spec, "x_axis_title", "") or "").strip() else 40
    chart.setMargins(QMargins(left, 20, 20, bottom))


def _cat_axis(spec: ChartSpec) -> QBarCategoryAxis:
    axis = QBarCategoryAxis()
    style_category_axis(
        axis,
        show_labels=bool(_opt(spec, "show_labels", True)),
        label_angle=int(_opt(spec, "label_angle", 45)),
        title=str(_opt(spec, "x_axis_title", "") or ""),
        show_grid=False,
    )
    return axis


def _val_axis(spec: ChartSpec, *, role: str = "y") -> QValueAxis:
    axis = QValueAxis()
    title_key = "y_axis_title" if role == "y" else "x_axis_title"
    style_value_axis(
        axis,
        title=str(_opt(spec, title_key, "") or ""),
        show_grid=bool(_opt(spec, "show_grid", True)),
    )
    return axis


def _build_table(spec: ChartSpec, data: ChartData, parent: Any) -> QWidget:
    host = QWidget(parent)
    host.setObjectName("PrismChartTable")
    host.setStyleSheet(
        f"QWidget#PrismChartTable {{ background: {BG.name()}; }}"
        f"QLabel {{ color: {TEXT.name()}; font-weight: 700; font-size: 14px; }}"
        f"QTableWidget {{ background: {BG.name()}; color: {TEXT.name()}; "
        f"gridline-color: {BORDER.name()}; border: 1px solid {BORDER.name()}; "
        f"border-radius: 11px; }}"
    )
    layout = QVBoxLayout(host)
    title = QLabel(spec.title or "Table")
    title.setObjectName("PageTitle")
    title.setFont(ui_font(point_size=12, bold=True))
    layout.addWidget(title)
    table = QTableWidget(host)
    table.setObjectName("DataGrid")
    table.setAlternatingRowColors(True)
    batch = data.batch
    table.setColumnCount(batch.num_columns)
    table.setHorizontalHeaderLabels(list(batch.schema.names))
    table.setRowCount(batch.num_rows)
    for row in range(batch.num_rows):
        for col in range(batch.num_columns):
            value = batch.column(col)[row].as_py()
            table.setItem(row, col, QTableWidgetItem("" if value is None else str(value)))
    layout.addWidget(table)
    return host


def _build_chart(spec: ChartSpec, data: ChartData) -> QChart:
    chart = QChart()
    _style_chart(chart, spec)
    chart_type = spec.chart_type
    if chart_type in {"bar", "histogram"}:
        _add_bar(chart, data, spec)
    elif chart_type == "line":
        _add_line(chart, data, spec)
    elif chart_type == "area":
        _add_area(chart, data, spec)
    elif chart_type == "pie":
        _add_pie(chart, data, spec)
    elif chart_type == "scatter":
        _add_scatter(chart, data, spec)
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


def _add_bar(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    rows = _rows(data)
    colors = _theme_colors(spec)
    if "series" in (data.batch.schema.names if data.batch.num_columns else []):
        series_map: dict[str, QBarSet] = {}
        cat_order: list[str] = []
        for row in rows:
            cat = str(row.get("category", ""))
            if cat not in cat_order:
                cat_order.append(cat)
            series_name = str(row.get("series", "value"))
            if series_name not in series_map:
                series_map[series_name] = QBarSet(series_name)
        for index, (series_name, bar_set) in enumerate(series_map.items()):
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
            style_bar_set(bar_set, colors[index % len(colors)])
        bar_series = QBarSeries()
        style_bar_series(bar_series)
        for bar_set in series_map.values():
            bar_series.append(bar_set)
        chart.addSeries(bar_series)
        axis_x = _cat_axis(spec)
        axis_x.append(cat_order)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        axis_y = _val_axis(spec)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)
        _ensure_value_axis_range(axis_y)
        return

    categories: list[str] = []
    bar_set = QBarSet(data.value_columns[0] if data.value_columns else "value")
    for row in rows:
        categories.append(str(row.get(data.category_column or "category", "")))
        bar_set.append(float(row.get("value") or 0))
    style_bar_set(bar_set, colors[0] if colors else ACCENT)
    bar_series = QBarSeries()
    style_bar_series(bar_series)
    bar_series.append(bar_set)
    chart.addSeries(bar_series)
    axis_x = _cat_axis(spec)
    axis_x.append(categories)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    bar_series.attachAxis(axis_x)
    axis_y = _val_axis(spec)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    bar_series.attachAxis(axis_y)
    _ensure_value_axis_range(axis_y)


def _ensure_value_axis_range(axis: QValueAxis) -> None:
    """Keep tick labels and Y title visible even when all values are zero."""
    if axis.max() <= axis.min():
        axis.setRange(0.0, 1.0)


def _add_line(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    rows = _rows(data)
    colors = _theme_colors(spec)
    series = QLineSeries()
    series.setName(data.value_columns[0] if data.value_columns else "value")
    style_line_series(series, colors[0] if colors else ACCENT)
    categories: list[str] = []
    for index, row in enumerate(rows):
        categories.append(str(row.get(data.category_column or "category", "")))
        series.append(float(index), float(row.get("value") or 0))
    chart.addSeries(series)
    axis_x = _cat_axis(spec)
    axis_x.append(categories)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)
    axis_y = _val_axis(spec)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)


def _add_area(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    rows = _rows(data)
    colors = _theme_colors(spec)
    upper = QLineSeries()
    lower = QLineSeries()
    categories: list[str] = []
    for index, row in enumerate(rows):
        categories.append(str(row.get(data.category_column or "category", "")))
        upper.append(float(index), float(row.get("value") or 0))
        lower.append(float(index), 0.0)
    area = QAreaSeries(upper, lower)
    area.setName(data.value_columns[0] if data.value_columns else "value")
    style_area_series(area, colors[0] if colors else ACCENT)
    chart.addSeries(area)
    axis_x = _cat_axis(spec)
    axis_x.append(categories)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    area.attachAxis(axis_x)
    axis_y = _val_axis(spec)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    area.attachAxis(axis_y)


def _add_pie(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    series = QPieSeries()
    colors = _theme_colors(spec) or list(SERIES_COLORS)
    for index, row in enumerate(_rows(data)):
        label = str(row.get(data.category_column or "category", ""))
        slice_ = series.append(label, float(row.get("value") or 0))
        slice_.setBrush(QBrush(colors[index % len(colors)]))
        slice_.setBorderColor(BG)
        slice_.setLabelColor(TEXT_MUTED)
        slice_.setLabelVisible(bool(_opt(spec, "show_labels", True)))
    chart.addSeries(series)


def _add_scatter(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    series = QScatterSeries()
    series.setName("points")
    style_scatter_series(series)
    for row in _rows(data):
        series.append(float(row.get("x") or 0), float(row.get("y") or 0))
    chart.addSeries(series)
    axis_x = _val_axis(spec, role="x")
    axis_y = _val_axis(spec, role="y")
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)
