"""Job / task center dock widget."""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prism_bi_sdk.dto.job import JobHandle, JobState


class JobCenterWidget(QWidget):
    """Lists background jobs with progress and cancel support."""

    cancel_requested = Signal(object)  # UUID

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Task Center")
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Task Center")
        title.setObjectName("JobCenterTitle")
        header.addWidget(title)
        header.addStretch(1)
        self._cancel_btn = QPushButton("Cancel selected")
        self._cancel_btn.setObjectName("JobCenterCancel")
        self._cancel_btn.setAccessibleName("Cancel selected job")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        header.addWidget(self._cancel_btn)
        layout.addLayout(header)

        self._list = QListWidget()
        self._list.setObjectName("JobCenterList")
        self._list.setAccessibleName("Background jobs")
        self._list.currentItemChanged.connect(self._on_selection)
        layout.addWidget(self._list)
        self._items: dict[str, QListWidgetItem] = {}
        self._empty = QLabel("No background tasks yet.")
        self._empty.setObjectName("EmptyStateLabel")
        self._empty.setAccessibleName("No background tasks")
        layout.addWidget(self._empty)

    def update_job(self, handle: JobHandle) -> None:
        key = str(handle.id)
        progress = ""
        if handle.state == JobState.RUNNING:
            progress = f" — {handle.progress_percent:.0f}%"
            if handle.progress_message:
                progress += f" ({handle.progress_message})"
        elif handle.state == JobState.FAILED and handle.error:
            progress = f" — {handle.error[:80]}"
        text = f"{handle.name} — {handle.state.value}{progress}"
        if key in self._items:
            item = self._items[key]
            item.setText(text)
            item.setData(256, str(handle.id))
            item.setData(257, handle.state.value)
        else:
            item = QListWidgetItem(text)
            item.setData(256, str(handle.id))
            item.setData(257, handle.state.value)
            self._items[key] = item
            self._list.addItem(item)
        self._empty.setVisible(self._list.count() == 0)
        self._on_selection(self._list.currentItem(), None)

    def _on_selection(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._cancel_btn.setEnabled(False)
            return
        state = str(current.data(257) or "")
        self._cancel_btn.setEnabled(state in {JobState.PENDING.value, JobState.RUNNING.value})

    def _on_cancel(self) -> None:
        item = self._list.currentItem()
        assert item is not None
        raw = item.data(256)
        if raw is None:
            return
        self.cancel_requested.emit(UUID(str(raw)))
