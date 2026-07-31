"""Central Prism BI design tokens and QtCharts styling helpers.

Presentation owns this module. Chart plugins that cannot import the host
should keep a matching local copy of the chart helpers (same hex tokens).
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

# —— Palette (exactly one accent) ——
BG = QColor("#0A0A0B")
SURFACE = QColor("#16171A")
ELEVATED = QColor("#1C1D21")
BORDER = QColor("#26272B")
ACCENT = QColor("#F5601A")
ACCENT_LIGHT = QColor("#FF8A3D")
TEXT = QColor("#F5F5F5")
TEXT_MUTED = QColor("#8A8F98")
POSITIVE = QColor("#3FCF8E")
NEGATIVE = QColor("#F5603A")

# Single-hue series ramp (orange → charcoal), never rainbow.
SERIES_COLORS: tuple[QColor, ...] = (
    QColor("#F5601A"),
    QColor("#FF8A3D"),
    QColor("#C44A12"),
    QColor("#A33D0F"),
    QColor("#FFB27A"),
    QColor("#8A8F98"),
)

HEATMAP_STOPS: tuple[QColor, ...] = (
    QColor("#16171A"),
    QColor("#F5601A"),
    QColor("#FF8A3D"),
)


def series_color(index: int) -> QColor:
    return SERIES_COLORS[index % len(SERIES_COLORS)]


def heatmap_color(t: float) -> QColor:
    """Interpolate charcoal → orange → pale for t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    if t <= 0.5:
        return _lerp(HEATMAP_STOPS[0], HEATMAP_STOPS[1], t * 2.0)
    return _lerp(HEATMAP_STOPS[1], HEATMAP_STOPS[2], (t - 0.5) * 2.0)


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


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
    view.setStyleSheet(
        f"QChartView {{ background: {BG.name()}; border: 1px solid {BORDER.name()}; "
        f"border-radius: 11px; }}"
    )


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
    # Slightly wider bars / tighter gaps for a denser modern look.
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
    pen = QPen(stroke, 2.0)
    series.setPen(pen)
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
