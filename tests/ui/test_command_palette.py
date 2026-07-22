"""Command palette indexes datasets by alias."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from prism_bi.application.use_cases.project_lifecycle import create_project
from prism_bi.bootstrap.container import build_container
from prism_bi.domain.entities.dataset import Dataset, DatasetRevision
from prism_bi.presentation.shell.main_window import MainWindow


def test_palette_finds_dataset_by_alias(qtbot, tmp_path: Path) -> None:
    container = build_container(
        user_data_dir=tmp_path,
        use_keyring=False,
        console_logging=False,
        repo_root=Path(__file__).resolve().parents[2],
    )
    window = MainWindow(container)
    qtbot.addWidget(window)
    assert create_project(container.workspace, tmp_path / "p.prism", "P").success
    assert container.workspace.project is not None
    container.workspace.project.add_dataset(
        Dataset(
            alias="Sales_Q1",
            id=uuid4(),
            source_plugin_id="x",
            source_entity_id="y",
            revisions=[
                DatasetRevision(
                    id=uuid4(),
                    parent_id=None,
                    created_at=datetime.now(UTC),
                    label="raw",
                    columns=(),
                )
            ],
        )
    )
    entries = window._palette_workspace_entries()  # noqa: SLF001
    labels = [label for label, _ in entries]
    assert any(label == "Dataset: Sales_Q1" for label in labels)
    container.plugins.deactivate_all()
    container.workspace.close()
    container.jobs.shutdown(wait=False)
