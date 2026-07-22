"""Reusable card widget for Home and empty states."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ActionCard(QFrame):
    """Notion-inspired action / info card."""

    def __init__(
        self,
        title: str,
        body: str,
        *,
        primary_label: str | None = None,
        on_primary: Callable[[], None] | None = None,
        secondary_label: str | None = None,
        on_secondary: Callable[[], None] | None = None,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        if icon is not None:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(22, 22))
            header.addWidget(icon_label)
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        header.addWidget(title_label, stretch=1)
        layout.addLayout(header)

        body_label = QLabel(body)
        body_label.setObjectName("CardBody")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)

        if primary_label or secondary_label:
            actions = QHBoxLayout()
            actions.setSpacing(8)
            if primary_label and on_primary is not None:
                btn = QPushButton(primary_label)
                btn.setObjectName("PrimaryButton")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(on_primary)
                actions.addWidget(btn)
            if secondary_label and on_secondary is not None:
                btn2 = QPushButton(secondary_label)
                btn2.setObjectName("GhostButton")
                btn2.setCursor(Qt.CursorShape.PointingHandCursor)
                btn2.clicked.connect(on_secondary)
                actions.addWidget(btn2)
            actions.addStretch(1)
            layout.addLayout(actions)
