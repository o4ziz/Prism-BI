"""Collapsible property section for designers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QFrame):
    """Expandable titled section used in property editors."""

    def __init__(self, title: str, *, expanded: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CollapsibleSection")
        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(8, 4, 8, 10)
        self._body_layout.setSpacing(8)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toggle = QToolButton()
        self._toggle.setObjectName("SectionToggle")
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(expanded)
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self._toggle.toggled.connect(self._on_toggled)
        root.addWidget(self._toggle)
        root.addWidget(self._body)
        self._body.setVisible(expanded)

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def add_widget(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def _on_toggled(self, checked: bool) -> None:
        self._body.setVisible(checked)
        self._toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
