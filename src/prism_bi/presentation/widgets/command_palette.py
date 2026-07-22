"""Command palette with dynamic workspace index (datasets/columns/dashboards)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class CommandPalette(QDialog):
    """Ctrl+K palette: static commands + live workspace entries."""

    def __init__(
        self,
        parent: QWidget,
        commands: Sequence[tuple[str, Callable[[], None]]],
        *,
        dynamic_provider: Callable[[], Sequence[tuple[str, Callable[[], None]]]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.resize(480, 360)
        self._commands = list(commands)
        self._dynamic_provider = dynamic_provider
        self._entries: list[tuple[str, Callable[[], None]]] = []

        layout = QVBoxLayout(self)
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Search commands, datasets, columns, dashboards…")
        self._filter.textChanged.connect(self._refilter)
        self._list = QListWidget()
        self._list.itemActivated.connect(self._activate)
        layout.addWidget(self._filter)
        layout.addWidget(self._list)

    def open_palette(self) -> None:
        self._rebuild_entries()
        self._filter.clear()
        self._refilter("")
        self._filter.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.exec()

    def _rebuild_entries(self) -> None:
        self._entries = list(self._commands)
        if self._dynamic_provider is not None:
            self._entries.extend(list(self._dynamic_provider()))

    def _refilter(self, text: str) -> None:
        self._list.clear()
        needle = text.strip().lower()
        for label, _callback in self._entries:
            if needle and needle not in label.lower():
                continue
            self._list.addItem(QListWidgetItem(label))

    def _activate(self, item: QListWidgetItem) -> None:
        label = item.text()
        for command_label, callback in self._entries:
            if command_label == label:
                self.accept()
                callback()
                return
