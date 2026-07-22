"""Lightweight SVG icon factory for the shell (no external assets)."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_COLOR = "#94A3B8"


def _svg_icon(path_d: str, *, color: str = _COLOR, size: int = 20) -> QIcon:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"
 viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.75"
 stroke-linecap="round" stroke-linejoin="round">{path_d}</svg>"""
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def icon_home(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
        color=color,
    )


def icon_data(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<rect x="3" y="4" width="18" height="4" rx="1"/>'
        '<rect x="3" y="10" width="18" height="4" rx="1"/>'
        '<rect x="3" y="16" width="18" height="4" rx="1"/>',
        color=color,
    )


def icon_prepare(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<path d="M4 6h16M4 12h10M4 18h7"/>'
        '<circle cx="18" cy="12" r="2"/><circle cx="15" cy="18" r="2"/>',
        color=color,
    )


def icon_visualize(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<path d="M4 19V5"/><path d="M4 19h16"/>'
        '<path d="M8 16V10"/><path d="M12 16V7"/><path d="M16 16v-5"/>',
        color=color,
    )


def icon_dashboard(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<rect x="3" y="3" width="8" height="8" rx="1"/>'
        '<rect x="13" y="3" width="8" height="5" rx="1"/>'
        '<rect x="13" y="10" width="8" height="11" rx="1"/>'
        '<rect x="3" y="13" width="8" height="8" rx="1"/>',
        color=color,
    )


def icon_reports(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<path d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/>'
        '<path d="M14 3v6h6"/><path d="M8 13h8M8 17h6"/>',
        color=color,
    )


def icon_settings(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4'
        'M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
        color=color,
    )


def icon_help(*, color: str = _COLOR) -> QIcon:
    return _svg_icon(
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1.5 1-1.5 2.2V14"/>'
        '<circle cx="12" cy="17" r="0.6" fill="{color}" stroke="none"/>'.replace("{color}", color),
        color=color,
    )


def icon_collapse(*, color: str = _COLOR) -> QIcon:
    return _svg_icon('<path d="M15 6 9 12l6 6"/>', color=color, size=16)


def icon_expand(*, color: str = _COLOR) -> QIcon:
    return _svg_icon('<path d="M9 6l6 6-6 6"/>', color=color, size=16)


MODULE_ICONS = {
    "Home": icon_home,
    "Data": icon_data,
    "Prepare": icon_prepare,
    "Visualize": icon_visualize,
    "Dashboard": icon_dashboard,
    "Reports": icon_reports,
    "Settings": icon_settings,
    "Help": icon_help,
}


def module_icon(name: str, *, active: bool = False) -> QIcon:
    factory = MODULE_ICONS.get(name, icon_home)
    color = "#14B8A6" if active else _COLOR
    return factory(color=color)


def toolbar_icon_size() -> QSize:
    return QSize(18, 18)
