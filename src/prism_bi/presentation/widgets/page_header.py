"""Page chrome — title row used by every module."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PageHeader(QWidget):
    """Title + subtitle strip for module pages."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("PageTitle")
        layout.addWidget(self._title)
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("PageSubtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setVisible(bool(subtitle))
        layout.addWidget(self._subtitle)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))


class ToolbarRow(QWidget):
    """Horizontal action strip under a page header."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ToolbarRow")
        self.layout_row = QHBoxLayout(self)
        self.layout_row.setContentsMargins(0, 0, 0, 8)
        self.layout_row.setSpacing(8)
