"""Help module — in-app guidance."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout, QWidget

from prism_bi import __version__
from prism_bi.presentation.widgets.page_header import PageHeader

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class HelpView(QWidget):
    """Getting started, shortcuts, and support pointers."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("ModulePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(PageHeader("Help", f"Prism BI {__version__}"))

        panel = QFrame()
        panel.setObjectName("ContentPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(
            "<h3>Getting started</h3>"
            "<ol>"
            "<li>File → Open Project and choose "
            "<b>samples/SalesDemo.prism</b>, or create a new project.</li>"
            "<li>Data → Import CSV, Excel, JSON, or SQLite files.</li>"
            "<li>Prepare to clean; Visualize and Dashboard for charts.</li>"
            "<li>Reports and Export for CSV, Excel, JSON, PNG, and PDF.</li>"
            "</ol>"
            "<h3>Keyboard</h3>"
            "<ul>"
            "<li><b>Ctrl+K</b> — Command palette</li>"
            "<li><b>Ctrl+S</b> — Save project</li>"
            "</ul>"
            "<h3>Support</h3>"
            "<p>Logs live under your user data folder (see Settings). "
            "Include Help → About version details when reporting issues.</p>"
        )
        panel_layout.addWidget(browser)
        layout.addWidget(panel, stretch=1)

        tip = QLabel("Tip: collapse the left rail to maximize canvas space.")
        tip.setObjectName("PageSubtitle")
        layout.addWidget(tip)
