"""Collapsible navigation rail (JetBrains / Azure Data Studio inspired)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from prism_bi.presentation.theme.icons import icon_collapse, icon_expand, module_icon

_EXPANDED_WIDTH = 168
_COLLAPSED_WIDTH = 56


class NavRail(QFrame):
    """Left activity rail with icons + optional labels."""

    module_selected = Signal(str)
    collapse_toggled = Signal(bool)

    def __init__(self, modules: tuple[str, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavRail")
        self._modules = modules
        self._collapsed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 12)
        root.setSpacing(8)

        brand_row = QHBoxLayout()
        self._brand = QLabel("Prism")
        self._brand.setObjectName("NavBrand")
        brand_row.addWidget(self._brand, stretch=1)
        self._toggle = QPushButton()
        self._toggle.setObjectName("NavCollapseButton")
        self._toggle.setIcon(icon_collapse())
        self._toggle.setFixedSize(28, 28)
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.setToolTip("Collapse navigation")
        self._toggle.clicked.connect(self.toggle_collapsed)
        brand_row.addWidget(self._toggle)
        root.addLayout(brand_row)

        self._list = QListWidget()
        self._list.setObjectName("ActivityBar")
        self._list.setSpacing(2)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for name in modules:
            item = QListWidgetItem(module_icon(name), name)
            item.setToolTip(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._list.addItem(item)
        self._list.currentRowChanged.connect(self._on_row_changed)
        root.addWidget(self._list, stretch=1)

        self.setFixedWidth(_EXPANDED_WIDTH)

    def set_current_module(self, name: str) -> None:
        try:
            index = self._modules.index(name)
        except ValueError:
            return
        self._list.blockSignals(True)
        self._list.setCurrentRow(index)
        self._list.blockSignals(False)
        self._refresh_icons(active=name)

    def toggle_collapsed(self) -> None:
        self._collapsed = not self._collapsed
        self.setFixedWidth(_COLLAPSED_WIDTH if self._collapsed else _EXPANDED_WIDTH)
        self._brand.setVisible(not self._collapsed)
        self._toggle.setIcon(icon_expand() if self._collapsed else icon_collapse())
        self._toggle.setToolTip("Expand navigation" if self._collapsed else "Collapse navigation")
        for row in range(self._list.count()):
            item = self._list.item(row)
            assert item is not None
            name = str(item.data(Qt.ItemDataRole.UserRole))
            item.setText("" if self._collapsed else name)
        self.collapse_toggled.emit(self._collapsed)

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self._modules):
            name = self._modules[row]
            self._refresh_icons(active=name)
            self.module_selected.emit(name)

    def _refresh_icons(self, *, active: str) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            assert item is not None
            name = str(item.data(Qt.ItemDataRole.UserRole))
            item.setIcon(module_icon(name, active=(name == active)))
