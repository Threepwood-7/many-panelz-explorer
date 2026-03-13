"""Qt models and widgets for the operation queue UI."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from . import file_ops
from ._operations.discovery import is_scripted_backend

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from ._operations.queue_manager import OperationQueueManager
    from ._operations.types import OperationJob


_HEADERS = [
    "ID",
    "Kind",
    "Backend",
    "Status",
    "Summary",
    "Message",
    "Created",
]

_DEFAULT_MODEL_INDEX = QModelIndex()


def _fmt_time(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone().strftime("%H:%M:%S")


class OperationQueueTableModel(QAbstractTableModel):
    """Expose queued operation jobs in a table-friendly model."""

    def __init__(
        self, manager: OperationQueueManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self._jobs: list[OperationJob] = manager.jobs()
        manager.job_added.connect(self._on_job_added)
        manager.job_updated.connect(self._on_job_updated)
        manager.jobs_reset.connect(self._on_jobs_reset)

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = _DEFAULT_MODEL_INDEX,
    ) -> int:
        _ = parent
        return len(self._jobs)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = _DEFAULT_MODEL_INDEX,
    ) -> int:
        _ = parent
        return len(_HEADERS)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if not index.isValid():
            return None
        if index.row() < 0 or index.row() >= len(self._jobs):
            return None
        job = self._jobs[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return job.job_id
        if role not in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return None
        column = index.column()
        if column == 0:
            return job.job_id[:8]
        if column == 1:
            return job.request.kind
        if column == 2:
            return job.request.backend_id
        if column == 3:
            return job.status
        if column == 4:
            return job.summary()
        if column == 5:
            return job.message
        if column == 6:
            return _fmt_time(job.created_at)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(_HEADERS):
                return _HEADERS[section]
            return None
        return str(section + 1)

    def job_id_at(self, row: int) -> str | None:
        if row < 0 or row >= len(self._jobs):
            return None
        return self._jobs[row].job_id

    def job_at(self, row: int) -> OperationJob | None:
        if row < 0 or row >= len(self._jobs):
            return None
        return self._jobs[row]

    def _on_job_added(self, job_obj: object) -> None:
        job = cast("OperationJob", job_obj)
        row = len(self._jobs)
        self.beginInsertRows(QModelIndex(), row, row)
        self._jobs.append(job)
        self.endInsertRows()

    def _on_job_updated(self, job_obj: object) -> None:
        job = cast("OperationJob", job_obj)
        for row, existing in enumerate(self._jobs):
            if existing.job_id != job.job_id:
                continue
            self._jobs[row] = replace(job)
            left = self.index(row, 0)
            right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(left, right)
            return

    def _on_jobs_reset(self) -> None:
        self.beginResetModel()
        self._jobs = self.manager.jobs()
        self.endResetModel()


class OperationQueuePanel(QWidget):
    """Render queue controls, job table, and artifact shortcuts."""

    def __init__(
        self,
        *,
        manager: OperationQueueManager,
        model: OperationQueueTableModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.model = model

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        self.title_label = QLabel("Operation Queue", self)
        root.addWidget(self.title_label)

        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)

        self.cancel_btn = QPushButton("Cancel", self)
        self.retry_btn = QPushButton("Retry", self)
        self.clear_btn = QPushButton("Clear Finished", self)
        self.open_script_btn = QPushButton("Open Script", self)
        self.open_log_btn = QPushButton("Open Log", self)
        self.open_metadata_btn = QPushButton("Open Metadata", self)
        controls.addWidget(self.cancel_btn)
        controls.addWidget(self.retry_btn)
        controls.addWidget(self.clear_btn)
        controls.addWidget(self.open_script_btn)
        controls.addWidget(self.open_log_btn)
        controls.addWidget(self.open_metadata_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        self.cancel_btn.clicked.connect(self._cancel_selected)
        self.retry_btn.clicked.connect(self._retry_selected)
        self.clear_btn.clicked.connect(self.manager.clear_finished)
        self.open_script_btn.clicked.connect(self._open_script)
        self.open_log_btn.clicked.connect(self._open_log)
        self.open_metadata_btn.clicked.connect(self._open_metadata)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.manager.job_updated.connect(self._on_job_signal)
        self.manager.job_added.connect(self._on_job_signal)
        self._sync_artifact_buttons()

    def selected_job_id(self) -> str | None:
        if not isValid(self) or not isValid(self.table):
            return None
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.job_id_at(row)

    def _cancel_selected(self) -> None:
        job_id = self.selected_job_id()
        if not job_id:
            return
        self.manager.cancel_job(job_id)

    def _retry_selected(self) -> None:
        job_id = self.selected_job_id()
        if not job_id:
            return
        self.manager.retry_job(job_id)

    def _selected_job(self) -> OperationJob | None:
        if not isValid(self) or not isValid(self.table):
            return None
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.model.job_at(indexes[0].row())

    def _on_selection_changed(self, *_args: object) -> None:
        self._sync_artifact_buttons()

    def _on_job_signal(self, _job: object) -> None:
        self._sync_artifact_buttons()

    def _artifact_path(self, artifact: str) -> Path | None:
        job = self._selected_job()
        if job is None or job.artifacts is None:
            return None
        if artifact == "script":
            if not is_scripted_backend(job.request.backend_id):
                return None
            script_path = job.artifacts.job_dir / "run.cmd"
            return script_path if script_path.exists() else None
        if artifact == "log":
            path = job.artifacts.log_path
            return path if path.exists() else None
        if artifact == "metadata":
            path = job.artifacts.metadata_path
            return path if path.exists() else None
        return None

    def _sync_artifact_buttons(self) -> None:
        if not isValid(self):
            return
        if not isValid(self.open_script_btn) or not isValid(self.table):
            return
        self.open_script_btn.setEnabled(self._artifact_path("script") is not None)
        self.open_log_btn.setEnabled(self._artifact_path("log") is not None)
        self.open_metadata_btn.setEnabled(self._artifact_path("metadata") is not None)

    def _open_artifact(self, kind: str) -> None:
        path = self._artifact_path(kind)
        if path is None:
            return
        try:
            if kind == "script":
                file_ops.open_in_text_editor(
                    path,
                    editor_executable=self.manager.preferences.default_editor_executable,
                )
            else:
                file_ops.open_with_default(path)
        except Exception as exc:
            QMessageBox.warning(self, "Open Artifact Failed", str(exc))

    def _open_script(self) -> None:
        self._open_artifact("script")

    def _open_log(self) -> None:
        self._open_artifact("log")

    def _open_metadata(self) -> None:
        self._open_artifact("metadata")
