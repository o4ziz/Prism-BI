"""Virtualized Qt table model backed by IAnalyticsStore windows."""

from __future__ import annotations

from uuid import UUID

import pyarrow as pa
from PySide6.QtCore import QAbstractTableModel, Qt

from prism_bi.application.ports.analytics import IAnalyticsStore


class RevisionTableModel(QAbstractTableModel):
    """Fetches row windows on demand — never loads the full table into Python."""

    def __init__(
        self,
        store: IAnalyticsStore,
        revision_id: UUID,
        *,
        window_size: int = 500,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self._store = store
        self._revision_id = revision_id
        self._window_size = window_size
        self._row_count = store.row_count(revision_id)
        self._columns = store.columns(revision_id)
        self._cache_start = -1
        self._cache_batch: pa.RecordBatch | None = None
        self._order_by: str | None = None
        self._descending = False

    def rowCount(self, parent=None) -> int:  # type: ignore[no-untyped-def]  # noqa: N802
        _ = parent
        return self._row_count

    def columnCount(self, parent=None) -> int:  # type: ignore[no-untyped-def]  # noqa: N802
        _ = parent
        return len(self._columns)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._columns):
                return self._columns[section].name
            return None
        return str(section + 1)

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole) -> object:  # type: ignore[no-untyped-def]  # noqa: N802
        if not index.isValid() or role not in {
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        }:
            return None
        row = index.row()
        col = index.column()
        batch = self._ensure_cache(row)
        if batch is None:
            return None
        local = row - self._cache_start
        if local < 0 or local >= batch.num_rows:
            return None
        value = batch.column(col)[local].as_py()
        return "" if value is None else str(value)

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if 0 <= column < len(self._columns):
            self._order_by = self._columns[column].name
            self._descending = order == Qt.SortOrder.DescendingOrder
            self._cache_start = -1
            self._cache_batch = None
            self.layoutChanged.emit()

    def _ensure_cache(self, row: int) -> pa.RecordBatch | None:
        if self._cache_batch is not None and (
            self._cache_start <= row < self._cache_start + self._cache_batch.num_rows
        ):
            return self._cache_batch
        start = (row // self._window_size) * self._window_size
        batch = self._store.fetch_window(
            self._revision_id,
            offset=start,
            limit=self._window_size,
            order_by=self._order_by,
            descending=self._descending,
        )
        self._cache_start = start
        self._cache_batch = batch
        return batch
