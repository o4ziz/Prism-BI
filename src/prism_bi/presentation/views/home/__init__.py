"""Home landing dashboard — commercial card layout."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prism_bi.presentation.theme.icons import (
    icon_data,
    icon_help,
    icon_home,
    icon_reports,
    icon_settings,
    icon_visualize,
)
from prism_bi.presentation.widgets.card import ActionCard
from prism_bi.presentation.widgets.page_header import PageHeader

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class HomeView(QWidget):
    """Modern Home with quick actions, recent projects, and status cards."""

    def __init__(
        self,
        container: AppContainer,
        *,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[], None],
        on_open_path: Callable[[Path], None],
        on_import: Callable[[], None],
        on_go_data: Callable[[], None],
        on_go_help: Callable[[], None],
        on_go_settings: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._on_new = on_new_project
        self._on_open = on_open_project
        self._on_open_path = on_open_path
        self._on_import = on_import
        self._on_go_data = on_go_data
        self._on_go_help = on_go_help
        self._on_go_settings = on_go_settings
        self.setObjectName("HomeView")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("HomeView")
        scroll.setWidget(content)
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(24, 20, 24, 24)
        self._layout.setSpacing(16)

        self._header = PageHeader(
            "Home",
            "Welcome to Prism BI — import, prepare, visualize, and share insights.",
        )
        self._layout.addWidget(self._header)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(14)
        self._grid.setVerticalSpacing(14)
        self._layout.addWidget(self._grid_host)
        self._layout.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        project = self._container.workspace.project
        project_line = (
            f"Open project: {project.name}"
            if project is not None
            else "No project open yet — create one or open the sample."
        )
        self._header.set_subtitle(project_line)

        plugins = self._container.plugins.plugin_summaries()
        active = sum(1 for item in plugins if item["active"])
        recent = self._container.workspace.project_store.list_recent(
            self._container.workspace.recent_file
        )
        sample = self._container.repo_root / "samples" / "SalesDemo.prism"

        cards: list[ActionCard] = [
            ActionCard(
                "Create project",
                "Start a new .prism workspace for your analysis.",
                primary_label="New project",
                on_primary=self._on_new,
                icon=icon_home(),
            ),
            ActionCard(
                "Open project",
                "Continue work in an existing Prism project folder.",
                primary_label="Open…",
                on_primary=self._on_open,
                icon=icon_reports(),
            ),
            ActionCard(
                "Import data",
                "Bring in CSV, Excel, JSON, or SQLite — then profile and explore.",
                primary_label="Import…",
                on_primary=self._on_import,
                secondary_label="Go to Data",
                on_secondary=self._on_go_data,
                icon=icon_data(),
            ),
            ActionCard(
                "Sample project",
                "Open Sales Demo with a seeded chart to explore the product quickly.",
                primary_label="Open sample" if sample.is_dir() else None,
                on_primary=(lambda: self._on_open_path(sample)) if sample.is_dir() else None,
                icon=icon_visualize(),
            ),
            ActionCard(
                "Recent projects",
                _recent_body(recent),
                primary_label="Open latest" if recent else None,
                on_primary=(lambda: self._on_open_path(recent[0])) if recent else None,
                secondary_label="Browse…",
                on_secondary=self._on_open,
                icon=icon_reports(),
            ),
            ActionCard(
                "Plugin status",
                f"{len(plugins)} loaded · {active} active. Soft-fail keeps the host stable.",
                primary_label="Settings",
                on_primary=self._on_go_settings,
                icon=icon_settings(),
            ),
            ActionCard(
                "System health",
                f"Logs: {self._container.config.user_data_dir / 'logs'}\n"
                f"User data: {self._container.config.user_data_dir}",
                primary_label="Open Help",
                on_primary=self._on_go_help,
                icon=icon_help(),
            ),
            ActionCard(
                "Keyboard shortcuts",
                "Ctrl+K command palette · Ctrl+S save · File menu for project actions.",
                primary_label="Getting started",
                on_primary=self._on_go_help,
                icon=icon_help(),
            ),
            ActionCard(
                "Quick actions",
                "Jump into the analyst workflow without hunting menus.",
                primary_label="Data",
                on_primary=self._on_go_data,
                secondary_label="Help",
                on_secondary=self._on_go_help,
                icon=icon_data(),
            ),
        ]

        section = QLabel("Workspace")
        section.setObjectName("SectionTitle")
        self._grid.addWidget(section, 0, 0, 1, 3)

        for index, card in enumerate(cards):
            row = 1 + index // 3
            col = index % 3
            self._grid.addWidget(card, row, col)
            card.setMinimumHeight(150)


def _recent_body(recent: list[Path]) -> str:
    if not recent:
        return "No recent projects yet. Create or open a .prism folder to begin."
    return "\n".join(f"• {path.name}" for path in recent[:5])
