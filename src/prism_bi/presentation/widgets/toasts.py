"""Non-blocking toast notifications via status-bar style labels."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMainWindow


class ToastHost:
    """Shows transient messages in the main window status area."""

    def __init__(self, window: QMainWindow) -> None:
        self._window = window

    def show_message(self, text: str, *, timeout_ms: int = 4000) -> None:
        status = self._window.statusBar()
        status.showMessage(text, timeout_ms)
        # Also flash a temporary top label for visibility in tests.
        banner = QLabel(text, self._window)
        banner.setObjectName("ToastBanner")
        banner.setStyleSheet("background: #222; color: #fff; padding: 8px; border-radius: 4px;")
        banner.adjustSize()
        banner.move(20, 40)
        banner.show()
        QTimer.singleShot(timeout_ms, banner.deleteLater)
