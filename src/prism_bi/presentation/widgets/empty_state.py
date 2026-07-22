"""Shared empty / status UI helpers."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def make_empty_state(text: str, *, object_name: str = "EmptyStateLabel") -> QLabel:
    """Create a consistent empty-state label (backward compatible)."""
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(True)
    label.setAccessibleName(text)
    return label


class EmptyStatePanel(QWidget):
    """Illustrated empty state with primary CTA."""

    def __init__(
        self,
        title: str,
        body: str,
        *,
        primary_label: str | None = None,
        on_primary: Callable[[], None] | None = None,
        secondary_label: str | None = None,
        on_secondary: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyStatePanel")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        glyph = QLabel("◇")
        glyph.setObjectName("EmptyStateGlyph")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(glyph)

        title_label = QLabel(title)
        title_label.setObjectName("EmptyStateTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setObjectName("EmptyStateLabel")
        body_label.setWordWrap(True)
        body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body_label.setMaximumWidth(420)
        layout.addWidget(body_label, alignment=Qt.AlignmentFlag.AlignCenter)

        if primary_label and on_primary is not None:
            btn = QPushButton(primary_label)
            btn.setObjectName("PrimaryButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(on_primary)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        if secondary_label and on_secondary is not None:
            btn2 = QPushButton(secondary_label)
            btn2.setObjectName("GhostButton")
            btn2.setCursor(Qt.CursorShape.PointingHandCursor)
            btn2.clicked.connect(on_secondary)
            layout.addWidget(btn2, alignment=Qt.AlignmentFlag.AlignCenter)
