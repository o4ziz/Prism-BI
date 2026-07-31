"""QtCharts design tokens for the chart engine plugin (host-independent).

Hex values must stay aligned with ``prism_bi.presentation.theme.prism_theme``.
"""

from __future__ import annotations

from PySide6.QtCharts import (
    QAreaSeries,
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLegend,
    QLineSeries,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen

BG = QColor("#0A0A0B")
SURFACE = QColor("#16171A")
ELEVATED = QColor("#1C1D21")
BORDER = QColor("#26272B")
ACCENT = QColor("#F5601A")
ACCENT_LIGHT = QColor("#FF8A3D")
TEXT = QColor("#F5F5F5")
TEXT_MUTED = QColor("#8A8F98")

SERIES_COLORS: tuple[QColor, ...] = (
    QColor("#F5601A"),
    QColor("#FF8A3D"),
    QColor("#C44A12"),
    QColor("#A33D0F"),
    QColor("#FFB27A"),
    QColor("#8A8F98"),
)

# Optional named ramps — still single-hue (orange / charcoal), never rainbow.
THEME_RAMPS: dict[str, tuple[QColor, ...]] = {
    "orange": SERIES_COLORS,
    "accent": SERIES_COLORS,
    "teal": SERIES_COLORS,  # legacy option ids map to orange
    "ocean": SERIES_COLORS,
    "sunset": SERIES_COLORS,
    "mono": (
        QColor("#F5601A"),
        QColor("#8A8F98"),
        QColor("#5C6068"),
        QColor("#3A3D44"),
        QColor("#FF8A3D"),
        QColor("#C44A12"),
    ),
}


def series_colors(name: str | None = None) -> list[QColor]:
    key = (name or "orange").lower()
    return list(THEME_RAMPS.get(key, SERIES_COLORS))


def ui_font(*, point_size: int = 10, bold: bool = False) -> QFont:
    font = QFont("Segoe UI")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPointSize(point_size)
    font.setBold(bold)
    return font


def style_chart_view(view: QChartView) -> None:
    view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    view.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    view.setBackgroundBrush(QBrush(BG))


def style_chart(chart: QChart, *, title: str | None = None, show_legend: bool = True) -> None:
    if title is not None:
        chart.setTitle(title)
    chart.setTitleFont(ui_font(point_size=12, bold=True))
    chart.setTitleBrush(QBrush(TEXT))
    chart.setBackgroundBrush(QBrush(BG))
    chart.setBackgroundRoundness(11)
    chart.setPlotAreaBackgroundVisible(False)
    chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
    legend = chart.legend()
    legend.setVisible(show_legend)
    legend.setAlignment(Qt.AlignmentFlag.AlignBottom)
    legend.setLabelColor(TEXT_MUTED)
    legend.setFont(ui_font(point_size=9))
    legend.setMarkerShape(QLegend.MarkerShape.MarkerShapeRectangle)


def style_category_axis(
    axis: QBarCategoryAxis,
    *,
    show_labels: bool = True,
    label_angle: int = 45,
    title: str = "",
    show_grid: bool = False,
) -> None:
    axis.setLabelsVisible(show_labels)
    axis.setLabelsAngle(-abs(label_angle))
    axis.setTruncateLabels(False)
    axis.setLabelsColor(TEXT_MUTED)
    axis.setLabelsFont(ui_font(point_size=9))
    axis.setGridLineVisible(show_grid)
    axis.setLineVisible(False)
    _style_axis_title(axis, title)


def style_value_axis(
    axis: QValueAxis,
    *,
    title: str = "",
    show_grid: bool = True,
) -> None:
    axis.setLabelsVisible(True)
    axis.setLabelsColor(TEXT_MUTED)
    axis.setLabelsFont(ui_font(point_size=9))
    axis.setGridLineVisible(show_grid)
    axis.setMinorGridLineVisible(False)
    grid = QPen(BORDER)
    grid.setWidthF(0.8)
    axis.setGridLinePen(grid)
    axis.setLineVisible(False)
    _style_axis_title(axis, title)


def _style_axis_title(axis: QBarCategoryAxis | QValueAxis, title: str) -> None:
    text = title.strip()
    if not text:
        axis.setTitleVisible(False)
        return
    axis.setTitleText(text)
    axis.setTitleVisible(True)
    axis.setTitleFont(ui_font(point_size=10, bold=True))
    axis.setTitleBrush(QBrush(TEXT_MUTED))


def style_bar_set(bar_set: QBarSet, color: QColor | None = None) -> None:
    fill = color or ACCENT
    bar_set.setColor(fill)
    bar_set.setBorderColor(Qt.GlobalColor.transparent)
    bar_set.setLabelColor(TEXT)


def style_bar_series(series: QBarSeries) -> None:
    series.setBarWidth(0.72)


def style_line_series(series: QLineSeries, color: QColor | None = None) -> None:
    stroke = color or ACCENT
    series.setColor(stroke)
    pen = QPen(stroke, 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    series.setPen(pen)


def style_area_series(series: QAreaSeries, color: QColor | None = None) -> None:
    stroke = color or ACCENT
    series.setBorderColor(stroke)
    series.setPen(QPen(stroke, 2.0))
    gradient = QLinearGradient(0, 0, 0, 1)
    gradient.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
    top = QColor(stroke.red(), stroke.green(), stroke.blue(), 110)
    bottom = QColor(stroke.red(), stroke.green(), stroke.blue(), 0)
    gradient.setColorAt(0.0, top)
    gradient.setColorAt(1.0, bottom)
    series.setBrush(QBrush(gradient))


def style_scatter_series(series: QScatterSeries, color: QColor | None = None) -> None:
    fill = color or QColor(245, 96, 26, 120)
    series.setColor(fill)
    series.setBorderColor(Qt.GlobalColor.transparent)
    series.setMarkerSize(7.0)
