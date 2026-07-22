"""Main application window — commercial shell chrome."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from prism_bi import __version__
from prism_bi.application.jobs import demo_sleep_worker
from prism_bi.application.use_cases.project_lifecycle import (
    create_project,
    open_project,
    save_project,
)
from prism_bi.presentation.shell.dock_host import QtDockHost
from prism_bi.presentation.theme import ThemeMode, apply_theme, load_theme_preference
from prism_bi.presentation.views.dashboard import DashboardView
from prism_bi.presentation.views.data_workspace import DataWorkspaceView
from prism_bi.presentation.views.help import HelpView
from prism_bi.presentation.views.home import HomeView
from prism_bi.presentation.views.prepare import PrepareView
from prism_bi.presentation.views.reports import ReportsView
from prism_bi.presentation.views.settings import SettingsView
from prism_bi.presentation.views.visualize import VisualizeView
from prism_bi.presentation.widgets.command_palette import CommandPalette
from prism_bi.presentation.widgets.job_center import JobCenterWidget
from prism_bi.presentation.widgets.nav_rail import NavRail
from prism_bi.presentation.widgets.toasts import ToastHost
from prism_bi_sdk.dto.job import JobHandle, JobState

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer

_MODULES = (
    "Home",
    "Data",
    "Prepare",
    "Visualize",
    "Dashboard",
    "Reports",
    "Settings",
    "Help",
)


class MainWindow(QMainWindow):
    """Shell with nav rail, stacked modules, docks, and jobs."""

    job_state_changed = Signal(object)

    def __init__(self, container: AppContainer) -> None:
        super().__init__()
        self._container = container
        self.setWindowTitle(f"{container.config.app_name}")
        self.resize(1360, 860)
        self.setObjectName("PrismMainWindow")

        self._toast_host = ToastHost(self)
        self._job_center = JobCenterWidget()
        self._job_center.cancel_requested.connect(self._cancel_job)
        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}

        self._build_shell()
        self._command_palette = CommandPalette(
            self,
            commands=self._palette_commands(),
            dynamic_provider=self._palette_workspace_entries,
        )
        self._build_menus()
        self._build_toolbar()
        self._build_docks()
        self._build_status()

        self.job_state_changed.connect(self._on_job_state)
        container.jobs.set_on_state_change(self._bridge_job_state)
        self._show_module("Home")
        self._update_project_status()

    def _build_shell(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._nav = NavRail(_MODULES)
        self._nav.module_selected.connect(self._show_module)
        layout.addWidget(self._nav)

        workspace = QWidget()
        workspace.setObjectName("ModulePage")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self._stack, stretch=1)
        layout.addWidget(workspace, stretch=1)

        for name in _MODULES:
            page = self._make_module_page(name)
            self._pages[name] = page
            self._stack.addWidget(page)

        self.setCentralWidget(central)
        self._nav.set_current_module("Home")

    def _make_module_page(self, name: str) -> QWidget:
        if name == "Home":
            self._home_view = HomeView(
                self._container,
                on_new_project=self._new_project,
                on_open_project=self._open_project,
                on_open_path=self._open_project_path,
                on_import=self._home_import,
                on_go_data=self._go_data,
                on_go_help=self._go_help,
                on_go_settings=self._go_settings,
            )
            return self._home_view
        if name == "Data":
            self._data_view = DataWorkspaceView(self._container)
            return self._wrap_module(self._data_view)
        if name == "Prepare":
            self._prepare_view = PrepareView(self._container)
            return self._wrap_module(self._prepare_view)
        if name == "Visualize":
            self._visualize_view = VisualizeView(self._container)
            return self._wrap_module(self._visualize_view)
        if name == "Dashboard":
            self._dashboard_view = DashboardView(self._container)
            return self._wrap_module(self._dashboard_view)
        if name == "Reports":
            self._reports_view = ReportsView(self._container)
            return self._wrap_module(self._reports_view)
        if name == "Settings":
            self._settings_view = SettingsView(self._container)
            return self._settings_view
        if name == "Help":
            self._help_view = HelpView(self._container)
            return self._help_view
        return QWidget()

    def _wrap_module(self, view: QWidget) -> QWidget:
        """Add consistent outer padding without changing module internals deeply."""
        host = QWidget()
        host.setObjectName("ModulePage")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.addWidget(view)
        return host

    def _home_import(self) -> None:
        self._go_data()
        if hasattr(self, "_data_view"):
            self._data_view._import_file()  # noqa: SLF001

    def _bridge_job_state(self, handle: JobHandle) -> None:
        self.job_state_changed.emit(handle)

    @Slot(object)
    def _on_job_state(self, handle: object) -> None:
        assert isinstance(handle, JobHandle)
        self._job_center.update_job(handle)
        if handle.state == JobState.RUNNING and handle.progress_message:
            self.statusBar().showMessage(
                f"{handle.name}: {handle.progress_percent:.0f}% {handle.progress_message}",
                2000,
            )
        if handle.state == JobState.COMPLETED:
            self._toast_host.show_message(f"Job completed: {handle.name}")
            self.statusBar().showMessage(f"Completed: {handle.name}", 5000)
            self._refresh_workspace_views()
        elif handle.state == JobState.FAILED:
            detail = handle.error or "Unknown error"
            self._toast_host.show_message(f"Job failed: {handle.name}")
            self.statusBar().showMessage(f"Failed: {handle.name} — {detail}", 8000)
        elif handle.state == JobState.CANCELLED:
            self._toast_host.show_message(f"Job cancelled: {handle.name}")

    def _cancel_job(self, job_id: object) -> None:
        from uuid import UUID

        if isinstance(job_id, UUID):
            self._container.jobs.cancel(job_id)
            self.statusBar().showMessage("Cancel requested…", 3000)

    def _refresh_workspace_views(self) -> None:
        if hasattr(self, "_home_view"):
            self._home_view.refresh()
        if hasattr(self, "_data_view"):
            self._data_view.refresh()
        if hasattr(self, "_prepare_view"):
            self._prepare_view.refresh()
        if hasattr(self, "_visualize_view"):
            self._visualize_view.refresh()
        if hasattr(self, "_dashboard_view"):
            self._dashboard_view.refresh()
        if hasattr(self, "_reports_view"):
            self._reports_view.refresh()
        self._update_project_status()

    def _show_module(self, name: str) -> None:
        if name not in self._pages:
            return
        self._stack.setCurrentWidget(self._pages[name])
        self._nav.set_current_module(name)
        self.statusBar().showMessage(name)
        self._update_project_status()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_action = QAction("&New Project…", self)
        new_action.triggered.connect(self._new_project)
        open_action = QAction("&Open Project…", self)
        open_action.triggered.connect(self._open_project)
        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        quit_action = QAction("E&xit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("&View")
        palette_action = QAction("Command Palette…", self)
        palette_action.setShortcut(QKeySequence("Ctrl+K"))
        palette_action.triggered.connect(self._command_palette.open_palette)
        view_menu.addAction(palette_action)
        toggle_nav = QAction("Toggle &Navigation", self)
        toggle_nav.triggered.connect(self._nav.toggle_collapsed)
        view_menu.addAction(toggle_nav)
        view_menu.addSeparator()
        light = QAction("Light Theme", self)
        light.triggered.connect(lambda: self._set_theme(ThemeMode.LIGHT))
        dark = QAction("Dark Theme", self)
        dark.triggered.connect(lambda: self._set_theme(ThemeMode.DARK))
        view_menu.addAction(light)
        view_menu.addAction(dark)

        jobs_menu = self.menuBar().addMenu("&Jobs")
        demo_action = QAction("Run Responsiveness Check", self)
        demo_action.setObjectName("ActionRunDemoJob")
        demo_action.triggered.connect(self._run_demo_job)
        jobs_menu.addAction(demo_action)
        show_tasks = QAction("Show &Task Center", self)
        show_tasks.triggered.connect(self._show_task_center)
        jobs_menu.addAction(show_tasks)

        help_menu = self.menuBar().addMenu("&Help")
        getting_started = QAction("&Getting Started", self)
        getting_started.triggered.connect(self._go_help)
        about_action = QAction("&About Prism BI", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(getting_started)
        help_menu.addAction(about_action)

    def _set_theme(self, mode: ThemeMode) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, mode)
            self._toast_host.show_message(f"Theme: {mode.value}")

    def _new_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Create project in folder")
        if not directory:
            return
        parent = Path(directory)
        name = parent.name or "Prism Project"
        root = parent / f"{name}.prism"
        if root.exists():
            QMessageBox.warning(self, "New Project", f"Already exists: {root}")
            return
        result = create_project(self._container.workspace, root, name)
        if not result.success:
            QMessageBox.critical(self, "New Project", result.message or "Failed")
            return
        self._toast_host.show_message(f"Created project: {name}")
        self._refresh_workspace_views()

    def _open_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Open Prism project folder")
        if not directory:
            return
        self._open_project_path(Path(directory))

    def _open_project_path(self, path: Path) -> None:
        result = open_project(self._container.workspace, path)
        if not result.success:
            QMessageBox.critical(self, "Open Project", result.message or "Failed")
            return
        self._toast_host.show_message("Project opened")
        self._refresh_workspace_views()
        self._go_data()

    def _save_project(self) -> None:
        result = save_project(self._container.workspace)
        if not result.success:
            QMessageBox.critical(self, "Save Project", result.message or "Failed")
            return
        self._toast_host.show_message("Project saved")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setObjectName("MainToolBar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_action = QAction("New", self)
        new_action.setToolTip("New project")
        new_action.triggered.connect(self._new_project)
        open_action = QAction("Open", self)
        open_action.setToolTip("Open project")
        open_action.triggered.connect(self._open_project)
        save_action = QAction("Save", self)
        save_action.setToolTip("Save project")
        save_action.triggered.connect(self._save_project)
        import_action = QAction("Import", self)
        import_action.setToolTip("Import data")
        import_action.triggered.connect(self._home_import)
        palette_action = QAction("Search", self)
        palette_action.setToolTip("Command palette (Ctrl+K)")
        palette_action.triggered.connect(self._command_palette.open_palette)

        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addSeparator()
        toolbar.addAction(import_action)
        toolbar.addAction(palette_action)

    def _build_docks(self) -> None:
        host = QtDockHost(self)
        host.add_dock(
            self._job_center,
            title="Task Center",
            area=Qt.DockWidgetArea.BottomDockWidgetArea,
            object_name="TaskCenterDock",
        )
        log_panel = QLabel(
            "Application logs are written to your user data directory.\n"
            "Open Settings for the exact path, or Help → About."
        )
        log_panel.setWordWrap(True)
        log_panel.setObjectName("LogsPanel")
        log_panel.setContentsMargins(12, 12, 12, 12)
        host.add_dock(
            log_panel,
            title="Logs",
            area=Qt.DockWidgetArea.BottomDockWidgetArea,
            object_name="LogsDock",
        )
        # Keep canvas dominant — docks available on demand (JetBrains-style).
        for name in ("TaskCenterDock", "LogsDock"):
            dock = self.findChild(QDockWidget, name)
            if dock is not None:
                dock.hide()

    def _build_status(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_project = QLabel("No project")
        self._status_project.setObjectName("StatusProject")
        status.addPermanentWidget(self._status_project)
        status.showMessage("Ready")

    def _update_project_status(self) -> None:
        project = self._container.workspace.project
        if project is None:
            self._status_project.setText("No project")
        else:
            self._status_project.setText(f"● {project.name}")

    def _palette_commands(self) -> list[tuple[str, Callable[[], None]]]:
        return [
            ("Go to Home", self._go_home),
            ("Go to Data", self._go_data),
            ("Go to Prepare", self._go_prepare),
            ("Go to Visualize", self._go_visualize),
            ("Go to Dashboard", self._go_dashboard),
            ("Go to Reports", self._go_reports),
            ("Go to Settings", self._go_settings),
            ("Go to Help", self._go_help),
            ("New Project", self._new_project),
            ("Open Project", self._open_project),
            ("Run Responsiveness Check", self._run_demo_job),
            ("About", self._show_about),
        ]

    def _palette_workspace_entries(self) -> list[tuple[str, Callable[[], None]]]:
        entries: list[tuple[str, Callable[[], None]]] = []
        project = self._container.workspace.project
        if project is None:
            return entries
        for dataset in project.datasets:
            alias = dataset.alias

            def _open_dataset(_alias: str = alias) -> None:
                self._select_module("Data")
                if hasattr(self, "_data_view"):
                    self._data_view.refresh()
                    for row in range(self._data_view._dataset_list.count()):  # noqa: SLF001
                        item = self._data_view._dataset_list.item(row)  # noqa: SLF001
                        if item is not None and item.text() == _alias:
                            self._data_view._dataset_list.setCurrentRow(row)  # noqa: SLF001
                            break

            entries.append((f"Dataset: {alias}", _open_dataset))
            if dataset.current_revision_id is not None:
                try:
                    columns = self._container.workspace.analytics.columns(
                        dataset.current_revision_id
                    )
                except Exception:  # noqa: BLE001
                    columns = ()
                for col in columns:
                    col_alias = alias

                    def _open_column(_a: str = col_alias) -> None:
                        _open_dataset(_alias=_a)

                    entries.append((f"Column: {alias}.{col.name}", _open_column))
        for dashboard in project.dashboards:
            title = dashboard.title

            def _open_dash(_title: str = title) -> None:
                self._select_module("Dashboard")
                if hasattr(self, "_dashboard_view"):
                    self._dashboard_view.refresh()
                    for row in range(self._dashboard_view._dash_list.count()):  # noqa: SLF001
                        item = self._dashboard_view._dash_list.item(row)  # noqa: SLF001
                        if item is not None and item.text() == _title:
                            self._dashboard_view._dash_list.setCurrentRow(row)  # noqa: SLF001
                            break

            entries.append((f"Dashboard: {title}", _open_dash))
        for chart in project.charts:
            entries.append((f"Chart: {chart.title}", self._go_visualize))
        for report in project.reports:
            entries.append((f"Report: {report.title}", self._go_reports))
        return entries

    def _go_home(self) -> None:
        self._select_module("Home")

    def _go_data(self) -> None:
        self._select_module("Data")

    def _go_prepare(self) -> None:
        self._select_module("Prepare")

    def _go_visualize(self) -> None:
        self._select_module("Visualize")

    def _go_dashboard(self) -> None:
        self._select_module("Dashboard")

    def _go_reports(self) -> None:
        self._select_module("Reports")

    def _go_settings(self) -> None:
        self._select_module("Settings")

    def _go_help(self) -> None:
        self._select_module("Help")

    def _select_module(self, name: str) -> None:
        self._show_module(name)

    def _run_demo_job(self) -> None:
        self._container.jobs.submit("demo-sleep", demo_sleep_worker)
        self._toast_host.show_message("Responsiveness check started")
        self._show_task_center()

    def _show_task_center(self) -> None:
        dock = self.findChild(QDockWidget, "TaskCenterDock")
        if dock is not None:
            dock.show()
            dock.raise_()
        self._job_center.setFocus()

    def _show_about(self) -> None:
        QMessageBox.about(self, "About Prism BI", self.about_text())

    def about_text(self) -> str:
        lines = [
            f"{self._container.config.app_name}",
            f"Version: {__version__}",
            f"User data: {self._container.config.user_data_dir}",
            f"Logs: {self._container.config.user_data_dir / 'logs'}",
            "",
            "License: Proprietary — see LICENSE in the product distribution.",
            "",
            "Plugins:",
        ]
        for summary in self._container.plugins.plugin_summaries():
            state = "active" if summary["active"] else f"inactive ({summary['error']})"
            lines.append(f"  - {summary['name']} {summary['version']} [{state}]")
        return "\n".join(lines)


def run_shell(container: AppContainer) -> int:
    """Create QApplication and show the main window."""
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    app.setApplicationName(container.config.app_name)
    app.setOrganizationName("Prism BI")
    app.setApplicationVersion(__version__)
    apply_theme(app, load_theme_preference())
    activated = container.plugins.activate_pending()
    if activated:
        container.logger.info("Activated %s deferred plugins", activated)
    window = MainWindow(container)
    window.show()
    app.processEvents()
    if container.config.settings_recovered:
        window._toast_host.show_message(  # noqa: SLF001
            "Settings were corrupt — using defaults (see logs)."
        )
    app.aboutToQuit.connect(lambda: _shutdown(container))
    return int(app.exec())


def _shutdown(container: AppContainer) -> None:
    container.plugins.deactivate_all()
    container.workspace.close()
    container.jobs.shutdown(wait=False)
