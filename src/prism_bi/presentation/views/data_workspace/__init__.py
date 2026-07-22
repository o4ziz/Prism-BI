"""Data workspace — import, explore, profile inspector."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from prism_bi.application.use_cases.export_data import export_dataset
from prism_bi.application.use_cases.import_data import import_materialize
from prism_bi.application.use_cases.profile_data import profile_revision
from prism_bi.domain.paths import validate_export_destination, validate_user_file
from prism_bi.presentation.views.data_workspace.table_model import RevisionTableModel
from prism_bi.presentation.widgets.empty_state import make_empty_state
from prism_bi.presentation.widgets.page_header import PageHeader
from prism_bi_sdk.contributions import ContributionKind
from prism_bi_sdk.datasources import IDataSourcePlugin
from prism_bi_sdk.dto.job import JobProgress
from prism_bi_sdk.dto.schema import EntityHandle

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class DataWorkspaceView(QWidget):
    """Primary Data module UI."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("DataWorkspaceView")
        self.setAccessibleName("Data workspace")

        root = QVBoxLayout(self)
        root.addWidget(
            PageHeader(
                "Data",
                "Import files, explore tables, profile columns, and export selections.",
            )
        )
        toolbar = QHBoxLayout()
        self._import_btn = QPushButton("Import…")
        self._import_btn.setObjectName("PrimaryButton")
        self._import_btn.setAccessibleName("Import data file")
        self._import_btn.clicked.connect(self._import_file)
        self._profile_btn = QPushButton("Profile")
        self._profile_btn.setAccessibleName("Profile selected dataset")
        self._profile_btn.clicked.connect(self._run_profile)
        self._export_btn = QPushButton("Export…")
        self._export_btn.setAccessibleName("Export selected dataset")
        self._export_btn.clicked.connect(self._export_dataset)
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._import_btn)
        toolbar.addWidget(self._profile_btn)
        toolbar.addWidget(self._export_btn)
        toolbar.addWidget(self._refresh_btn)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self._status = make_empty_state("Open or create a project to import data.")
        root.addWidget(self._status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._dataset_list = QListWidget()
        self._dataset_list.setObjectName("DatasetList")
        self._dataset_list.setAccessibleName("Datasets")
        self._dataset_list.currentItemChanged.connect(self._on_dataset_selected)
        splitter.addWidget(self._dataset_list)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self._table = QTableView()
        self._table.setObjectName("DataGrid")
        self._table.setAccessibleName("Data grid")
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        center_layout.addWidget(self._table)
        splitter.addWidget(center)

        self._inspector = QTextEdit()
        self._inspector.setObjectName("ProfileInspector")
        self._inspector.setAccessibleName("Profile inspector")
        self._inspector.setReadOnly(True)
        self._inspector.setPlaceholderText("Profile metrics appear here.")
        splitter.addWidget(self._inspector)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)

        self._current_dataset_id: UUID | None = None
        self.refresh()

    def refresh(self) -> None:
        self._dataset_list.clear()
        session = self._container.workspace
        if not session.is_open:
            self._status.setText("Open or create a project to import data.")
            self._status.show()
            self._inspector.setPlainText("")
            self._table.setModel(None)
            return
        summaries = session.dataset_summaries()
        if not summaries:
            self._status.setText(
                "No datasets yet — click Import to add CSV, Excel, JSON, or SQLite."
            )
            self._status.show()
        else:
            self._status.hide()
        for summary in summaries:
            item = QListWidgetItem(str(summary["alias"]))
            item.setData(Qt.ItemDataRole.UserRole, summary["id"])
            self._dataset_list.addItem(item)
        if self._dataset_list.count():
            self._dataset_list.setCurrentRow(0)

    def _on_dataset_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            return
        dataset_id = UUID(str(current.data(Qt.ItemDataRole.UserRole)))
        self._current_dataset_id = dataset_id
        self._load_grid(dataset_id)
        cache_key = None
        project = self._container.workspace.project
        if project:
            ds = project.get_dataset(dataset_id)
            if ds and ds.current_revision_id:
                cache_key = str(ds.current_revision_id)
        if cache_key and cache_key in self._container.workspace.profile_cache:
            self._show_profile(self._container.workspace.profile_cache[cache_key])

    def _load_grid(self, dataset_id: UUID) -> None:
        session = self._container.workspace
        project = session.project
        if project is None:
            return
        dataset = project.get_dataset(dataset_id)
        if dataset is None or dataset.current_revision_id is None:
            return
        model = RevisionTableModel(
            session.analytics,
            dataset.current_revision_id,
            window_size=self._container.config.performance.grid_window_rows,
        )
        self._table.setModel(model)

    def _import_file(self) -> None:
        session = self._container.workspace
        if not session.is_open:
            QMessageBox.warning(self, "Import", "Create or open a project first.")
            return
        if self._container.jobs.has_running():
            QMessageBox.information(
                self, "Import", "Wait for the current background job to finish."
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import data",
            "",
            "Data files (*.csv *.tsv *.txt *.json *.xlsx *.sqlite *.db *.sqlite3);;All files (*.*)",
        )
        if not path:
            return
        try:
            file_path = validate_user_file(Path(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import", str(exc))
            return
        plugin = self._resolve_plugin(file_path)
        if plugin is None:
            QMessageBox.warning(self, "Import", "No datasource plugin matches this file.")
            return
        try:
            entities = plugin.discover(str(file_path))
            if not entities:
                QMessageBox.warning(self, "Import", "No entities discovered.")
                return
            entity = self._pick_entity(entities)
            if entity is None:
                return
            plan = plugin.materialize(entity)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        plugin_id = plugin.manifest.id
        chunk_rows = self._container.config.performance.import_chunk_rows

        def worker(progress: object, cancelled: object) -> None:
            assert callable(progress) and callable(cancelled)
            progress(JobProgress(5, "Materializing…"))
            if cancelled():
                return
            result = import_materialize(
                session,
                plugin_id=plugin_id,
                plan=plan,
                chunk_rows=chunk_rows,
            )
            if cancelled():
                return
            if not result.success:
                raise RuntimeError(result.message or "Import failed")
            progress(JobProgress(100, "Import complete"))

        self._container.jobs.submit(f"import:{file_path.name}", worker)
        self._status.setText("Import running in background…")
        self._status.show()

    def _run_profile(self) -> None:
        if self._current_dataset_id is None:
            return
        if self._container.jobs.has_running():
            QMessageBox.information(
                self, "Profile", "Wait for the current background job to finish."
            )
            return
        dataset_id = self._current_dataset_id
        session = self._container.workspace

        def worker(progress: object, cancelled: object) -> None:
            assert callable(progress) and callable(cancelled)
            progress(JobProgress(10, "Profiling…"))
            if cancelled():
                return
            result = profile_revision(session, dataset_id)
            if cancelled():
                return
            if not result.success:
                raise RuntimeError(result.message or "Profiling failed")
            progress(JobProgress(100, "Profile complete"))

        self._container.jobs.submit("profile-dataset", worker)
        self._status.setText("Profiling in background…")
        self._status.show()

    def _export_dataset(self) -> None:
        if self._current_dataset_id is None:
            QMessageBox.warning(self, "Export", "Select a dataset first.")
            return
        if self._container.jobs.has_running():
            QMessageBox.information(
                self, "Export", "Wait for the current background job to finish."
            )
            return
        formats = [
            fmt
            for fmt in self._container.exporters.available_formats()
            if fmt in {"csv", "xlsx", "json"}
        ]
        if not formats:
            QMessageBox.warning(self, "Export", "No tabular exporters loaded.")
            return
        from PySide6.QtWidgets import QInputDialog

        format_id, ok = QInputDialog.getItem(self, "Export dataset", "Format:", formats, 0, False)
        if not ok:
            return
        filters = {
            "csv": "CSV (*.csv)",
            "xlsx": "Excel (*.xlsx)",
            "json": "JSON (*.json)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export dataset",
            f"export.{format_id}",
            filters.get(format_id, "All (*.*)"),
        )
        if not path:
            return
        try:
            dest = validate_export_destination(Path(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", str(exc))
            return
        dataset_id = self._current_dataset_id
        session = self._container.workspace
        builder = self._container.export_builder
        exporters = self._container.exporters

        def worker(progress: object, cancelled: object) -> None:
            assert callable(progress) and callable(cancelled)
            progress(JobProgress(15, f"Exporting {format_id}…"))
            if cancelled():
                return
            result = export_dataset(
                session,
                builder,
                exporters,
                dataset_id=dataset_id,
                format_id=format_id,
                destination=dest,
            )
            if cancelled():
                return
            if not result.success:
                raise RuntimeError(result.message or "Export failed")
            progress(JobProgress(100, f"Saved {dest.name}"))

        self._container.jobs.submit(f"export:{format_id}", worker)
        self._status.setText("Export running in background…")
        self._status.show()

    def _resolve_plugin(self, path: Path) -> IDataSourcePlugin | None:
        ext = path.suffix.lower()
        for reg in self._container.plugins.registry.list_by_kind(ContributionKind.DATA_SOURCES):
            meta = reg.metadata or {}
            extensions = [str(e).lower() for e in meta.get("extensions", [])]
            if ext in extensions:
                factory = reg.factory
                if hasattr(factory, "materialize") and hasattr(factory, "discover"):
                    return factory  # type: ignore[no-any-return]
        return None

    def _pick_entity(self, entities: list[EntityHandle]) -> EntityHandle | None:
        if len(entities) == 1:
            return entities[0]
        from PySide6.QtWidgets import QInputDialog

        labels = [entity.display_name for entity in entities]
        choice, ok = QInputDialog.getItem(self, "Select entity", "Sheet / table:", labels, 0, False)
        if not ok:
            return None
        for entity in entities:
            if entity.display_name == choice:
                return entity
        return entities[0]

    def _show_profile(self, report: object) -> None:
        from prism_bi.domain.profiling import ProfileReport

        assert isinstance(report, ProfileReport)
        lines = [
            f"Rows: {report.row_count}",
            f"Duplicate rows (approx): {report.duplicate_row_count}",
            f"Sampled: {report.sampled}",
            "",
            "Columns:",
        ]
        for col in report.columns:
            lines.append(
                f"- {col.name} [{col.logical_type.value}] "
                f"nulls={col.null_count} ({col.null_ratio:.1%}) "
                f"distinct={col.distinct_count} "
                f"outliers={col.outlier_count} "
                f"{'KEY?' if col.is_candidate_key else ''}"
            )
        if report.relationship_hints:
            lines.append("")
            lines.append("Relationship hints:")
            for hint in report.relationship_hints:
                lines.append(f"- {hint}")
        self._inspector.setPlainText("\n".join(lines))
