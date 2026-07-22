"""PDF exporter using Qt QPdfWriter — no DuckDB / reportlab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QMarginsF, QPointF, QRectF
from PySide6.QtGui import QFont, QImage, QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.dto.export_artifact import ExportArtifact, ExportSection

_FORMATS = ("pdf",)


class PdfExporterPlugin:
    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.exporter.pdf",
            name="PDF Exporter",
            version="1.0.0",
            api_version=1,
            entry_module="prism_exporter_pdf.plugin",
            entry_class="PdfExporterPlugin",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.EXPORTERS,
                contribution_id="prism.exporter.pdf",
                factory=self,
                display_name="PDF",
                metadata={"formats": list(_FORMATS)},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context

    def deactivate(self) -> None:
        self._context = None

    def format_ids(self) -> tuple[str, ...]:
        return _FORMATS

    def supports(self, artifact: ExportArtifact, format_id: str) -> bool:
        return format_id == "pdf" and artifact.kind == "document"

    def export(
        self,
        artifact: ExportArtifact,
        destination: Path,
        *,
        format_id: str,
        options: dict[str, Any] | None = None,
    ) -> Path:
        _ = options
        if not self.supports(artifact, format_id):
            raise ValueError(f"Cannot export kind={artifact.kind} as {format_id}")
        if QApplication.instance() is None:
            raise RuntimeError("QApplication required for PDF export")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_pdf(artifact, destination)
        return destination.resolve()


def _write_pdf(artifact: ExportArtifact, path: Path) -> None:
    writer = QPdfWriter(str(path))
    writer.setTitle(artifact.title or "Prism BI Report")
    writer.setPageMargins(QMarginsF(36, 36, 36, 36))

    painter = QPainter(writer)
    page_rect = writer.pageLayout().paintRectPoints()
    y = float(page_rect.top())
    max_y = float(page_rect.bottom())
    left = float(page_rect.left())
    width = float(page_rect.width())

    title_font = QFont()
    title_font.setPointSize(16)
    title_font.setBold(True)
    body_font = QFont()
    body_font.setPointSize(10)
    heading_font = QFont()
    heading_font.setPointSize(13)
    heading_font.setBold(True)

    painter.setFont(title_font)
    painter.drawText(QPointF(left, y + 16), artifact.title or "Report")
    y += 32

    for section in artifact.sections:
        y = _draw_section(
            painter,
            writer,
            section,
            left=left,
            width=width,
            y=y,
            max_y=max_y,
            page_rect=page_rect,
            body_font=body_font,
            heading_font=heading_font,
        )

    painter.end()


def _draw_section(
    painter: QPainter,
    writer: QPdfWriter,
    section: ExportSection,
    *,
    left: float,
    width: float,
    y: float,
    max_y: float,
    page_rect: QRectF,
    body_font: QFont,
    heading_font: QFont,
) -> float:
    def advance_page(needed: float) -> float:
        nonlocal y
        if y + needed > max_y:
            writer.newPage()
            y = float(page_rect.top())
        return y

    if section.kind == "heading":
        y = advance_page(24)
        painter.setFont(heading_font)
        painter.drawText(QPointF(left, y + 14), section.title or section.text)
        return y + 28

    if section.kind == "text":
        painter.setFont(body_font)
        if section.title:
            y = advance_page(18)
            painter.drawText(QPointF(left, y + 12), section.title)
            y += 18
        text = section.text or ""
        line_height = 14.0
        chunk_size = max(40, int(width / 6))
        for start in range(0, len(text), chunk_size):
            y = advance_page(line_height)
            painter.drawText(QPointF(left, y + 12), text[start : start + chunk_size])
            y += line_height
        return y + 8

    if section.kind == "image" and section.image_png:
        image = QImage.fromData(section.image_png, "PNG")
        if image.isNull():
            return y
        if section.title:
            y = advance_page(18)
            painter.setFont(heading_font)
            painter.drawText(QPointF(left, y + 12), section.title)
            y += 20
        target_w = min(width, float(image.width()))
        scale = target_w / max(1.0, float(image.width()))
        target_h = float(image.height()) * scale
        max_h = max_y - y - 8
        if target_h > max_h and max_h < 120:
            writer.newPage()
            y = float(page_rect.top())
            max_h = max_y - y - 8
        if target_h > max_h:
            scale = max_h / max(1.0, float(image.height()))
            target_w = float(image.width()) * scale
            target_h = max_h
        rect = QRectF(left, y, target_w, target_h)
        painter.drawImage(rect, image)
        return y + target_h + 16

    if section.kind == "table" and section.table is not None:
        painter.setFont(body_font)
        if section.title:
            y = advance_page(18)
            painter.setFont(heading_font)
            painter.drawText(QPointF(left, y + 12), section.title)
            y += 20
            painter.setFont(body_font)
        table = section.table
        names = list(table.column_names)[:6]
        y = advance_page(16)
        painter.drawText(QPointF(left, y + 12), " | ".join(names))
        y += 16
        for row_idx in range(min(table.num_rows, 40)):
            y = advance_page(14)
            cells = []
            for name in names:
                value = table.column(name)[row_idx].as_py()
                cells.append("" if value is None else str(value))
            painter.drawText(QPointF(left, y + 12), " | ".join(cells)[:120])
            y += 14
        return y + 10

    return y
