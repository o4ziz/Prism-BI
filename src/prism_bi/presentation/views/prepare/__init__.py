"""Prepare module — cleaning pipeline editor."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prism_bi.application.use_cases.clean_data import apply_cleaning
from prism_bi.domain.cleaning import CleaningPipeline, CleaningStep
from prism_bi.presentation.widgets.page_header import PageHeader

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class PrepareView(QWidget):
    """Minimal cleaning UI: pick dataset, add built-in steps, apply."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("PrepareView")
        self._pipeline = CleaningPipeline()

        layout = QVBoxLayout(self)
        layout.addWidget(
            PageHeader(
                "Prepare",
                "Compose cleaning steps and apply them as a new dataset revision.",
            )
        )

        row = QHBoxLayout()
        self._datasets = QComboBox()
        row.addWidget(QLabel("Dataset"))
        row.addWidget(self._datasets, stretch=1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        layout.addLayout(row)

        ops = QHBoxLayout()
        self._op = QComboBox()
        self._op.addItems(
            [
                "drop_columns",
                "rename_column",
                "cast_column",
                "fill_null",
                "drop_nulls",
                "trim_column",
                "replace_values",
                "dedupe",
                "filter_rows",
            ]
        )
        self._params = QLineEdit()
        self._params.setPlaceholderText(
            'Params JSON, e.g. {"columns":["a"]} or {"column":"a","duck_type":"BIGINT"}'
        )
        add_btn = QPushButton("Add step")
        add_btn.clicked.connect(self._add_step)
        ops.addWidget(self._op)
        ops.addWidget(self._params, stretch=1)
        ops.addWidget(add_btn)
        layout.addLayout(ops)

        self._steps = QListWidget()
        layout.addWidget(self._steps)

        apply_btn = QPushButton("Apply pipeline")
        apply_btn.clicked.connect(self._apply)
        layout.addWidget(apply_btn)
        self.refresh()

    def refresh(self) -> None:
        self._datasets.clear()
        session = self._container.workspace
        if not session.is_open:
            return
        for summary in session.dataset_summaries():
            self._datasets.addItem(str(summary["alias"]), summary["id"])

    def _add_step(self) -> None:
        import json

        raw = self._params.text().strip() or "{}"
        try:
            params = json.loads(raw)
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "Params", f"Invalid JSON: {exc}")
            return
        step = CleaningStep(op=self._op.currentText(), params=params)
        self._pipeline.add(step)
        self._steps.addItem(QListWidgetItem(f"{step.op}: {step.params}"))

    def _apply(self) -> None:
        dataset_id_raw = self._datasets.currentData()
        if dataset_id_raw is None:
            QMessageBox.warning(self, "Clean", "Select a dataset.")
            return
        result = apply_cleaning(
            self._container.workspace,
            UUID(str(dataset_id_raw)),
            self._pipeline,
        )
        if not result.success:
            QMessageBox.critical(self, "Clean failed", result.message or "Unknown error")
            return
        QMessageBox.information(self, "Clean", f"Created revision {result.value}")
        self._pipeline = CleaningPipeline()
        self._steps.clear()
