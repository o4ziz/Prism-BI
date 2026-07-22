"""Dashboard module — canvas composition + filter linkage."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from prism_bi.application.use_cases.export_data import export_dashboard_pdf
from prism_bi.application.use_cases.manage_visualization import delete_dashboard, save_dashboard
from prism_bi.presentation.widgets.chart_host import ChartHostWidget
from prism_bi.presentation.widgets.page_header import PageHeader
from prism_bi_sdk.dto.chart import ChartSpec, DashboardSpec, DashboardWidget

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class DashboardView(QWidget):
    """Compose saved charts on a grid canvas with optional shared filter."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("DashboardView")
        self._editing_id: UUID | None = None
        self._widgets: list[DashboardWidget] = []
        self._hosts: dict[UUID, ChartHostWidget] = {}

        root = QHBoxLayout(self)
        shell = QVBoxLayout()
        shell.addWidget(
            PageHeader(
                "Dashboard",
                "Compose charts on a canvas with optional shared filters.",
            )
        )
        body = QHBoxLayout()
        shell.addLayout(body)
        root.addLayout(shell)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Dashboards"))
        self._dash_list = QListWidget()
        self._dash_list.currentRowChanged.connect(self._on_select_dashboard)
        left_layout.addWidget(self._dash_list)

        self._title = QLineEdit()
        self._title.setPlaceholderText("Dashboard title")
        left_layout.addWidget(self._title)

        left_layout.addWidget(QLabel("Add chart"))
        self._chart_pick = QComboBox()
        left_layout.addWidget(self._chart_pick)
        add_btn = QPushButton("Add widget")
        add_btn.clicked.connect(self._add_widget)
        left_layout.addWidget(add_btn)

        left_layout.addWidget(QLabel("Shared filter (optional)"))
        self._filter_field = QComboBox()
        self._filter_value = QLineEdit()
        self._filter_value.setPlaceholderText("Filter value")
        left_layout.addWidget(self._filter_field)
        left_layout.addWidget(self._filter_value)
        apply_filter = QPushButton("Apply filter")
        apply_filter.clicked.connect(self._render_canvas)
        left_layout.addWidget(apply_filter)

        save_btn = QPushButton("Save dashboard")
        save_btn.clicked.connect(self._save)
        export_btn = QPushButton("Export PDF…")
        export_btn.clicked.connect(self._export_pdf)
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete)
        left_layout.addWidget(save_btn)
        left_layout.addWidget(export_btn)
        left_layout.addWidget(new_btn)
        left_layout.addWidget(del_btn)
        left_layout.addStretch(1)
        body.addWidget(left, stretch=1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._canvas_host = QWidget()
        self._grid = QGridLayout(self._canvas_host)
        scroll.setWidget(self._canvas_host)
        body.addWidget(scroll, stretch=3)

        self.refresh()

    def refresh(self) -> None:
        self._dash_list.clear()
        self._chart_pick.clear()
        self._filter_field.clear()
        self._filter_field.addItem("(none)", "")
        session = self._container.workspace
        if not session.is_open or session.project is None:
            self._clear_canvas()
            return
        project = session.project
        for dashboard in project.dashboards:
            item = QListWidgetItem(dashboard.title)
            item.setData(256, str(dashboard.id))
            self._dash_list.addItem(item)
        for chart in project.charts:
            self._chart_pick.addItem(chart.title, str(chart.id))
            # Collect fields from first chart's dataset for filter UI
        if project.charts:
            try:
                fields = self._container.chart_data.list_fields(project.charts[0].dataset_id)
                for field in fields:
                    self._filter_field.addItem(field.name, field.name)
            except Exception:  # noqa: BLE001
                pass

    def _new(self) -> None:
        self._editing_id = None
        self._title.clear()
        self._widgets = []
        self._filter_value.clear()
        self._clear_canvas()

    def _clear_canvas(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._hosts.clear()

    def _add_widget(self) -> None:
        chart_id_raw = self._chart_pick.currentData()
        if chart_id_raw is None:
            QMessageBox.warning(self, "Dashboard", "Save a chart first, then add it here.")
            return
        # Place on next row
        row = max((w.y + w.height for w in self._widgets), default=0)
        widget = DashboardWidget(
            id=uuid4(),
            chart_id=UUID(str(chart_id_raw)),
            x=0,
            y=row,
            width=6,
            height=4,
        )
        self._widgets.append(widget)
        self._render_canvas()

    def _render_canvas(self) -> None:
        self._clear_canvas()
        project = self._container.workspace.project
        if project is None:
            return
        filters = self._current_filters()
        for widget in self._widgets:
            chart = project.get_chart(widget.chart_id)
            if chart is None:
                continue
            frame = QWidget()
            frame_layout = QVBoxLayout(frame)
            header = QHBoxLayout()
            header.addWidget(QLabel(chart.title))
            w_spin = QSpinBox()
            w_spin.setRange(1, 12)
            w_spin.setValue(widget.width)
            h_spin = QSpinBox()
            h_spin.setRange(1, 12)
            h_spin.setValue(widget.height)
            remove = QPushButton("Remove")
            wid = widget.id

            def _resize(
                _value: int = 0,
                *,
                target: UUID = wid,
                width_spin: QSpinBox = w_spin,
                height_spin: QSpinBox = h_spin,
            ) -> None:
                self._update_widget_size(target, width_spin.value(), height_spin.value())

            w_spin.valueChanged.connect(_resize)
            h_spin.valueChanged.connect(_resize)
            remove.clicked.connect(lambda _=False, target=wid: self._remove_widget(target))
            header.addWidget(QLabel("W"))
            header.addWidget(w_spin)
            header.addWidget(QLabel("H"))
            header.addWidget(h_spin)
            header.addWidget(remove)
            frame_layout.addLayout(header)

            host = ChartHostWidget(self._container.chart_data, self._container.chart_renderers)
            bound = _with_filters(chart, filters)
            try:
                host.bind(bound)
            except Exception as exc:  # noqa: BLE001
                frame_layout.addWidget(QLabel(f"Error: {exc}"))
            else:
                frame_layout.addWidget(host)
                self._hosts[widget.id] = host
            self._grid.addWidget(frame, widget.y, widget.x, widget.height, widget.width)

    def _update_widget_size(self, widget_id: UUID, width: int, height: int) -> None:
        updated: list[DashboardWidget] = []
        for widget in self._widgets:
            if widget.id == widget_id:
                updated.append(
                    DashboardWidget(
                        id=widget.id,
                        chart_id=widget.chart_id,
                        x=widget.x,
                        y=widget.y,
                        width=width,
                        height=height,
                    )
                )
            else:
                updated.append(widget)
        self._widgets = updated

    def _remove_widget(self, widget_id: UUID) -> None:
        self._widgets = [w for w in self._widgets if w.id != widget_id]
        self._render_canvas()

    def _current_filters(self) -> list[dict[str, Any]]:
        field = self._filter_field.currentData()
        value = self._filter_value.text().strip()
        if not field or not value:
            return []
        return [{"field": str(field), "op": "eq", "value": value}]

    def _save(self) -> None:
        if not self._title.text().strip():
            QMessageBox.warning(self, "Dashboard", "Enter a title.")
            return
        dashboard = DashboardSpec(
            id=self._editing_id or uuid4(),
            title=self._title.text().strip(),
            widgets=tuple(self._widgets),
            options={"filters": self._current_filters()},
        )
        result = save_dashboard(self._container.workspace, dashboard)
        if not result.success:
            QMessageBox.critical(self, "Save dashboard", result.message or "Failed")
            return
        self._editing_id = dashboard.id
        self.refresh()

    def _export_pdf(self) -> None:
        if self._editing_id is None:
            QMessageBox.warning(self, "Export PDF", "Save the dashboard first.")
            return
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Export dashboard PDF", "dashboard.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        result = export_dashboard_pdf(
            self._container.workspace,
            self._container.export_builder,
            self._container.exporters,
            dashboard_id=self._editing_id,
            destination=Path(path),
        )
        if not result.success:
            QMessageBox.critical(self, "Export PDF", result.message or "Failed")
            return
        QMessageBox.information(self, "Export PDF", f"Saved {result.value}")

    def _delete(self) -> None:
        if self._editing_id is None:
            return
        result = delete_dashboard(self._container.workspace, self._editing_id)
        if not result.success:
            QMessageBox.critical(self, "Delete dashboard", result.message or "Failed")
            return
        self._new()
        self.refresh()

    def _on_select_dashboard(self, row: int) -> None:
        if row < 0:
            return
        item = self._dash_list.item(row)
        assert item is not None
        project = self._container.workspace.project
        if project is None:
            return
        dashboard = project.get_dashboard(UUID(str(item.data(256))))
        if dashboard is None:
            return
        self._editing_id = dashboard.id
        self._title.setText(dashboard.title)
        self._widgets = list(dashboard.widgets)
        filters = dashboard.options.get("filters") or []
        if filters and isinstance(filters, list) and filters:
            first = filters[0]
            if isinstance(first, dict):
                field = str(first.get("field", ""))
                idx = self._filter_field.findData(field)
                if idx >= 0:
                    self._filter_field.setCurrentIndex(idx)
                self._filter_value.setText(str(first.get("value", "")))
        self._render_canvas()


def _with_filters(chart: ChartSpec, filters: list[dict[str, Any]]) -> ChartSpec:
    if not filters:
        return chart
    options = dict(chart.options)
    options["filters"] = filters
    return replace(chart, options=options)
