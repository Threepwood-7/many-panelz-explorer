"""Operation configuration dialog with backend-specific option controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .._operations.backend_options import (
    UnstoppableBackendOptions,
    generate_unstoppable_switch_args,
)
from .._operations.types import OperationKind, OperationRequest
from ._operation_dialog_option_widgets import (
    build_external_options_group,
    build_robocopy_options_group,
    build_teracopy_options_group,
    build_unstoppable_options_group,
)

if TYPE_CHECKING:
    from pathlib import Path

    from .._operations.backend_options import (
        ExternalCopyMoveBackendOptions,
        RobocopyBackendOptions,
        TeraCopyBackendOptions,
    )
    from .._settings.models import UiPreferences


@dataclass(frozen=True)
class OperationDialogResult:
    """Capture the user's selected operation dialog settings."""

    backend_id: str
    dispatch_mode: str
    conflict_policy: str
    backend_options: dict[str, str]


class OperationDialog(QDialog):
    """Collect backend-specific settings for a copy, move, or delete request."""

    def __init__(
        self,
        *,
        kind: OperationKind,
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
        self.backend_combo.currentIndexChanged.connect(
            self._sync_backend_options_visibility
        )
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
        self._bind_backend_option_widgets()

        self._backend_options_layout.addWidget(self.robocopy_options_group)
        self._backend_options_layout.addWidget(self.teracopy_options_group)
        self._backend_options_layout.addWidget(self.unstoppable_options_group)
        self._backend_options_layout.addWidget(self.external_options_group)
        self._backend_options_layout.addStretch(1)
        self._load_backend_options_from_preferences()
        root.addWidget(self._backend_options_host)
        self._sync_backend_options_visibility()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    def _bind_backend_option_widgets(self) -> None:
        """Create backend-specific option widgets and expose them on the dialog."""
        robocopy = build_robocopy_options_group(
            self._backend_options_host,
            kind=self._kind,
        )
        self.robocopy_options_group = robocopy.group
        self.robocopy_include_subdirs_checkbox = robocopy.include_subdirs_checkbox
        self.robocopy_mirror_checkbox = robocopy.mirror_checkbox
        self.robocopy_move_checkbox = robocopy.move_checkbox
        self.robocopy_restartable_checkbox = robocopy.restartable_checkbox
        self.robocopy_backup_mode_checkbox = robocopy.backup_mode_checkbox
        self.robocopy_list_only_checkbox = robocopy.list_only_checkbox
        self.robocopy_quiet_checkbox = robocopy.quiet_checkbox
        self.robocopy_retry_spin = robocopy.retry_spin
        self.robocopy_wait_spin = robocopy.wait_spin
        self.robocopy_multithread_checkbox = robocopy.multithread_checkbox
        self.robocopy_multithread_spin = robocopy.multithread_spin
        self.robocopy_extra_args_edit = robocopy.extra_args_edit

        teracopy = build_teracopy_options_group(self._backend_options_host)
        self.teracopy_options_group = teracopy.group
        self.teracopy_close_checkbox = teracopy.close_checkbox
        self.teracopy_no_close_checkbox = teracopy.no_close_checkbox
        self.teracopy_conflict_combo = teracopy.conflict_combo
        self.teracopy_extra_args_edit = teracopy.extra_args_edit
        self.teracopy_close_checkbox.toggled.connect(self._on_teracopy_close_toggled)
        self.teracopy_no_close_checkbox.toggled.connect(
            self._on_teracopy_no_close_toggled
        )

        unstoppable = build_unstoppable_options_group(self._backend_options_host)
        self.unstoppable_options_group = unstoppable.group
        self.unstoppable_defaults_checkbox = unstoppable.defaults_checkbox
        self.unstoppable_keep_attributes_checkbox = unstoppable.keep_attributes_checkbox
        self.unstoppable_keep_owner_checkbox = unstoppable.keep_owner_checkbox
        self.unstoppable_keep_time_checkbox = unstoppable.keep_time_checkbox
        self.unstoppable_overwrite_checkbox = unstoppable.overwrite_checkbox
        self.unstoppable_include_subdirs_checkbox = unstoppable.include_subdirs_checkbox
        self.unstoppable_resume_checkbox = unstoppable.resume_checkbox
        self.unstoppable_copy_newer_checkbox = unstoppable.copy_newer_checkbox
        self.unstoppable_skip_damaged_checkbox = unstoppable.skip_damaged_checkbox
        self.unstoppable_undamaged_first_checkbox = unstoppable.undamaged_first_checkbox
        self.unstoppable_overwrite_readonly_checkbox = (
            unstoppable.overwrite_readonly_checkbox
        )
        self.unstoppable_copy_empty_folders_checkbox = (
            unstoppable.copy_empty_folders_checkbox
        )
        self.unstoppable_eta_checkbox = unstoppable.eta_checkbox
        self.unstoppable_power_down_checkbox = unstoppable.power_down_checkbox
        self.unstoppable_extra_args_edit = unstoppable.extra_args_edit

        external = build_external_options_group(self._backend_options_host)
        self.external_options_group = external.group
        self.external_extra_args_edit = external.extra_args_edit

    def _summary_text(self) -> str:
        """Return the dialog summary text for the selected sources."""
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
        """Return the available backends for the current operation kind."""
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
        """Select a combo item by its stored data value."""
        for index in range(combo.count()):
            if str(combo.itemData(index)) == str(target_data):
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _on_teracopy_close_toggled(self, checked: bool) -> None:
        """Keep `/Close` and `/NoClose` mutually exclusive."""
        if checked and self.teracopy_no_close_checkbox.isChecked():
            self.teracopy_no_close_checkbox.setChecked(False)

    def _on_teracopy_no_close_toggled(self, checked: bool) -> None:
        """Keep `/NoClose` and `/Close` mutually exclusive."""
        if checked and self.teracopy_close_checkbox.isChecked():
            self.teracopy_close_checkbox.setChecked(False)

    def _load_backend_options_from_preferences(self) -> None:
        """Apply structured backend defaults from preferences to the controls."""
        self._apply_robocopy_structured_options_to_controls(
            self._preferences.robocopy_structured_options
        )
        self._apply_teracopy_structured_options_to_controls(
            self._preferences.teracopy_structured_options
        )
        self._apply_unstoppable_structured_options_to_controls(
            self._preferences.unstoppable_structured_options
        )
        self._apply_external_copymove_structured_options_to_controls(
            self._preferences.external_copymove_structured_options
        )

    def _apply_robocopy_structured_options_to_controls(
        self, options: RobocopyBackendOptions
    ) -> None:
        """Load stored Robocopy options into the dialog controls."""
        self.robocopy_include_subdirs_checkbox.setChecked(
            options.include_subdirectories
        )
        self.robocopy_mirror_checkbox.setChecked(options.mirror_target)
        if self._kind == "move":
            self.robocopy_move_checkbox.setChecked(options.move_files_for_move)
        self.robocopy_restartable_checkbox.setChecked(options.restartable_mode)
        self.robocopy_backup_mode_checkbox.setChecked(options.backup_mode)
        self.robocopy_list_only_checkbox.setChecked(options.list_only)
        self.robocopy_quiet_checkbox.setChecked(options.suppress_logs)
        self.robocopy_retry_spin.setValue(int(options.retry_count))
        self.robocopy_wait_spin.setValue(int(options.wait_seconds))
        self.robocopy_multithread_checkbox.setChecked(options.use_multithreading)
        self.robocopy_multithread_spin.setValue(int(options.multithread_count))
        self.robocopy_extra_args_edit.setText(str(options.extra_args or "").strip())

    def _apply_teracopy_structured_options_to_controls(
        self, options: TeraCopyBackendOptions
    ) -> None:
        """Load stored TeraCopy options into the dialog controls."""
        self.teracopy_close_checkbox.setChecked(options.close_on_finish)
        self.teracopy_no_close_checkbox.setChecked(options.keep_open)
        self._set_combo_data(self.teracopy_conflict_combo, options.conflict_mode)
        extra_parts: list[str] = []
        if options.verify_after_copy:
            extra_parts.append("/Verify")
        if options.no_sound:
            extra_parts.append("/NoSound")
        extra = str(options.extra_args or "").strip()
        if extra:
            extra_parts.append(extra)
        self.teracopy_extra_args_edit.setText(" ".join(extra_parts))

    def _apply_unstoppable_structured_options_to_controls(
        self, options: UnstoppableBackendOptions
    ) -> None:
        """Load stored Unstoppable Copier options into the dialog controls."""
        self.unstoppable_defaults_checkbox.setChecked(options.use_defaults)
        self.unstoppable_keep_attributes_checkbox.setChecked(options.keep_attributes)
        self.unstoppable_keep_owner_checkbox.setChecked(options.keep_owner)
        self.unstoppable_keep_time_checkbox.setChecked(options.keep_time)
        self.unstoppable_overwrite_checkbox.setChecked(options.overwrite_existing)
        self.unstoppable_include_subdirs_checkbox.setChecked(options.include_subfolders)
        self.unstoppable_resume_checkbox.setChecked(options.recover_and_resume)
        self.unstoppable_copy_newer_checkbox.setChecked(options.copy_newer_only)
        self.unstoppable_skip_damaged_checkbox.setChecked(options.skip_damaged)
        self.unstoppable_undamaged_first_checkbox.setChecked(options.undamaged_first)
        self.unstoppable_overwrite_readonly_checkbox.setChecked(
            options.overwrite_readonly
        )
        self.unstoppable_copy_empty_folders_checkbox.setChecked(
            options.copy_empty_folders
        )
        self.unstoppable_eta_checkbox.setChecked(options.show_eta)
        self.unstoppable_power_down_checkbox.setChecked(options.power_down_when_done)
        self.unstoppable_extra_args_edit.setText(str(options.extra_args or "").strip())

    def _apply_external_copymove_structured_options_to_controls(
        self, options: ExternalCopyMoveBackendOptions
    ) -> None:
        """Load stored external-command options into the dialog controls."""
        self.external_extra_args_edit.setText(str(options.extra_args or "").strip())

    def _sync_backend_options_visibility(self) -> None:
        """Show only the backend panel that applies to the current selection."""
        backend = str(self.backend_combo.currentData() or "")
        show_robocopy = backend == "robocopy" and self._kind in {"copy", "move"}
        show_teracopy = backend == "teracopy" and self._kind in {"copy", "move"}
        show_unstoppable = backend == "unstoppable" and self._kind in {"copy", "move"}
        show_external = backend == "external_copymove" and self._kind in {
            "copy",
            "move",
        }
        self.robocopy_options_group.setVisible(show_robocopy)
        self.teracopy_options_group.setVisible(show_teracopy)
        self.unstoppable_options_group.setVisible(show_unstoppable)
        self.external_options_group.setVisible(show_external)
        self._backend_options_host.setVisible(
            show_robocopy or show_teracopy or show_unstoppable or show_external
        )

    def _collect_robocopy_args(self) -> str:
        """Serialize the Robocopy controls back into command-line arguments."""
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
        """Serialize the TeraCopy controls back into extra arguments."""
        parts: list[str] = []
        if self.teracopy_close_checkbox.isChecked():
            parts.append("/Close")
        if self.teracopy_no_close_checkbox.isChecked():
            parts.append("/NoClose")
        conflict_override = str(
            self.teracopy_conflict_combo.currentData() or ""
        ).strip()
        if conflict_override:
            parts.append(conflict_override)
        extra = self.teracopy_extra_args_edit.text().strip()
        if extra:
            parts.extend(part for part in extra.split(" ") if part.strip())
        return " ".join(parts).strip()

    def _collect_unstoppable_extra_args(self) -> str:
        """Serialize the Unstoppable Copier controls back into switch args."""
        flags = generate_unstoppable_switch_args(
            UnstoppableBackendOptions(
                use_defaults=self.unstoppable_defaults_checkbox.isChecked(),
                keep_attributes=self.unstoppable_keep_attributes_checkbox.isChecked(),
                keep_owner=self.unstoppable_keep_owner_checkbox.isChecked(),
                keep_time=self.unstoppable_keep_time_checkbox.isChecked(),
                overwrite_existing=self.unstoppable_overwrite_checkbox.isChecked(),
                include_subfolders=self.unstoppable_include_subdirs_checkbox.isChecked(),
                recover_and_resume=self.unstoppable_resume_checkbox.isChecked(),
                copy_newer_only=self.unstoppable_copy_newer_checkbox.isChecked(),
                skip_damaged=self.unstoppable_skip_damaged_checkbox.isChecked(),
                undamaged_first=self.unstoppable_undamaged_first_checkbox.isChecked(),
                overwrite_readonly=self.unstoppable_overwrite_readonly_checkbox.isChecked(),
                copy_empty_folders=self.unstoppable_copy_empty_folders_checkbox.isChecked(),
                show_eta=self.unstoppable_eta_checkbox.isChecked(),
                power_down_when_done=self.unstoppable_power_down_checkbox.isChecked(),
            )
        )
        extra = self.unstoppable_extra_args_edit.text().strip()
        if extra:
            flags.extend(part for part in extra.split(" ") if part.strip())
        return " ".join(flags).strip()

    def _collect_backend_options(self) -> dict[str, str]:
        """Collect the backend-specific options for the active selection."""
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
        """Return the currently selected dialog values."""
        return OperationDialogResult(
            backend_id=str(self.backend_combo.currentData()),
            dispatch_mode=str(self.dispatch_combo.currentData()),
            conflict_policy=str(self.conflict_combo.currentData()),
            backend_options=self._collect_backend_options(),
        )

    def build_request(
        self,
        *,
        kind: OperationKind,
        sources: list[Path],
        target_dir: Path | None,
        created_by: str,
    ) -> OperationRequest:
        """Build an operation request from the current dialog selection."""
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
