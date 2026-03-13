"""Transfer-backend settings cards for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..._operations.types import DEFAULT_TERA_COPY_EXE
from ..._settings.manager import SettingsManager
from . import control_builders

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def build_robocopy_settings_card(dialog: SettingsDialog) -> QWidget:
    """Build the structured Robocopy settings card."""

    host = QWidget(dialog)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    grid = QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)
    dialog.robocopy_struct_include_subdirs_checkbox = QCheckBox(
        "Copy subdirectories (/E)",
        host,
    )
    dialog.robocopy_struct_mirror_checkbox = QCheckBox(
        "Mirror target (/MIR)",
        host,
    )
    dialog.robocopy_struct_move_checkbox = QCheckBox(
        "Move files for move (/MOVE)",
        host,
    )
    dialog.robocopy_struct_restartable_checkbox = QCheckBox(
        "Restartable mode (/Z)",
        host,
    )
    dialog.robocopy_struct_backup_checkbox = QCheckBox("Backup mode (/B)", host)
    dialog.robocopy_struct_list_only_checkbox = QCheckBox(
        "List only dry-run (/L)",
        host,
    )
    dialog.robocopy_struct_quiet_checkbox = QCheckBox(
        "Suppress detail logs (/NFL /NDL /NJH /NJS /NP)",
        host,
    )
    dialog.robocopy_struct_retry_spin = QSpinBox(host)
    dialog.robocopy_struct_retry_spin.setRange(0, 1_000_000)
    dialog.robocopy_struct_wait_spin = QSpinBox(host)
    dialog.robocopy_struct_wait_spin.setRange(0, 3_600)
    dialog.robocopy_struct_multithread_checkbox = QCheckBox(
        "Multi-threaded (/MT)",
        host,
    )
    dialog.robocopy_struct_multithread_spin = QSpinBox(host)
    dialog.robocopy_struct_multithread_spin.setRange(1, 128)
    dialog.robocopy_struct_extra_args_edit = QLineEdit(host)
    dialog.robocopy_struct_extra_args_edit.setPlaceholderText("Extra args")

    for widget in [
        dialog.robocopy_struct_include_subdirs_checkbox,
        dialog.robocopy_struct_mirror_checkbox,
        dialog.robocopy_struct_move_checkbox,
        dialog.robocopy_struct_restartable_checkbox,
        dialog.robocopy_struct_backup_checkbox,
        dialog.robocopy_struct_list_only_checkbox,
        dialog.robocopy_struct_quiet_checkbox,
        dialog.robocopy_struct_multithread_checkbox,
    ]:
        widget.toggled.connect(dialog.on_controls_changed)

    for widget in [
        dialog.robocopy_struct_retry_spin,
        dialog.robocopy_struct_wait_spin,
        dialog.robocopy_struct_multithread_spin,
    ]:
        widget.valueChanged.connect(dialog.on_controls_changed)
    dialog.robocopy_struct_extra_args_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    dialog.robocopy_struct_multithread_checkbox.toggled.connect(
        dialog.robocopy_struct_multithread_spin.setEnabled
    )

    grid.addWidget(dialog.robocopy_struct_include_subdirs_checkbox, 0, 0, 1, 2)
    grid.addWidget(dialog.robocopy_struct_mirror_checkbox, 1, 0, 1, 2)
    grid.addWidget(dialog.robocopy_struct_move_checkbox, 2, 0, 1, 2)
    grid.addWidget(dialog.robocopy_struct_restartable_checkbox, 3, 0, 1, 2)
    grid.addWidget(dialog.robocopy_struct_backup_checkbox, 4, 0, 1, 2)
    grid.addWidget(dialog.robocopy_struct_list_only_checkbox, 5, 0, 1, 2)
    grid.addWidget(dialog.robocopy_struct_quiet_checkbox, 6, 0, 1, 2)
    grid.addWidget(QLabel("Retry count (/R)", host), 7, 0)
    grid.addWidget(dialog.robocopy_struct_retry_spin, 7, 1)
    grid.addWidget(QLabel("Wait seconds (/W)", host), 8, 0)
    grid.addWidget(dialog.robocopy_struct_wait_spin, 8, 1)
    grid.addWidget(dialog.robocopy_struct_multithread_checkbox, 9, 0)
    grid.addWidget(dialog.robocopy_struct_multithread_spin, 9, 1)
    grid.addWidget(QLabel("Extra args", host), 10, 0)
    grid.addWidget(dialog.robocopy_struct_extra_args_edit, 10, 1)
    grid.addWidget(dialog.use_extended_paths_robocopy_checkbox, 11, 1)
    layout.addLayout(grid)

    dialog.robocopy_preview_label = control_builders.build_preview_label(dialog)
    layout.addWidget(dialog.robocopy_preview_label)

    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    dialog.robocopy_reset_backend_btn.clicked.connect(
        dialog.reset_robocopy_backend_defaults
    )
    dialog.robocopy_test_btn.clicked.connect(
        lambda: control_builders.backend_actions.test_backend(
            dialog,
            "copy",
            "robocopy",
        )
    )
    actions_layout.addWidget(dialog.robocopy_reset_backend_btn)
    actions_layout.addWidget(dialog.robocopy_test_btn)
    layout.addWidget(actions)
    return host


def build_teracopy_settings_card(dialog: SettingsDialog) -> QWidget:
    """Build the structured TeraCopy settings card."""

    host = QWidget(dialog)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(
        control_builders.build_backend_executable_controls(
            dialog,
            executable_edit=dialog.teracopy_executable_edit,
            default_executable=SettingsManager.DEFAULT_TERACOPY_EXECUTABLE,
            discover_default_executable=DEFAULT_TERA_COPY_EXE,
        )
    )

    grid = QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)
    dialog.teracopy_struct_close_checkbox = QCheckBox(
        "Close when done (/Close)",
        host,
    )
    dialog.teracopy_struct_keep_open_checkbox = QCheckBox(
        "Keep open (/NoClose)",
        host,
    )
    dialog.teracopy_struct_verify_checkbox = QCheckBox(
        "Verify after copy (/Verify)",
        host,
    )
    dialog.teracopy_struct_no_sound_checkbox = QCheckBox(
        "Disable sounds (/NoSound)",
        host,
    )
    dialog.teracopy_struct_conflict_combo = QComboBox(host)
    dialog.teracopy_struct_conflict_combo.addItem("No explicit override", "")
    dialog.teracopy_struct_conflict_combo.addItem("Overwrite All", "/OverwriteAll")
    dialog.teracopy_struct_conflict_combo.addItem("Skip All", "/SkipAll")
    dialog.teracopy_struct_conflict_combo.addItem("Rename All", "/RenameAll")
    dialog.teracopy_struct_conflict_combo.addItem(
        "Overwrite Older",
        "/OverwriteOlder",
    )
    dialog.teracopy_struct_conflict_combo.addItem(
        "Overwrite Different Size",
        "/OverwriteDiffSize",
    )
    dialog.teracopy_struct_conflict_combo.addItem(
        "Rename Copied",
        "/RenameCopied",
    )
    dialog.teracopy_struct_conflict_combo.addItem(
        "Rename Destination",
        "/RenameDestination",
    )
    dialog.teracopy_struct_extra_args_edit = QLineEdit(host)
    dialog.teracopy_struct_extra_args_edit.setPlaceholderText("Extra args")

    dialog.teracopy_struct_close_checkbox.toggled.connect(
        dialog.on_teracopy_struct_close_toggled
    )
    dialog.teracopy_struct_keep_open_checkbox.toggled.connect(
        dialog.on_teracopy_struct_keep_open_toggled
    )
    for widget in [
        dialog.teracopy_struct_verify_checkbox,
        dialog.teracopy_struct_no_sound_checkbox,
        dialog.use_extended_paths_teracopy_checkbox,
    ]:
        widget.toggled.connect(dialog.on_controls_changed)
    dialog.teracopy_struct_conflict_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    dialog.teracopy_struct_extra_args_edit.textChanged.connect(
        dialog.on_controls_changed
    )

    grid.addWidget(dialog.teracopy_struct_close_checkbox, 0, 0, 1, 2)
    grid.addWidget(dialog.teracopy_struct_keep_open_checkbox, 1, 0, 1, 2)
    grid.addWidget(dialog.teracopy_struct_verify_checkbox, 2, 0, 1, 2)
    grid.addWidget(dialog.teracopy_struct_no_sound_checkbox, 3, 0, 1, 2)
    grid.addWidget(QLabel("Conflict mode", host), 4, 0)
    grid.addWidget(dialog.teracopy_struct_conflict_combo, 4, 1)
    grid.addWidget(QLabel("Extra args", host), 5, 0)
    grid.addWidget(dialog.teracopy_struct_extra_args_edit, 5, 1)
    grid.addWidget(dialog.use_extended_paths_teracopy_checkbox, 6, 1)
    grid.setColumnStretch(1, 1)
    layout.addLayout(grid)

    dialog.teracopy_preview_label = control_builders.build_preview_label(dialog)
    layout.addWidget(dialog.teracopy_preview_label)

    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    dialog.teracopy_reset_backend_btn.clicked.connect(
        dialog.reset_teracopy_backend_defaults
    )
    dialog.teracopy_test_btn.clicked.connect(
        lambda: control_builders.backend_actions.test_backend(
            dialog,
            "copy",
            "teracopy",
        )
    )
    actions_layout.addWidget(dialog.teracopy_reset_backend_btn)
    actions_layout.addWidget(dialog.teracopy_test_btn)
    layout.addWidget(actions)
    return host
