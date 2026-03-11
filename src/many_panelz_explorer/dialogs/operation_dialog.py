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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .._operations.types import OperationRequest

if TYPE_CHECKING:
    from .._settings.models import UiPreferences


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
        self._backend_options_layout = QVBoxLayout(self._backend_options_host)
        self._backend_options_layout.setContentsMargins(0, 0, 0, 0)
        self._backend_options_layout.setSpacing(8)

        self.robocopy_options_group = QWidget(self._backend_options_host)
        robocopy_layout = QGridLayout(self.robocopy_options_group)
        robocopy_layout.setContentsMargins(0, 0, 0, 0)
        robocopy_layout.setHorizontalSpacing(8)
        robocopy_layout.setVerticalSpacing(6)
        self.robocopy_include_subdirs_checkbox = QCheckBox("Copy subdirectories (/E)", self)
        self.robocopy_include_subdirs_checkbox.setChecked(True)
        self.robocopy_mirror_checkbox = QCheckBox("Mirror target (/MIR)", self)
        self.robocopy_mirror_checkbox.setChecked(False)
        self.robocopy_move_checkbox = QCheckBox("Move files (/MOVE)", self)
        self.robocopy_move_checkbox.setChecked(self._kind == "move")
        self.robocopy_move_checkbox.setEnabled(self._kind == "move")
        self.robocopy_restartable_checkbox = QCheckBox("Restartable mode (/Z)", self)
        self.robocopy_restartable_checkbox.setChecked(False)
        self.robocopy_backup_mode_checkbox = QCheckBox("Backup mode (/B)", self)
        self.robocopy_backup_mode_checkbox.setChecked(False)
        self.robocopy_list_only_checkbox = QCheckBox("List only dry-run (/L)", self)
        self.robocopy_list_only_checkbox.setChecked(False)
        self.robocopy_quiet_checkbox = QCheckBox(
            "Suppress detailed logs (/NFL /NDL /NJH /NJS /NP)",
            self,
        )
        # Default is verbose.
        self.robocopy_quiet_checkbox.setChecked(False)

        self.robocopy_retry_spin = QSpinBox(self)
        self.robocopy_retry_spin.setRange(0, 1_000_000)
        self.robocopy_retry_spin.setValue(0)
        self.robocopy_wait_spin = QSpinBox(self)
        self.robocopy_wait_spin.setRange(0, 3600)
        self.robocopy_wait_spin.setValue(0)
        self.robocopy_multithread_checkbox = QCheckBox("Multi-threaded copy (/MT)", self)
        self.robocopy_multithread_checkbox.setChecked(False)
        self.robocopy_multithread_spin = QSpinBox(self)
        self.robocopy_multithread_spin.setRange(1, 128)
        self.robocopy_multithread_spin.setValue(8)
        self.robocopy_multithread_spin.setEnabled(False)
        self.robocopy_multithread_checkbox.toggled.connect(
            self.robocopy_multithread_spin.setEnabled
        )
        self.robocopy_extra_args_edit = QLineEdit(self)
        self.robocopy_extra_args_edit.setPlaceholderText("Additional Robocopy args")

        robocopy_layout.addWidget(self.robocopy_include_subdirs_checkbox, 0, 0, 1, 2)
        robocopy_layout.addWidget(self.robocopy_mirror_checkbox, 1, 0, 1, 2)
        robocopy_layout.addWidget(self.robocopy_move_checkbox, 2, 0, 1, 2)
        robocopy_layout.addWidget(self.robocopy_restartable_checkbox, 3, 0, 1, 2)
        robocopy_layout.addWidget(self.robocopy_backup_mode_checkbox, 4, 0, 1, 2)
        robocopy_layout.addWidget(self.robocopy_list_only_checkbox, 5, 0, 1, 2)
        robocopy_layout.addWidget(self.robocopy_quiet_checkbox, 6, 0, 1, 2)
        robocopy_layout.addWidget(QLabel("Retry count (/R)", self), 7, 0)
        robocopy_layout.addWidget(self.robocopy_retry_spin, 7, 1)
        robocopy_layout.addWidget(QLabel("Wait seconds (/W)", self), 8, 0)
        robocopy_layout.addWidget(self.robocopy_wait_spin, 8, 1)
        robocopy_layout.addWidget(self.robocopy_multithread_checkbox, 9, 0)
        robocopy_layout.addWidget(self.robocopy_multithread_spin, 9, 1)
        robocopy_layout.addWidget(QLabel("Extra args", self), 10, 0)
        robocopy_layout.addWidget(self.robocopy_extra_args_edit, 10, 1)
        robocopy_layout.setColumnStretch(1, 1)

        self.teracopy_options_group = QWidget(self._backend_options_host)
        teracopy_layout = QGridLayout(self.teracopy_options_group)
        teracopy_layout.setContentsMargins(0, 0, 0, 0)
        teracopy_layout.setHorizontalSpacing(8)
        teracopy_layout.setVerticalSpacing(6)
        self.teracopy_close_checkbox = QCheckBox("Close on completion (/Close)", self)
        self.teracopy_no_close_checkbox = QCheckBox("Keep window open (/NoClose)", self)
        self.teracopy_close_checkbox.toggled.connect(self._on_teracopy_close_toggled)
        self.teracopy_no_close_checkbox.toggled.connect(
            self._on_teracopy_no_close_toggled
        )
        self.teracopy_conflict_combo = QComboBox(self)
        self.teracopy_conflict_combo.addItem("No explicit override", "")
        self.teracopy_conflict_combo.addItem("Overwrite All", "/OverwriteAll")
        self.teracopy_conflict_combo.addItem("Skip All", "/SkipAll")
        self.teracopy_conflict_combo.addItem("Rename All", "/RenameAll")
        self.teracopy_conflict_combo.addItem("Overwrite Older", "/OverwriteOlder")
        self.teracopy_conflict_combo.addItem("Overwrite Different Size", "/OverwriteDiffSize")
        self.teracopy_conflict_combo.addItem("Rename Copied", "/RenameCopied")
        self.teracopy_conflict_combo.addItem(
            "Rename Destination",
            "/RenameDestination",
        )
        self.teracopy_extra_args_edit = QLineEdit(self)
        self.teracopy_extra_args_edit.setPlaceholderText("Additional TeraCopy args")
        teracopy_layout.addWidget(self.teracopy_close_checkbox, 0, 0, 1, 2)
        teracopy_layout.addWidget(self.teracopy_no_close_checkbox, 1, 0, 1, 2)
        teracopy_layout.addWidget(QLabel("Conflict override", self), 2, 0)
        teracopy_layout.addWidget(self.teracopy_conflict_combo, 2, 1)
        teracopy_layout.addWidget(QLabel("Extra args", self), 3, 0)
        teracopy_layout.addWidget(self.teracopy_extra_args_edit, 3, 1)
        teracopy_layout.setColumnStretch(1, 1)

        self.unstoppable_options_group = QWidget(self._backend_options_host)
        unstoppable_layout = QGridLayout(self.unstoppable_options_group)
        unstoppable_layout.setContentsMargins(0, 0, 0, 0)
        unstoppable_layout.setHorizontalSpacing(8)
        unstoppable_layout.setVerticalSpacing(6)
        self.unstoppable_defaults_checkbox = QCheckBox("Use program defaults (+d)", self)
        self.unstoppable_defaults_checkbox.setChecked(True)
        self.unstoppable_keep_attributes_checkbox = QCheckBox("Copy attributes (+a)", self)
        self.unstoppable_keep_attributes_checkbox.setChecked(True)
        self.unstoppable_keep_owner_checkbox = QCheckBox("Copy ownership (+o)", self)
        self.unstoppable_keep_owner_checkbox.setChecked(True)
        self.unstoppable_keep_time_checkbox = QCheckBox("Copy date/time (+t)", self)
        self.unstoppable_keep_time_checkbox.setChecked(True)
        self.unstoppable_overwrite_checkbox = QCheckBox("Overwrite existing (+e)", self)
        self.unstoppable_overwrite_checkbox.setChecked(True)
        self.unstoppable_include_subdirs_checkbox = QCheckBox("Include subfolders (+i)", self)
        self.unstoppable_include_subdirs_checkbox.setChecked(True)
        self.unstoppable_resume_checkbox = QCheckBox("Recover damaged and resume (+r)", self)
        self.unstoppable_resume_checkbox.setChecked(False)
        self.unstoppable_copy_newer_checkbox = QCheckBox("Copy only if source newer (+c)", self)
        self.unstoppable_copy_newer_checkbox.setChecked(False)
        self.unstoppable_skip_damaged_checkbox = QCheckBox("Auto-skip damaged files (+s)", self)
        self.unstoppable_skip_damaged_checkbox.setChecked(False)
        self.unstoppable_undamaged_first_checkbox = QCheckBox("Undamaged files first (+u)", self)
        self.unstoppable_undamaged_first_checkbox.setChecked(False)
        self.unstoppable_overwrite_readonly_checkbox = QCheckBox("Overwrite read-only files (+w)", self)
        self.unstoppable_overwrite_readonly_checkbox.setChecked(False)
        self.unstoppable_copy_empty_folders_checkbox = QCheckBox("Copy empty folders (+f)", self)
        self.unstoppable_copy_empty_folders_checkbox.setChecked(False)
        self.unstoppable_eta_checkbox = QCheckBox("Show remaining time (+z)", self)
        self.unstoppable_eta_checkbox.setChecked(False)
        self.unstoppable_power_down_checkbox = QCheckBox("Power down after completion (+p)", self)
        self.unstoppable_power_down_checkbox.setChecked(False)
        self.unstoppable_extra_args_edit = QLineEdit(self)
        self.unstoppable_extra_args_edit.setPlaceholderText(
            "Additional Unstoppable Copier args"
        )

        unstoppable_layout.addWidget(self.unstoppable_defaults_checkbox, 0, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_keep_attributes_checkbox, 1, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_keep_owner_checkbox, 2, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_keep_time_checkbox, 3, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_overwrite_checkbox, 4, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_include_subdirs_checkbox, 5, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_resume_checkbox, 6, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_copy_newer_checkbox, 7, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_skip_damaged_checkbox, 8, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_undamaged_first_checkbox, 9, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_overwrite_readonly_checkbox, 10, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_copy_empty_folders_checkbox, 11, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_eta_checkbox, 12, 0, 1, 2)
        unstoppable_layout.addWidget(self.unstoppable_power_down_checkbox, 13, 0, 1, 2)
        unstoppable_layout.addWidget(QLabel("Extra args", self), 14, 0)
        unstoppable_layout.addWidget(self.unstoppable_extra_args_edit, 14, 1)
        unstoppable_layout.setColumnStretch(1, 1)

        self.external_options_group = QWidget(self._backend_options_host)
        external_layout = QHBoxLayout(self.external_options_group)
        external_layout.setContentsMargins(0, 0, 0, 0)
        external_layout.setSpacing(8)
        self.external_extra_args_edit = QLineEdit(self)
        self.external_extra_args_edit.setPlaceholderText(
            "Optional args appended to command"
        )
        external_layout.addWidget(QLabel("Extra args", self))
        external_layout.addWidget(self.external_extra_args_edit, 1)

        self._backend_options_layout.addWidget(self.robocopy_options_group)
        self._backend_options_layout.addWidget(self.teracopy_options_group)
        self._backend_options_layout.addWidget(self.unstoppable_options_group)
        self._backend_options_layout.addWidget(self.external_options_group)
        self._backend_options_layout.addStretch(1)
        self._load_robocopy_options_from_preferences()
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

    def _on_teracopy_close_toggled(self, checked: bool) -> None:
        if checked and self.teracopy_no_close_checkbox.isChecked():
            self.teracopy_no_close_checkbox.setChecked(False)

    def _on_teracopy_no_close_toggled(self, checked: bool) -> None:
        if checked and self.teracopy_close_checkbox.isChecked():
            self.teracopy_close_checkbox.setChecked(False)

    def _load_robocopy_options_from_preferences(self) -> None:
        raw = (
            self._preferences.robocopy_move_args
            if self._kind == "move"
            else self._preferences.robocopy_copy_args
        )
        tokens = [part.strip() for part in str(raw or "").split(" ") if part.strip()]
        if tokens:
            self.robocopy_include_subdirs_checkbox.setChecked(False)
            self.robocopy_mirror_checkbox.setChecked(False)
            if self._kind == "move":
                self.robocopy_move_checkbox.setChecked(False)
            self.robocopy_restartable_checkbox.setChecked(False)
            self.robocopy_backup_mode_checkbox.setChecked(False)
            self.robocopy_list_only_checkbox.setChecked(False)
            self.robocopy_quiet_checkbox.setChecked(False)
            self.robocopy_retry_spin.setValue(0)
            self.robocopy_wait_spin.setValue(0)
            self.robocopy_multithread_checkbox.setChecked(False)
            self.robocopy_multithread_spin.setValue(8)
            self.robocopy_extra_args_edit.setText("")
        quiet_flags = {"/NFL", "/NDL", "/NJH", "/NJS", "/NP"}
        seen_quiet: set[str] = set()
        extra_tokens: list[str] = []
        for token in tokens:
            upper = token.upper()
            if upper == "/E":
                self.robocopy_include_subdirs_checkbox.setChecked(True)
                continue
            if upper == "/MIR":
                self.robocopy_mirror_checkbox.setChecked(True)
                continue
            if upper == "/MOVE":
                if self._kind == "move":
                    self.robocopy_move_checkbox.setChecked(True)
                continue
            if upper == "/Z":
                self.robocopy_restartable_checkbox.setChecked(True)
                continue
            if upper == "/B":
                self.robocopy_backup_mode_checkbox.setChecked(True)
                continue
            if upper == "/L":
                self.robocopy_list_only_checkbox.setChecked(True)
                continue
            if upper.startswith("/R:"):
                try:
                    self.robocopy_retry_spin.setValue(max(0, int(upper.split(":", 1)[1])))
                except ValueError:
                    extra_tokens.append(token)
                continue
            if upper.startswith("/W:"):
                try:
                    self.robocopy_wait_spin.setValue(max(0, int(upper.split(":", 1)[1])))
                except ValueError:
                    extra_tokens.append(token)
                continue
            if upper.startswith("/MT:"):
                try:
                    value = int(upper.split(":", 1)[1])
                except ValueError:
                    extra_tokens.append(token)
                    continue
                self.robocopy_multithread_checkbox.setChecked(True)
                self.robocopy_multithread_spin.setValue(max(1, min(128, value)))
                continue
            if upper in quiet_flags:
                seen_quiet.add(upper)
                continue
            extra_tokens.append(token)
        self.robocopy_quiet_checkbox.setChecked(seen_quiet == quiet_flags)
        self.robocopy_extra_args_edit.setText(" ".join(extra_tokens))

    def _sync_backend_options_visibility(self) -> None:
        backend = str(self.backend_combo.currentData() or "")
        show_robocopy = backend == "robocopy" and self._kind in {"copy", "move"}
        show_teracopy = backend == "teracopy" and self._kind in {"copy", "move"}
        show_unstoppable = backend == "unstoppable" and self._kind in {"copy", "move"}
        show_external = backend == "external_copymove" and self._kind in {"copy", "move"}
        self.robocopy_options_group.setVisible(show_robocopy)
        self.teracopy_options_group.setVisible(show_teracopy)
        self.unstoppable_options_group.setVisible(show_unstoppable)
        self.external_options_group.setVisible(show_external)
        self._backend_options_host.setVisible(
            show_robocopy or show_teracopy or show_unstoppable or show_external
        )

    def _collect_robocopy_args(self) -> str:
        parts: list[str] = []
        if self.robocopy_include_subdirs_checkbox.isChecked():
            parts.append("/E")
        if self.robocopy_mirror_checkbox.isChecked():
            parts.append("/MIR")
        if self._kind == "move" and self.robocopy_move_checkbox.isChecked():
            parts.append("/MOVE")
        if self.robocopy_restartable_checkbox.isChecked():
            parts.append("/Z")
        if self.robocopy_backup_mode_checkbox.isChecked():
            parts.append("/B")
        if self.robocopy_list_only_checkbox.isChecked():
            parts.append("/L")
        parts.append(f"/R:{int(self.robocopy_retry_spin.value())}")
        parts.append(f"/W:{int(self.robocopy_wait_spin.value())}")
        if self.robocopy_multithread_checkbox.isChecked():
            parts.append(f"/MT:{int(self.robocopy_multithread_spin.value())}")
        if self.robocopy_quiet_checkbox.isChecked():
            parts.extend(["/NFL", "/NDL", "/NJH", "/NJS", "/NP"])
        extra = self.robocopy_extra_args_edit.text().strip()
        if extra:
            parts.extend(part for part in extra.split(" ") if part.strip())
        return " ".join(parts).strip()

    def _collect_teracopy_extra_args(self) -> str:
        parts: list[str] = []
        if self.teracopy_close_checkbox.isChecked():
            parts.append("/Close")
        if self.teracopy_no_close_checkbox.isChecked():
            parts.append("/NoClose")
        conflict_override = str(self.teracopy_conflict_combo.currentData() or "").strip()
        if conflict_override:
            parts.append(conflict_override)
        extra = self.teracopy_extra_args_edit.text().strip()
        if extra:
            parts.extend(part for part in extra.split(" ") if part.strip())
        return " ".join(parts).strip()

    def _collect_unstoppable_extra_args(self) -> str:
        flags: list[str] = []
        flag_map = [
            ("d", self.unstoppable_defaults_checkbox.isChecked()),
            ("a", self.unstoppable_keep_attributes_checkbox.isChecked()),
            ("o", self.unstoppable_keep_owner_checkbox.isChecked()),
            ("t", self.unstoppable_keep_time_checkbox.isChecked()),
            ("e", self.unstoppable_overwrite_checkbox.isChecked()),
            ("i", self.unstoppable_include_subdirs_checkbox.isChecked()),
            ("r", self.unstoppable_resume_checkbox.isChecked()),
            ("c", self.unstoppable_copy_newer_checkbox.isChecked()),
            ("s", self.unstoppable_skip_damaged_checkbox.isChecked()),
            ("u", self.unstoppable_undamaged_first_checkbox.isChecked()),
            ("w", self.unstoppable_overwrite_readonly_checkbox.isChecked()),
            ("f", self.unstoppable_copy_empty_folders_checkbox.isChecked()),
            ("z", self.unstoppable_eta_checkbox.isChecked()),
            ("p", self.unstoppable_power_down_checkbox.isChecked()),
        ]
        for code, enabled in flag_map:
            flags.append(f"+{code}" if enabled else f"-{code}")
        flags.append("+m" if self._kind == "move" else "-m")

        extra = self.unstoppable_extra_args_edit.text().strip()
        if extra:
            flags.extend(part for part in extra.split(" ") if part.strip())
        return " ".join(flags).strip()

    def _collect_backend_options(self) -> dict[str, str]:
        backend = str(self.backend_combo.currentData() or "")
        options: dict[str, str] = {}
        if backend == "robocopy" and self._kind in {"copy", "move"}:
            options["robocopy_args"] = self._collect_robocopy_args()
        elif backend == "teracopy" and self._kind in {"copy", "move"}:
            extra_args = self._collect_teracopy_extra_args()
            if extra_args:
                options["extra_args"] = extra_args
        elif backend == "unstoppable" and self._kind in {"copy", "move"}:
            extra_args = self._collect_unstoppable_extra_args()
            if extra_args:
                options["extra_args"] = extra_args
        elif backend == "external_copymove" and self._kind in {"copy", "move"}:
            extra_args = self.external_extra_args_edit.text().strip()
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
