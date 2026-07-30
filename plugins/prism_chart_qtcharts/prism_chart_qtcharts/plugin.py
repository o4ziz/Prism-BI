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
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
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

_THEMES: dict[str, list[QColor]] = {
    "teal": [
        QColor("#0D9488"),
        QColor("#14B8A6"),
        QColor("#2DD4BF"),
        QColor("#5EEAD4"),
        QColor("#0991B3"),
        QColor("#0284C7"),
    ],
    "ocean": [
        QColor("#0369A1"),
        QColor("#0284C7"),
        QColor("#0EA5E9"),
        QColor("#38BDF8"),
        QColor("#06B6D4"),
        QColor("#22D3EE"),
    ],
    "sunset": [
        QColor("#EA580C"),
        QColor("#F97316"),
        QColor("#FB923C"),
        QColor("#E11D48"),
        QColor("#F43F5E"),
        QColor("#A855F7"),
    ],
    "mono": [
        QColor("#0F172A"),
        QColor("#334155"),
        QColor("#475569"),
        QColor("#64748B"),
        QColor("#94A3B8"),
        QColor("#CBD5E1"),
    ],
}


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
        view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        view.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
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


def _theme_colors(spec: ChartSpec) -> list[QColor]:
    name = str(_opt(spec, "color_theme", "teal")).lower()
    return list(_THEMES.get(name, _THEMES["teal"]))


def _style_chart(chart: QChart, spec: ChartSpec) -> None:
    chart.setTitle(spec.title or spec.chart_type)
    title_font = QFont()
    title_font.setPointSize(12)
    title_font.setBold(True)
    chart.setTitleFont(title_font)
    chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
    chart.setBackgroundRoundness(8)
    # Leave room for vertical Y title + tick labels and angled X labels + X title.
    left = 56 if str(_opt(spec, "y_axis_title", "") or "").strip() else 36
    bottom = 52 if str(_opt(spec, "x_axis_title", "") or "").strip() else 40
    chart.setMargins(QMargins(left, 20, 20, bottom))
    chart.legend().setVisible(bool(_opt(spec, "show_legend", True)))
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)


def _apply_axis_title(axis: QBarCategoryAxis | QValueAxis, title: str) -> None:
    text = title.strip()
    if not text:
        axis.setTitleVisible(False)
        return
    axis.setTitleText(text)
    axis.setTitleVisible(True)
    title_font = QFont()
    title_font.setPointSize(10)
    title_font.setBold(True)
    axis.setTitleFont(title_font)
    axis.setTitleBrush(QBrush(QColor("#334155")))


def _style_category_axis(axis: QBarCategoryAxis, spec: ChartSpec) -> None:
    show = bool(_opt(spec, "show_labels", True))
    axis.setLabelsVisible(show)
    angle = int(_opt(spec, "label_angle", 45))
    axis.setLabelsAngle(-abs(angle))
    axis.setTruncateLabels(False)
    _apply_axis_title(axis, str(_opt(spec, "x_axis_title", "") or ""))
    font = QFont()
    font.setPointSize(9)
    axis.setLabelsFont(font)


def _style_value_axis(axis: QValueAxis, spec: ChartSpec, *, role: str = "y") -> None:
    show_grid = bool(_opt(spec, "show_grid", True))
    axis.setGridLineVisible(show_grid)
    axis.setMinorGridLineVisible(False)
    axis.setLabelsVisible(True)
    pen = QPen(QColor("#CBD5E1"))
    pen.setWidthF(0.8)
    axis.setGridLinePen(pen)
    title_key = "y_axis_title" if role == "y" else "x_axis_title"
    _apply_axis_title(axis, str(_opt(spec, title_key, "") or ""))
    font = QFont()
    font.setPointSize(9)
    axis.setLabelsFont(font)


def _colorize_bar_set(bar_set: QBarSet, color: QColor) -> None:
    bar_set.setColor(color)
    bar_set.setBorderColor(color.darker(110))


def _build_table(spec: ChartSpec, data: ChartData, parent: Any) -> QWidget:
    host = QWidget(parent)
    layout = QVBoxLayout(host)
    title = QLabel(spec.title or "Table")
    title.setObjectName("PageTitle")
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
    host.setObjectName("PrismChartTable")
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
            _colorize_bar_set(bar_set, colors[index % len(colors)])
        bar_series = QBarSeries()
        for bar_set in series_map.values():
            bar_series.append(bar_set)
        chart.addSeries(bar_series)
        axis_x = QBarCategoryAxis()
        axis_x.append(cat_order)
        _style_category_axis(axis_x, spec)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        axis_y = QValueAxis()
        _style_value_axis(axis_y, spec)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)
        _ensure_value_axis_range(axis_y)
        return

    categories: list[str] = []
    bar_set = QBarSet(data.value_columns[0] if data.value_columns else "value")
    for row in rows:
        categories.append(str(row.get(data.category_column or "category", "")))
        bar_set.append(float(row.get("value") or 0))
    _colorize_bar_set(bar_set, colors[0])
    bar_series = QBarSeries()
    bar_series.append(bar_set)
    chart.addSeries(bar_series)
    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    _style_category_axis(axis_x, spec)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    bar_series.attachAxis(axis_x)
    axis_y = QValueAxis()
    _style_value_axis(axis_y, spec)
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
    series.setColor(colors[0])
    series.setPen(QPen(colors[0], 2.2))
    categories: list[str] = []
    for index, row in enumerate(rows):
        categories.append(str(row.get(data.category_column or "category", "")))
        series.append(float(index), float(row.get("value") or 0))
    chart.addSeries(series)
    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    _style_category_axis(axis_x, spec)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)
    axis_y = QValueAxis()
    _style_value_axis(axis_y, spec)
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
    area.setColor(colors[0])
    area.setBorderColor(colors[0].darker(110))
    brush = QBrush(colors[0])
    brush.setStyle(Qt.BrushStyle.SolidPattern)
    area.setBrush(brush)
    chart.addSeries(area)
    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    _style_category_axis(axis_x, spec)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    area.attachAxis(axis_x)
    axis_y = QValueAxis()
    _style_value_axis(axis_y, spec)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    area.attachAxis(axis_y)


def _add_pie(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    series = QPieSeries()
    colors = _theme_colors(spec)
    for index, row in enumerate(_rows(data)):
        label = str(row.get(data.category_column or "category", ""))
        slice_ = series.append(label, float(row.get("value") or 0))
        slice_.setBrush(colors[index % len(colors)])
        slice_.setLabelVisible(bool(_opt(spec, "show_labels", True)))
    chart.addSeries(series)


def _add_scatter(chart: QChart, data: ChartData, spec: ChartSpec) -> None:
    series = QScatterSeries()
    colors = _theme_colors(spec)
    series.setName("points")
    series.setMarkerSize(10.0)
    series.setColor(colors[0])
    for row in _rows(data):
        series.append(float(row.get("x") or 0), float(row.get("y") or 0))
    chart.addSeries(series)
    axis_x = QValueAxis()
    axis_y = QValueAxis()
    _style_value_axis(axis_x, spec, role="x")
    _style_value_axis(axis_y, spec, role="y")
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)
