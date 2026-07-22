"""Capture shell screenshots for documentation.

Prefer a real Windows display for readable fonts. Falls back to offscreen
only when ``QT_QPA_PLATFORM`` is already set in the environment.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from prism_bi.application.use_cases.project_lifecycle import open_project
from prism_bi.bootstrap.container import build_container
from prism_bi.presentation.shell.main_window import MainWindow, _apply_stylesheet


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)

    # Prefer native platform so fonts render; allow CI to force offscreen.
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "windows"

    app = QApplication.instance() or QApplication(sys.argv)
    container = build_container(
        repo_root=root,
        user_data_dir=root / ".ga-capture-userdata",
        use_keyring=False,
        console_logging=False,
    )
    container.plugins.activate_pending()
    _apply_stylesheet(app)

    sample = root / "samples" / "SalesDemo.prism"
    if sample.is_dir():
        opened = open_project(container.workspace, sample)
        if not opened.success:
            print(f"WARN: could not open sample: {opened.message}")

    window = MainWindow(container)
    window.resize(1280, 800)
    window.show()
    app.processEvents()

    modules = ("Home", "Data", "Prepare", "Visualize", "Dashboard", "Reports")
    for name in modules:
        window._select_module(name)  # noqa: SLF001
        app.processEvents()
        path = out / f"{name.lower()}.png"
        ok = window.grab().save(str(path), "PNG")
        size = path.stat().st_size if path.is_file() else 0
        print(f"{'OK' if ok else 'FAIL'}: {path} ({size} bytes)")

    container.plugins.deactivate_all()
    container.workspace.close()
    container.jobs.shutdown(wait=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
