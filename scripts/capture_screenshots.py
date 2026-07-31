"""Capture shell screenshots for documentation.

Prefer a real Windows display for readable fonts. Falls back to offscreen
only when ``QT_QPA_PLATFORM`` is already set in the environment.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDockWidget

from prism_bi.application.use_cases.project_lifecycle import open_project
from prism_bi.bootstrap.container import build_container
from prism_bi.presentation.shell.main_window import MainWindow
from prism_bi.presentation.theme import ThemeMode, apply_theme


def _pump(app: QApplication, ms: int = 200) -> None:
    deadline = time.monotonic() + (ms / 1000.0)
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _hide_utility_docks(window: MainWindow) -> None:
    for name in ("TaskCenterDock", "LogsDock"):
        dock = window.findChild(QDockWidget, name)
        if dock is not None:
            dock.hide()


def _prepare_visualize(window: MainWindow, app: QApplication) -> None:
    view = getattr(window, "_visualize_view", None)
    if view is None:
        return
    view.refresh()
    _pump(app, 150)
    if view._chart_list.count() > 0:  # noqa: SLF001
        view._chart_list.setCurrentRow(0)  # noqa: SLF001
        _pump(app, 400)


def _prepare_data(window: MainWindow, app: QApplication) -> None:
    view = getattr(window, "_data_view", None)
    if view is None:
        return
    view.refresh()
    _pump(app, 200)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)

    # Prefer native platform so fonts render; allow CI to force offscreen.
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "windows"

    app = QApplication.instance() or QApplication(sys.argv)
    # Docs shots use the dark orange product theme.
    apply_theme(app, ThemeMode.DARK)

    container = build_container(
        repo_root=root,
        user_data_dir=root / ".ga-capture-userdata",
        use_keyring=False,
        console_logging=False,
    )
    container.plugins.activate_pending()

    sample = root / "samples" / "SalesDemo.prism"
    if sample.is_dir():
        opened = open_project(container.workspace, sample)
        if not opened.success:
            print(f"WARN: could not open sample: {opened.message}")

    window = MainWindow(container)
    window.resize(1440, 900)
    window.show()
    _hide_utility_docks(window)
    _pump(app, 300)

    modules = ("Home", "Data", "Prepare", "Visualize", "Dashboard", "Reports")
    for name in modules:
        window._select_module(name)  # noqa: SLF001
        _hide_utility_docks(window)
        _pump(app, 200)
        if name == "Visualize":
            _prepare_visualize(window, app)
        elif name == "Data":
            _prepare_data(window, app)
        else:
            view = getattr(window, f"_{name.lower()}_view", None)
            refresh = getattr(view, "refresh", None)
            if callable(refresh):
                refresh()
                _pump(app, 150)

        # Let QtCharts finish layout/paint before grabbing.
        _pump(app, 300)
        path = out / f"{name.lower()}.png"
        ok = window.grab().save(str(path), "PNG")
        size = path.stat().st_size if path.is_file() else 0
        print(f"{'OK' if ok else 'FAIL'}: {path} ({size} bytes)")

    container.plugins.deactivate_all()
    container.workspace.close()
    container.jobs.shutdown(wait=False)
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
