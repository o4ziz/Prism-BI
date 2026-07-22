"""Visualize module — chart builder."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from prism_bi.application.use_cases.export_data import export_chart_png
from prism_bi.application.use_cases.manage_visualization import delete_chart, save_chart
from prism_bi.presentation.widgets.chart_host import ChartHostWidget
from prism_bi.presentation.widgets.page_header import PageHeader
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class VisualizeView(QWidget):
    """Build and preview charts without writing SQL."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("VisualizeView")
        self._editing_id: UUID | None = None

        root = QHBoxLayout(self)
        outer = QVBoxLayout()
        outer.addWidget(
            PageHeader(
                "Visualize",
                "Build charts from aggregated fields — no SQL required.",
            )
        )
        splitter = QSplitter()
        outer.addWidget(splitter)
        root.addLayout(outer)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Charts"))
        self._chart_list = QListWidget()
        self._chart_list.currentRowChanged.connect(self._on_select_chart)
        left_layout.addWidget(self._chart_list)
        btn_row = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new_chart)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_chart)
        btn_row.addWidget(new_btn)
        btn_row.addWidget(del_btn)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        center = QWidget()
        form = QFormLayout(center)
        self._title = QLineEdit()
        self._datasets = QComboBox()
        self._datasets.currentIndexChanged.connect(self._reload_fields)
        self._chart_type = QComboBox()
        self._x_field = QComboBox()
        self._y_field = QComboBox()
        self._y_agg = QComboBox()
        self._y_agg.addItems(["sum", "avg", "count", "min", "max"])
        self._series_field = QComboBox()
        form.addRow("Title", self._title)
        form.addRow("Dataset", self._datasets)
        form.addRow("Chart type", self._chart_type)
        form.addRow("X / category", self._x_field)
        form.addRow("Y / value", self._y_field)
        form.addRow("Y aggregation", self._y_agg)
        form.addRow("Series (optional)", self._series_field)
        actions = QHBoxLayout()
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self._preview)
        save_btn = QPushButton("Save chart")
        save_btn.clicked.connect(self._save)
        export_btn = QPushButton("Export PNG…")
        export_btn.clicked.connect(self._export_png)
        actions.addWidget(preview_btn)
        actions.addWidget(save_btn)
        actions.addWidget(export_btn)
        form.addRow(actions)
        splitter.addWidget(center)

        self._host = ChartHostWidget(container.chart_data, container.chart_renderers)
        splitter.addWidget(self._host)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)

        self.refresh()

    def refresh(self) -> None:
        self._chart_type.blockSignals(True)
        self._chart_type.clear()
        for chart_type in self._container.chart_renderers.available_types():
            self._chart_type.addItem(chart_type)
        self._chart_type.blockSignals(False)

        self._datasets.blockSignals(True)
        self._datasets.clear()
        session = self._container.workspace
        if session.is_open:
            for summary in session.dataset_summaries():
                self._datasets.addItem(str(summary["alias"]), summary["id"])
        self._datasets.blockSignals(False)
        self._reload_fields()

        self._chart_list.clear()
        if session.is_open and session.project is not None:
            for chart in session.project.charts:
                item = QListWidgetItem(f"{chart.title} ({chart.chart_type})")
                item.setData(256, str(chart.id))
                self._chart_list.addItem(item)

    def _reload_fields(self) -> None:
        self._x_field.clear()
        self._y_field.clear()
        self._series_field.clear()
        self._series_field.addItem("(none)", "")
        dataset_id = self._datasets.currentData()
        if dataset_id is None:
            return
        try:
            fields = self._container.chart_data.list_fields(UUID(str(dataset_id)))
        except Exception:  # noqa: BLE001
            return
        for field in fields:
            self._x_field.addItem(field.name, field.name)
            self._y_field.addItem(field.name, field.name)
            self._series_field.addItem(field.name, field.name)

    def _build_spec(self) -> ChartSpec | None:
        dataset_id = self._datasets.currentData()
        if dataset_id is None:
            QMessageBox.warning(self, "Chart", "Select a dataset.")
            return None
        x_field = self._x_field.currentData()
        if not x_field and self._chart_type.currentText() != "table":
            QMessageBox.warning(self, "Chart", "Select an X field.")
            return None
        encodings: list[ChartEncoding] = []
        if x_field:
            encodings.append(ChartEncoding(role="x", field=str(x_field)))
        y_field = self._y_field.currentData()
        if y_field and self._chart_type.currentText() not in {"histogram", "table"}:
            encodings.append(
                ChartEncoding(
                    role="y",
                    field=str(y_field),
                    aggregation=self._y_agg.currentText(),
                )
            )
        series = self._series_field.currentData()
        if series:
            encodings.append(ChartEncoding(role="series", field=str(series)))
        chart_id = self._editing_id or uuid4()
        return ChartSpec(
            id=chart_id,
            chart_type=self._chart_type.currentText() or "bar",
            dataset_id=UUID(str(dataset_id)),
            title=self._title.text().strip() or "Untitled chart",
            encodings=tuple(encodings),
        )

    def _preview(self) -> None:
        spec = self._build_spec()
        if spec is None:
            return
        try:
            self._host.bind(spec)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preview failed", str(exc))

    def _save(self) -> None:
        spec = self._build_spec()
        if spec is None:
            return
        result = save_chart(self._container.workspace, spec)
        if not result.success:
            QMessageBox.critical(self, "Save chart", result.message or "Failed")
            return
        self._editing_id = spec.id
        self.refresh()
        self._host.bind(spec)

    def _new_chart(self) -> None:
        self._editing_id = None
        self._title.clear()
        self._host.clear()
        self._chart_list.clearSelection()

    def _delete_chart(self) -> None:
        item = self._chart_list.currentItem()
        assert item is not None
        chart_id = UUID(str(item.data(256)))
        result = delete_chart(self._container.workspace, chart_id)
        if not result.success:
            QMessageBox.critical(self, "Delete chart", result.message or "Failed")
            return
        self._new_chart()
        self.refresh()

    def _on_select_chart(self, row: int) -> None:
        if row < 0:
            return
        item = self._chart_list.item(row)
        assert item is not None
        project = self._container.workspace.project
        if project is None:
            return
        chart = project.get_chart(UUID(str(item.data(256))))
        if chart is None:
            return
        self._editing_id = chart.id
        self._title.setText(chart.title)
        idx = self._chart_type.findText(chart.chart_type)
        if idx >= 0:
            self._chart_type.setCurrentIndex(idx)
        ds_idx = self._datasets.findData(str(chart.dataset_id))
        if ds_idx >= 0:
            self._datasets.setCurrentIndex(ds_idx)
        self._reload_fields()
        for enc in chart.encodings:
            if enc.role == "x":
                i = self._x_field.findData(enc.field)
                if i >= 0:
                    self._x_field.setCurrentIndex(i)
            elif enc.role == "y":
                i = self._y_field.findData(enc.field)
                if i >= 0:
                    self._y_field.setCurrentIndex(i)
                if enc.aggregation:
                    a = self._y_agg.findText(enc.aggregation)
                    if a >= 0:
                        self._y_agg.setCurrentIndex(a)
            elif enc.role == "series":
                i = self._series_field.findData(enc.field)
                if i >= 0:
                    self._series_field.setCurrentIndex(i)
        try:
            self._host.bind(chart)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Chart", str(exc))

    def _export_png(self) -> None:
        if self._editing_id is None:
            QMessageBox.warning(self, "Export PNG", "Save the chart first.")
            return
        from pathlib import Path

        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "chart.png", "PNG (*.png)")
        if not path:
            return
        result = export_chart_png(
            self._container.workspace,
            self._container.export_builder,
            self._container.exporters,
            chart_id=self._editing_id,
            destination=Path(path),
        )
        if not result.success:
            QMessageBox.critical(self, "Export PNG", result.message or "Failed")
            return
        QMessageBox.information(self, "Export PNG", f"Saved {result.value}")
