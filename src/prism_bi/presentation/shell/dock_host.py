"""Dock host abstraction (QDockWidget now; ADS-replaceable later)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget


@runtime_checkable
class IDockHost(Protocol):
    """Abstraction over docking so ADS can replace Qt docks later."""

    def add_dock(
        self,
        widget: QWidget,
        *,
        title: str,
        area: Qt.DockWidgetArea,
        object_name: str,
    ) -> None:
        """Add a docked panel."""


class QtDockHost:
    """Default dock host using ``QDockWidget``."""

    def __init__(self, window: QMainWindow) -> None:
        self._window = window

    def add_dock(
        self,
        widget: QWidget,
        *,
        title: str,
        area: Qt.DockWidgetArea,
        object_name: str,
    ) -> None:
        dock = QDockWidget(title, self._window)
        dock.setObjectName(object_name)
        dock.setWidget(widget)
        self._window.addDockWidget(area, dock)
