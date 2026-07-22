"""pytest-qt smoke for the Milestone 1 shell."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism_bi.bootstrap.container import build_container
from prism_bi.presentation.shell.main_window import MainWindow


@pytest.fixture
def main_window(qtbot, tmp_path: Path):
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    window = MainWindow(container)
    qtbot.addWidget(window)
    window.show()
    yield window
    container.plugins.deactivate_all()
    container.jobs.shutdown(wait=False)


def test_shell_has_modules_and_about(main_window: MainWindow, qtbot) -> None:
    assert main_window.objectName() == "PrismMainWindow"
    from PySide6.QtWidgets import QListWidget

    activity = main_window.findChild(QListWidget, "ActivityBar")
    assert activity is not None
    assert activity.count() == 8
    about = main_window.about_text()
    assert "Plugins:" in about
    assert "Null AI Provider" in about
    assert "QtCharts Chart Engine" in about
    assert "Tabular Exporters" in about
    assert hasattr(main_window, "_visualize_view")
    assert hasattr(main_window, "_dashboard_view")
    assert hasattr(main_window, "_reports_view")


def test_demo_job_does_not_block_ui(main_window: MainWindow, qtbot) -> None:
    # Start demo job; UI event loop should keep processing.
    main_window._run_demo_job()  # noqa: SLF001
    qtbot.wait(100)
    assert main_window.isVisible()
    # Pump events to prove responsiveness.
    for _ in range(5):
        qtbot.wait(50)
        assert main_window.isEnabled()
