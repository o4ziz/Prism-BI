"""Theme application for Prism BI (presentation-only)."""

from __future__ import annotations

from enum import StrEnum
from importlib import resources

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget


class ThemeMode(StrEnum):
    LIGHT = "light"
    DARK = "dark"


_SETTINGS_ORG = "Prism BI"
_SETTINGS_APP = "PrismBI"
_KEY = "ui/theme"


def load_theme_preference() -> ThemeMode:
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    raw = str(settings.value(_KEY, ThemeMode.LIGHT.value))
    return ThemeMode.DARK if raw == ThemeMode.DARK.value else ThemeMode.LIGHT


def save_theme_preference(mode: ThemeMode) -> None:
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    settings.setValue(_KEY, mode.value)


def _build_palette(mode: ThemeMode) -> QPalette:
    """Keep native combo/popup text readable when QSS alone is not enough."""
    palette = QPalette()
    if mode is ThemeMode.DARK:
        window = QColor("#0B1220")
        base = QColor("#111827")
        text = QColor("#E5E7EB")
        disabled = QColor("#6B7280")
        highlight = QColor("#134E4A")
        highlighted = QColor("#F0FDFA")
        button = QColor("#1F2937")
    else:
        window = QColor("#F1F5F9")
        base = QColor("#FFFFFF")
        text = QColor("#0F172A")
        disabled = QColor("#94A3B8")
        highlight = QColor("#CCFBF1")
        highlighted = QColor("#0F766E")
        button = QColor("#FFFFFF")

    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, window)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, button)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.ToolTipBase, base)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, disabled)
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, highlighted)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
    return palette


def _repolish(app: QApplication) -> None:
    style = app.style()
    for widget in app.allWidgets():
        if isinstance(widget, QWidget):
            style.unpolish(widget)
            style.polish(widget)
            widget.update()


def apply_theme(app: QApplication, mode: ThemeMode | None = None) -> ThemeMode:
    """Load and apply the QSS for the given (or preferred) theme."""
    chosen = mode or load_theme_preference()
    name = "app_dark.qss" if chosen is ThemeMode.DARK else "app.qss"
    try:
        root = resources.files("prism_bi.presentation.resources")
        qss = root.joinpath(name).read_text(encoding="utf-8")
        app.setPalette(_build_palette(chosen))
        app.setStyleSheet(qss)
        _repolish(app)
    except (OSError, FileNotFoundError, TypeError, AttributeError):
        pass
    app.setProperty("prismTheme", chosen.value)
    save_theme_preference(chosen)
    return chosen
