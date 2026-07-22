"""Settings module — presentation-only preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from prism_bi.presentation.theme import ThemeMode, apply_theme, load_theme_preference
from prism_bi.presentation.widgets.page_header import PageHeader

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class SettingsView(QWidget):
    """User preferences that do not require new use cases."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("ModulePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(
            PageHeader(
                "Settings",
                "Appearance and local paths. Project data stays in your .prism folders.",
            )
        )

        panel = QFrame()
        panel.setObjectName("ContentPanel")
        form = QFormLayout(panel)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self._theme = QComboBox()
        self._theme.addItem("Light", ThemeMode.LIGHT.value)
        self._theme.addItem("Dark", ThemeMode.DARK.value)
        current = load_theme_preference()
        self._theme.setCurrentIndex(0 if current is ThemeMode.LIGHT else 1)
        self._theme.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("Theme", self._theme)

        form.addRow("App data", QLabel(str(container.config.user_data_dir)))
        form.addRow("Logs", QLabel(str(container.config.user_data_dir / "logs")))
        form.addRow(
            "Settings file",
            QLabel(str(container.config.user_data_dir / "settings.toml")),
        )
        layout.addWidget(panel)
        layout.addStretch(1)

    def _on_theme_changed(self, _index: int) -> None:
        from PySide6.QtWidgets import QApplication

        value = self._theme.currentData()
        mode = ThemeMode.DARK if value == ThemeMode.DARK.value else ThemeMode.LIGHT
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, mode)  # type: ignore[arg-type]
