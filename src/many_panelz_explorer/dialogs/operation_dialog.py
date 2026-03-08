from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..operations import OperationRequest

if TYPE_CHECKING:
    from ..settings import UiPreferences


@dataclass(frozen=True)
class OperationDialogResult:
    backend_id: str
    dispatch_mode: str
    conflict_policy: str
    backend_options: dict[str, str]


class OperationDialog(QDialog):
    def __init__(
        self,
        *,
        kind: str,
        sources: list[Path],
        target_dir: Path | None,
        preferences: UiPreferences,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._kind = str(kind)
        self._preferences = preferences
        self._sources = list(sources)
        self._target_dir = target_dir
        self._result = OperationDialogResult(
            backend_id=(
                preferences.default_delete_backend
                if self._kind == "delete"
                else preferences.default_copy_move_backend
            ),
            dispatch_mode=preferences.default_operation_dispatch_mode,
            conflict_policy=preferences.default_operation_conflict_policy,
            backend_options={},
        )

        self.setWindowTitle("Configure Operation")
        self.resize(560, 320)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        summary = QLabel(self._summary_text(), self)
        summary.setWordWrap(True)
        summary.setTextFormat(Qt.TextFormat.PlainText)
        root.addWidget(summary)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.backend_combo = QComboBox(self)
        for label, value in self._backend_options():
            self.backend_combo.addItem(label, value)
        self._set_combo_data(self.backend_combo, self._result.backend_id)
        self.backend_combo.currentIndexChanged.connect(self._sync_backend_options_visibility)
        form.addRow("Backend", self.backend_combo)

        self.dispatch_combo = QComboBox(self)
        self.dispatch_combo.addItem("Queue", "queue")
        self.dispatch_combo.addItem("Launch Now (No Wait)", "launch_now_no_wait")
        self.dispatch_combo.addItem("Run Now (Wait)", "run_now_wait")
        self._set_combo_data(self.dispatch_combo, self._result.dispatch_mode)
        form.addRow("Dispatch", self.dispatch_combo)

        self.conflict_combo = QComboBox(self)
        self.conflict_combo.addItem("Overwrite", "overwrite")
        self.conflict_combo.addItem("Skip", "skip")
        self.conflict_combo.addItem("Rename", "rename")
        self.conflict_combo.addItem("Cancel", "cancel")
        self._set_combo_data(self.conflict_combo, self._result.conflict_policy)
        self.conflict_combo.setEnabled(self._kind in {"copy", "move"})
        form.addRow("Conflict Policy", self.conflict_combo)

        root.addLayout(form)

        self._backend_options_host = QWidget(self)
        self._backend_options_layout = QGridLayout(self._backend_options_host)
        self._backend_options_layout.setContentsMargins(0, 0, 0, 0)
        self._backend_options_layout.setHorizontalSpacing(8)
        self._backend_options_layout.setVerticalSpacing(6)

        self.robocopy_include_subdirs_checkbox = QCheckBox("Copy subdirectories (/E)", self)
        self.robocopy_include_subdirs_checkbox.setChecked(True)
        self.robocopy_no_retry_checkbox = QCheckBox("No retries (/R:0 /W:0)", self)
        self.robocopy_no_retry_checkbox.setChecked(True)
        self.robocopy_quiet_checkbox = QCheckBox("Quiet logs (/NFL /NDL /NJH /NJS /NP)", self)
        self.robocopy_quiet_checkbox.setChecked(True)
        self.robocopy_mirror_checkbox = QCheckBox("Mirror target (/MIR)", self)
        self.robocopy_mirror_checkbox.setChecked(False)
        self.robocopy_move_checkbox = QCheckBox("Move files (/MOVE)", self)
        self.robocopy_move_checkbox.setChecked(self._kind == "move")
        self.robocopy_move_checkbox.setEnabled(self._kind == "move")

        self.tool_extra_args_label = QLabel("Extra tool args", self)
        self.tool_extra_args_edit = QLineEdit(self)
        self.tool_extra_args_edit.setPlaceholderText("Optional args appended to command")

        self._backend_options_layout.addWidget(self.robocopy_include_subdirs_checkbox, 0, 0, 1, 2)
        self._backend_options_layout.addWidget(self.robocopy_no_retry_checkbox, 1, 0, 1, 2)
        self._backend_options_layout.addWidget(self.robocopy_quiet_checkbox, 2, 0, 1, 2)
        self._backend_options_layout.addWidget(self.robocopy_mirror_checkbox, 3, 0, 1, 2)
        self._backend_options_layout.addWidget(self.robocopy_move_checkbox, 4, 0, 1, 2)
        self._backend_options_layout.addWidget(self.tool_extra_args_label, 5, 0)
        self._backend_options_layout.addWidget(self.tool_extra_args_edit, 5, 1)
        root.addWidget(self._backend_options_host)
        self._sync_backend_options_visibility()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    def _summary_text(self) -> str:
        lines: list[str] = []
        lines.append(f"Operation: {self._kind}")
        lines.append(f"Items: {len(self._sources)}")
        lines.extend(str(source) for source in self._sources[:5])
        if len(self._sources) > 5:
            lines.append(f"... +{len(self._sources) - 5} more")
        if self._target_dir is not None:
            lines.append(f"Target: {self._target_dir}")
        return "\n".join(lines)

    def _backend_options(self) -> list[tuple[str, str]]:
        if self._kind == "delete":
            return [
                ("Recycle Bin", "recycle_bin"),
                ("Permanent Native", "permanent_native"),
                ("cmd Delete", "cmd_delete"),
                ("PowerShell Delete", "powershell_delete"),
                ("rimraf", "rimraf"),
                ("External Delete", "external_delete"),
            ]
        return [
            ("Python Built-in", "python_builtin"),
            ("Windows Explorer", "windows_explorer"),
            ("Robocopy", "robocopy"),
            ("TeraCopy", "teracopy"),
            ("Unstoppable Copier", "unstoppable"),
            ("External Command", "external_copymove"),
        ]

    def _set_combo_data(self, combo: QComboBox, target_data: str) -> None:
        for index in range(combo.count()):
            if str(combo.itemData(index)) == str(target_data):
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _sync_backend_options_visibility(self) -> None:
        backend = str(self.backend_combo.currentData() or "")
        show_robocopy = backend == "robocopy" and self._kind in {"copy", "move"}
        show_extra_args = backend in {"teracopy", "unstoppable", "external_copymove"}
        self.robocopy_include_subdirs_checkbox.setVisible(show_robocopy)
        self.robocopy_no_retry_checkbox.setVisible(show_robocopy)
        self.robocopy_quiet_checkbox.setVisible(show_robocopy)
        self.robocopy_mirror_checkbox.setVisible(show_robocopy)
        self.robocopy_move_checkbox.setVisible(show_robocopy and self._kind == "move")
        self.tool_extra_args_label.setVisible(show_extra_args)
        self.tool_extra_args_edit.setVisible(show_extra_args)
        self._backend_options_host.setVisible(show_robocopy or show_extra_args)

    def _collect_backend_options(self) -> dict[str, str]:
        backend = str(self.backend_combo.currentData() or "")
        options: dict[str, str] = {}
        if backend == "robocopy" and self._kind in {"copy", "move"}:
            robocopy_parts: list[str] = []
            if self.robocopy_include_subdirs_checkbox.isChecked():
                robocopy_parts.append("/E")
            if self.robocopy_no_retry_checkbox.isChecked():
                robocopy_parts.extend(["/R:0", "/W:0"])
            if self.robocopy_quiet_checkbox.isChecked():
                robocopy_parts.extend(["/NFL", "/NDL", "/NJH", "/NJS", "/NP"])
            if self.robocopy_mirror_checkbox.isChecked():
                robocopy_parts.append("/MIR")
            if self._kind == "move" and self.robocopy_move_checkbox.isChecked():
                robocopy_parts.append("/MOVE")
            options["robocopy_args"] = " ".join(robocopy_parts)
        if backend in {"teracopy", "unstoppable", "external_copymove"}:
            extra_args = self.tool_extra_args_edit.text().strip()
            if extra_args:
                options["extra_args"] = extra_args
        return options

    def selected_result(self) -> OperationDialogResult:
        return OperationDialogResult(
            backend_id=str(self.backend_combo.currentData()),
            dispatch_mode=str(self.dispatch_combo.currentData()),
            conflict_policy=str(self.conflict_combo.currentData()),
            backend_options=self._collect_backend_options(),
        )

    def build_request(self, *, kind: str, sources: list[Path], target_dir: Path | None, created_by: str) -> OperationRequest:
        selection = self.selected_result()
        return OperationRequest(
            kind=kind,
            sources=tuple(sources),
            target_dir=target_dir,
            backend_id=selection.backend_id,
            dispatch_mode=selection.dispatch_mode,
            conflict_policy=selection.conflict_policy,
            backend_options=selection.backend_options,
            created_by=created_by,
        )
