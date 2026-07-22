"""Lightweight report template editor (V1 — not full designer)."""

from __future__ import annotations

from pathlib import Path
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from prism_bi.application.use_cases.export_data import (
    delete_report_template,
    export_report,
    save_report_template,
)
from prism_bi.presentation.widgets.page_header import PageHeader
from prism_bi_sdk.dto.report import ReportSectionSpec, ReportTemplate

if TYPE_CHECKING:
    from prism_bi.bootstrap.container import AppContainer


class ReportsView(QWidget):
    """Compose template-based reports from charts/datasets, then export via plugins."""

    def __init__(self, container: AppContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self.setObjectName("ReportsView")
        self._editing_id: UUID | None = None
        self._sections: list[ReportSectionSpec] = []

        root = QHBoxLayout(self)
        shell = QVBoxLayout()
        shell.addWidget(
            PageHeader(
                "Reports",
                "Template-based reports with chart and dataset sections — export via plugins.",
            )
        )
        body = QHBoxLayout()
        shell.addLayout(body)
        root.addLayout(shell)

        left = QVBoxLayout()
        left.addWidget(QLabel("Report templates"))
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        left.addWidget(self._list)
        btn_row = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(new_btn)
        btn_row.addWidget(del_btn)
        left.addLayout(btn_row)
        body.addLayout(left, stretch=1)

        form_host = QWidget()
        form = QFormLayout(form_host)
        self._title = QLineEdit()
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(80)
        form.addRow("Title", self._title)
        form.addRow("Notes", self._notes)

        add_row = QHBoxLayout()
        self._section_kind = QComboBox()
        self._section_kind.addItems(["heading", "notes", "chart", "dataset"])
        self._section_ref = QComboBox()
        self._section_title = QLineEdit()
        self._section_title.setPlaceholderText("Section title")
        add_btn = QPushButton("Add section")
        add_btn.clicked.connect(self._add_section)
        add_row.addWidget(self._section_kind)
        add_row.addWidget(self._section_ref, stretch=1)
        add_row.addWidget(self._section_title)
        add_row.addWidget(add_btn)
        form.addRow("Add", add_row)

        self._section_list = QListWidget()
        form.addRow("Sections", self._section_list)

        actions = QHBoxLayout()
        save_btn = QPushButton("Save template")
        save_btn.clicked.connect(self._save)
        export_btn = QPushButton("Export PDF…")
        export_btn.clicked.connect(self._export_pdf)
        actions.addWidget(save_btn)
        actions.addWidget(export_btn)
        form.addRow(actions)
        body.addWidget(form_host, stretch=2)

        self._section_kind.currentTextChanged.connect(self._reload_refs)
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        self._reload_refs()
        session = self._container.workspace
        if not session.is_open or session.project is None:
            return
        for report in session.project.reports:
            item = QListWidgetItem(report.title)
            item.setData(256, str(report.id))
            self._list.addItem(item)

    def _reload_refs(self) -> None:
        self._section_ref.clear()
        project = self._container.workspace.project
        if project is None:
            return
        kind = self._section_kind.currentText()
        if kind == "chart":
            for chart in project.charts:
                self._section_ref.addItem(chart.title, str(chart.id))
        elif kind == "dataset":
            for dataset in project.datasets:
                self._section_ref.addItem(dataset.alias, str(dataset.id))
        else:
            self._section_ref.addItem("(text)", "")

    def _new(self) -> None:
        self._editing_id = None
        self._title.clear()
        self._notes.clear()
        self._sections = []
        self._section_list.clear()

    def _add_section(self) -> None:
        kind = self._section_kind.currentText()
        title = self._section_title.text().strip()
        ref = self._section_ref.currentData()
        chart_id = UUID(str(ref)) if kind == "chart" and ref else None
        dataset_id = UUID(str(ref)) if kind == "dataset" and ref else None
        body = title if kind in {"heading", "notes"} else ""
        section = ReportSectionSpec(
            kind=kind,
            title=title,
            body=body,
            chart_id=chart_id,
            dataset_id=dataset_id,
        )
        self._sections.append(section)
        self._section_list.addItem(f"{kind}: {title or ref or '(empty)'}")
        self._section_title.clear()

    def _build_template(self) -> ReportTemplate | None:
        title = self._title.text().strip()
        if not title:
            QMessageBox.warning(self, "Report", "Enter a title.")
            return None
        return ReportTemplate(
            id=self._editing_id or uuid4(),
            title=title,
            notes=self._notes.toPlainText().strip(),
            sections=tuple(self._sections),
        )

    def _save(self) -> None:
        template = self._build_template()
        if template is None:
            return
        result = save_report_template(self._container.workspace, template)
        if not result.success:
            QMessageBox.critical(self, "Save report", result.message or "Failed")
            return
        self._editing_id = template.id
        self.refresh()

    def _delete(self) -> None:
        if self._editing_id is None:
            return
        result = delete_report_template(self._container.workspace, self._editing_id)
        if not result.success:
            QMessageBox.critical(self, "Delete report", result.message or "Failed")
            return
        self._new()
        self.refresh()

    def _export_pdf(self) -> None:
        template = self._build_template()
        if template is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "report.pdf", "PDF (*.pdf)")
        if not path:
            return
        result = export_report(
            self._container.workspace,
            self._container.export_builder,
            self._container.exporters,
            template=template,
            format_id="pdf",
            destination=Path(path),
        )
        if not result.success:
            QMessageBox.critical(self, "Export PDF", result.message or "Failed")
            return
        QMessageBox.information(self, "Export PDF", f"Saved {result.value}")

    def _on_select(self, row: int) -> None:
        if row < 0:
            return
        item = self._list.item(row)
        assert item is not None
        project = self._container.workspace.project
        if project is None:
            return
        report = project.get_report(UUID(str(item.data(256))))
        if report is None:
            return
        self._editing_id = report.id
        self._title.setText(report.title)
        self._notes.setPlainText(report.notes)
        self._sections = list(report.sections)
        self._section_list.clear()
        for section in self._sections:
            label = (
                section.title or (str(section.chart_id or section.dataset_id or section.body)[:40])
            )
            self._section_list.addItem(f"{section.kind}: {label}")
