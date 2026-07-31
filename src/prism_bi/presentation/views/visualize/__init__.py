"""Visualize module — commercial chart designer UI (presentation only)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from prism_bi.application.use_cases.export_data import export_chart_png
from prism_bi.application.use_cases.manage_visualization import delete_chart, save_chart
from prism_bi.presentation.theme.icons import icon_visualize
from prism_bi.presentation.widgets.chart_host import ChartHostWidget
from prism_bi.presentation.widgets.collapsible_section import CollapsibleSection
from prism_bi.presentation.widgets.empty_state import EmptyStatePanel
from prism_bi.presentation.widgets.page_header import PageHeader
from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class VisualizeView(QWidget):
    """Three-pane chart designer: library · properties · live preview."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("VisualizeView")
        self._editing_id: UUID | None = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(
            PageHeader(
                "Visualize",
                "Design charts with a live preview — fields left, canvas right.",
            )
        )

        self._toolbar = QToolBar()
        self._toolbar.setObjectName("VisualizeToolBar")
        self._toolbar.setMovable(False)
        self._act_preview = QAction("Preview", self)
        self._act_preview.triggered.connect(self._preview)
        self._act_save = QAction("Save", self)
        self._act_save.triggered.connect(self._save)
        self._act_dup = QAction("Duplicate", self)
        self._act_dup.triggered.connect(self._duplicate_chart)
        self._act_rename = QAction("Rename", self)
        self._act_rename.triggered.connect(self._focus_title)
        self._act_export = QAction("Export PNG", self)
        self._act_export.triggered.connect(self._export_png)
        self._act_reset = QAction("Reset", self)
        self._act_reset.triggered.connect(self._reset_editor)
        self._act_refresh = QAction("Refresh", self)
        self._act_refresh.triggered.connect(self._preview)
        for action in (
            self._act_preview,
            self._act_save,
            self._act_dup,
            self._act_rename,
            self._act_export,
            self._act_reset,
            self._act_refresh,
        ):
            self._toolbar.addAction(action)
        root.addWidget(self._toolbar)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._empty = EmptyStatePanel(
            "Create your first visualization",
            "Pick a dataset, choose chart type and fields, then preview on the canvas. "
            "Save charts to reuse them on dashboards and reports.",
            primary_label="New chart",
            on_primary=self._new_chart,
            secondary_label="Tip",
            on_secondary=self._show_empty_tip,
        )
        self._stack.addWidget(self._empty)

        designer = QWidget()
        designer.setObjectName("VisualizeDesigner")
        designer_layout = QHBoxLayout(designer)
        designer_layout.setContentsMargins(0, 8, 0, 0)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        designer_layout.addWidget(self._splitter)
        self._stack.addWidget(designer)

        self._splitter.addWidget(self._build_library_panel())
        self._splitter.addWidget(self._build_property_panel())
        self._splitter.addWidget(self._build_preview_panel())
        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setStretchFactor(2, 6)
        self._splitter.setSizes([220, 320, 720])

        self.refresh()

    def _show_empty_tip(self) -> None:
        QMessageBox.information(
            self,
            "Tip",
            "Open samples/SalesDemo.prism from Home, then select the seeded chart "
            "or create a new one here.",
        )

    def _build_library_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ContentPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Saved charts")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search charts…")
        self._search.textChanged.connect(self._filter_chart_list)
        layout.addWidget(self._search)

        self._chart_list = QListWidget()
        self._chart_list.setObjectName("ChartLibraryList")
        self._chart_list.currentRowChanged.connect(self._on_select_chart)
        layout.addWidget(self._chart_list, stretch=1)

        actions = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.setObjectName("PrimaryButton")
        new_btn.clicked.connect(self._new_chart)
        dup_btn = QPushButton("Duplicate")
        dup_btn.clicked.connect(self._duplicate_chart)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_chart)
        actions.addWidget(new_btn)
        actions.addWidget(dup_btn)
        actions.addWidget(del_btn)
        layout.addLayout(actions)
        panel.setMinimumWidth(180)
        panel.setMaximumWidth(360)
        return panel

    def _build_property_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ContentPanel")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Chart builder")
        header.setObjectName("SectionTitle")
        header.setContentsMargins(12, 12, 12, 0)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        scroll.setWidget(body)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(8, 4, 8, 12)
        body_layout.setSpacing(10)

        general = CollapsibleSection("General", expanded=True)
        form_g = QFormLayout()
        form_g.setSpacing(8)
        self._title = QLineEdit()
        self._title.setPlaceholderText("Chart title")
        self._datasets = QComboBox()
        self._datasets.currentIndexChanged.connect(self._reload_fields)
        self._chart_type = QComboBox()
        self._description = QLineEdit()
        self._description.setPlaceholderText("Optional description")
        form_g.addRow("Title", self._title)
        form_g.addRow("Dataset", self._datasets)
        form_g.addRow("Chart type", self._chart_type)
        form_g.addRow("Description", self._description)
        wrap_g = QWidget()
        wrap_g.setLayout(form_g)
        general.add_widget(wrap_g)
        body_layout.addWidget(general)

        axes = CollapsibleSection("Axes", expanded=True)
        form_a = QFormLayout()
        form_a.setSpacing(8)
        self._x_field = QComboBox()
        self._y_field = QComboBox()
        self._y_agg = QComboBox()
        self._y_agg.addItems(["sum", "avg", "count", "min", "max"])
        self._series_field = QComboBox()
        self._x_axis_title = QLineEdit()
        self._x_axis_title.setPlaceholderText("X axis title")
        self._y_axis_title = QLineEdit()
        self._y_axis_title.setPlaceholderText("Y axis title")
        form_a.addRow("X axis", self._x_field)
        form_a.addRow("Y axis", self._y_field)
        form_a.addRow("Aggregation", self._y_agg)
        form_a.addRow("Series", self._series_field)
        form_a.addRow("X title", self._x_axis_title)
        form_a.addRow("Y title", self._y_axis_title)
        wrap_a = QWidget()
        wrap_a.setLayout(form_a)
        axes.add_widget(wrap_a)
        body_layout.addWidget(axes)

        appearance = CollapsibleSection("Appearance", expanded=True)
        form_p = QFormLayout()
        form_p.setSpacing(8)
        self._show_legend = QCheckBox("Show legend")
        self._show_legend.setChecked(True)
        self._show_grid = QCheckBox("Show grid")
        self._show_grid.setChecked(True)
        self._show_labels = QCheckBox("Show category labels")
        self._show_labels.setChecked(True)
        self._label_angle = QSlider(Qt.Orientation.Horizontal)
        self._label_angle.setRange(0, 90)
        self._label_angle.setValue(45)
        self._label_angle.setToolTip("Rotate X-axis labels (degrees)")
        self._color_theme = QComboBox()
        self._color_theme.addItems(["Orange", "Mono"])
        form_p.addRow(self._show_legend)
        form_p.addRow(self._show_grid)
        form_p.addRow(self._show_labels)
        form_p.addRow("Label angle", self._label_angle)
        form_p.addRow("Colors", self._color_theme)
        wrap_p = QWidget()
        wrap_p.setLayout(form_p)
        appearance.add_widget(wrap_p)
        body_layout.addWidget(appearance)

        advanced = CollapsibleSection("Advanced", expanded=False)
        form_adv = QFormLayout()
        form_adv.setSpacing(8)
        self._sort_mode = QComboBox()
        self._sort_mode.addItems(["Default", "Category A→Z", "Category Z→A", "Value ↑", "Value ↓"])
        self._top_n = QSpinBox()
        self._top_n.setRange(0, 500)
        self._top_n.setSpecialValueText("All")
        self._null_handling = QComboBox()
        self._null_handling.addItems(["Skip nulls", "Treat as zero", "Keep labels"])
        self._filter_field = QComboBox()
        self._filter_value = QLineEdit()
        self._filter_value.setPlaceholderText("Filter value (optional)")
        form_adv.addRow("Sorting", self._sort_mode)
        form_adv.addRow("Top N", self._top_n)
        form_adv.addRow("Nulls", self._null_handling)
        form_adv.addRow("Filter field", self._filter_field)
        form_adv.addRow("Filter value", self._filter_value)
        wrap_adv = QWidget()
        wrap_adv.setLayout(form_adv)
        advanced.add_widget(wrap_adv)
        body_layout.addWidget(advanced)
        body_layout.addStretch(1)
        panel.setMinimumWidth(260)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("ChartPreviewPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._host = ChartHostWidget(
            self._container.chart_data, self._container.chart_renderers
        )
        self._host.setMinimumSize(360, 280)
        self._host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        header = QHBoxLayout()
        title = QLabel("Live preview")
        title.setObjectName("SectionTitle")
        header.addWidget(title, stretch=1)
        self._btn_zoom_in = QPushButton("+")
        self._btn_zoom_in.setFixedWidth(32)
        self._btn_zoom_in.setToolTip("Zoom in")
        self._btn_zoom_in.clicked.connect(lambda: self._host.zoom(1.2))
        self._btn_zoom_out = QPushButton("−")
        self._btn_zoom_out.setFixedWidth(32)
        self._btn_zoom_out.setToolTip("Zoom out")
        self._btn_zoom_out.clicked.connect(lambda: self._host.zoom(1 / 1.2))
        self._btn_fit = QPushButton("Fit")
        self._btn_fit.setToolTip("Fit to window")
        self._btn_fit.clicked.connect(self._host.fit_to_view)
        self._btn_prev_refresh = QPushButton("Refresh")
        self._btn_prev_refresh.clicked.connect(self._preview)
        self._btn_prev_export = QPushButton("PNG")
        self._btn_prev_export.setObjectName("PrimaryButton")
        self._btn_prev_export.clicked.connect(self._export_png)
        for btn in (
            self._btn_zoom_in,
            self._btn_zoom_out,
            self._btn_fit,
            self._btn_prev_refresh,
            self._btn_prev_export,
        ):
            header.addWidget(btn)
        layout.addLayout(header)
        layout.addWidget(self._host, stretch=1)

        self._preview_hint = QLabel("Preview updates when you click Preview or Save.")
        self._preview_hint.setObjectName("PageSubtitle")
        layout.addWidget(self._preview_hint)
        return panel

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
                item = QListWidgetItem(icon_visualize(), f"{chart.title}")
                item.setToolTip(f"{chart.title} · {chart.chart_type}")
                item.setData(Qt.ItemDataRole.UserRole, str(chart.id))
                self._chart_list.addItem(item)

        self._filter_chart_list(self._search.text())
        # Designer stays available whenever a project is open (create first chart).
        self._stack.setCurrentIndex(1 if session.is_open else 0)

    def _filter_chart_list(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self._chart_list.count()):
            item = self._chart_list.item(row)
            assert item is not None
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _reload_fields(self) -> None:
        self._x_field.clear()
        self._y_field.clear()
        self._series_field.clear()
        self._series_field.addItem("(none)", "")
        self._filter_field.clear()
        self._filter_field.addItem("(none)", "")
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
            self._filter_field.addItem(field.name, field.name)

    def _options_from_ui(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "description": self._description.text().strip(),
            "show_legend": self._show_legend.isChecked(),
            "show_grid": self._show_grid.isChecked(),
            "show_labels": self._show_labels.isChecked(),
            "label_angle": int(self._label_angle.value()),
            "color_theme": self._color_theme.currentText().lower(),
            "x_axis_title": self._x_axis_title.text().strip(),
            "y_axis_title": self._y_axis_title.text().strip(),
            "sort": self._sort_mode.currentText(),
            "top_n": int(self._top_n.value()),
            "null_handling": self._null_handling.currentText(),
        }
        field = self._filter_field.currentData()
        value = self._filter_value.text().strip()
        if field and value:
            options["filters"] = [{"field": str(field), "op": "eq", "value": value}]
        return options

    def _apply_options_to_ui(self, options: dict[str, Any]) -> None:
        self._description.setText(str(options.get("description", "")))
        self._show_legend.setChecked(bool(options.get("show_legend", True)))
        self._show_grid.setChecked(bool(options.get("show_grid", True)))
        self._show_labels.setChecked(bool(options.get("show_labels", True)))
        self._label_angle.setValue(int(options.get("label_angle", 45)))
        theme = str(options.get("color_theme", "orange")).title()
        if theme in {"Teal", "Ocean", "Sunset"}:
            theme = "Orange"
        idx = self._color_theme.findText(theme)
        if idx >= 0:
            self._color_theme.setCurrentIndex(idx)
        self._x_axis_title.setText(str(options.get("x_axis_title", "")))
        self._y_axis_title.setText(str(options.get("y_axis_title", "")))
        sort = str(options.get("sort", "Default"))
        sidx = self._sort_mode.findText(sort)
        if sidx >= 0:
            self._sort_mode.setCurrentIndex(sidx)
        self._top_n.setValue(int(options.get("top_n", 0) or 0))
        nulls = str(options.get("null_handling", "Skip nulls"))
        nidx = self._null_handling.findText(nulls)
        if nidx >= 0:
            self._null_handling.setCurrentIndex(nidx)
        filters = options.get("filters")
        if isinstance(filters, list) and filters:
            first = filters[0]
            if isinstance(first, dict):
                fidx = self._filter_field.findData(str(first.get("field", "")))
                if fidx >= 0:
                    self._filter_field.setCurrentIndex(fidx)
                self._filter_value.setText(str(first.get("value", "")))

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
            options=self._options_from_ui(),
        )

    def _preview(self) -> None:
        spec = self._build_spec()
        if spec is None:
            return
        try:
            self._host.bind(spec)
            self._preview_hint.setText(f"Preview · {spec.title} ({spec.chart_type})")
            self._stack.setCurrentIndex(1)
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
        self._select_chart_id(spec.id)
        self._host.bind(spec)
        self._preview_hint.setText(f"Saved · {spec.title}")

    def _new_chart(self) -> None:
        self._loading = True
        self._editing_id = None
        self._title.clear()
        self._description.clear()
        self._x_axis_title.clear()
        self._y_axis_title.clear()
        self._filter_value.clear()
        self._show_legend.setChecked(True)
        self._show_grid.setChecked(True)
        self._show_labels.setChecked(True)
        self._label_angle.setValue(45)
        self._color_theme.setCurrentIndex(0)
        self._sort_mode.setCurrentIndex(0)
        self._top_n.setValue(0)
        self._host.clear()
        self._chart_list.clearSelection()
        self._preview_hint.setText("New chart — configure fields, then Preview.")
        self._stack.setCurrentIndex(1)
        self._loading = False
        self._title.setFocus()

    def _duplicate_chart(self) -> None:
        spec = self._build_spec()
        if spec is None:
            return
        dup = ChartSpec(
            id=uuid4(),
            chart_type=spec.chart_type,
            dataset_id=spec.dataset_id,
            title=f"{spec.title} copy",
            encodings=spec.encodings,
            options=deepcopy(dict(spec.options)),
        )
        result = save_chart(self._container.workspace, dup)
        if not result.success:
            QMessageBox.critical(self, "Duplicate", result.message or "Failed")
            return
        self._editing_id = dup.id
        self.refresh()
        self._select_chart_id(dup.id)
        self._host.bind(dup)

    def _focus_title(self) -> None:
        self._title.setFocus()
        self._title.selectAll()

    def _reset_editor(self) -> None:
        if self._editing_id is None:
            self._new_chart()
            return
        project = self._container.workspace.project
        if project is None:
            return
        chart = project.get_chart(self._editing_id)
        if chart is None:
            self._new_chart()
            return
        self._load_chart(chart)
        try:
            self._host.bind(chart)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Chart", str(exc))

    def _delete_chart(self) -> None:
        row = self._chart_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete chart", "Select a chart to delete.")
            return
        item = self._chart_list.item(row)
        assert item is not None
        chart_id = UUID(str(item.data(Qt.ItemDataRole.UserRole)))
        result = delete_chart(self._container.workspace, chart_id)
        if not result.success:
            QMessageBox.critical(self, "Delete chart", result.message or "Failed")
            return
        self._new_chart()
        self.refresh()

    def _select_chart_id(self, chart_id: UUID) -> None:
        for row in range(self._chart_list.count()):
            item = self._chart_list.item(row)
            assert item is not None
            if str(item.data(Qt.ItemDataRole.UserRole)) == str(chart_id):
                self._chart_list.setCurrentRow(row)
                break

    def _on_select_chart(self, row: int) -> None:
        if row < 0 or self._loading:
            return
        item = self._chart_list.item(row)
        assert item is not None
        project = self._container.workspace.project
        if project is None:
            return
        chart = project.get_chart(UUID(str(item.data(Qt.ItemDataRole.UserRole))))
        if chart is None:
            return
        self._load_chart(chart)
        try:
            self._host.bind(chart)
            self._preview_hint.setText(f"Loaded · {chart.title}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Chart", str(exc))

    def _load_chart(self, chart: ChartSpec) -> None:
        self._loading = True
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
        self._apply_options_to_ui(dict(chart.options or {}))
        self._loading = False

    def _export_png(self) -> None:
        if self._editing_id is None:
            if self._host.current_view is not None:
                path, _ = QFileDialog.getSaveFileName(
                    self, "Export PNG", "chart.png", "PNG (*.png)"
                )
                if not path:
                    return
                try:
                    self._host.export_png(path)
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.critical(self, "Export PNG", str(exc))
                    return
                QMessageBox.information(self, "Export PNG", f"Saved {path}")
                return
            QMessageBox.warning(self, "Export PNG", "Preview or save a chart first.")
            return
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
