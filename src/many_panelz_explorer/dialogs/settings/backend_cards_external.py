"""External transfer-backend settings cards for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..._operations.types import DEFAULT_UNSTOPPABLE_EXE
from ..._settings.manager import SettingsManager
from . import control_builders

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def build_unstoppable_settings_card(dialog: SettingsDialog) -> QWidget:
    """Build the structured Unstoppable Copier settings card."""

    host = QWidget(dialog)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(
        control_builders.build_backend_executable_controls(
            dialog,
            executable_edit=dialog.unstoppable_executable_edit,
            default_executable=SettingsManager.DEFAULT_UNSTOPPABLE_EXECUTABLE,
            discover_default_executable=DEFAULT_UNSTOPPABLE_EXE,
        )
    )
    grid = _build_unstoppable_options_grid(dialog, host)
    layout.addLayout(grid)
    dialog.unstoppable_preview_label = control_builders.build_preview_label(dialog)
    layout.addWidget(dialog.unstoppable_preview_label)
    layout.addWidget(_build_unstoppable_actions(dialog, host))
    return host


def _build_unstoppable_options_grid(
    dialog: SettingsDialog,
    host: QWidget,
) -> QGridLayout:
    """Build the Unstoppable Copier options grid."""

    grid = QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)
    dialog.unstoppable_struct_defaults_checkbox = QCheckBox(
        "Use defaults (+d)",
        host,
    )
    dialog.unstoppable_struct_keep_attributes_checkbox = QCheckBox(
        "Copy attributes (+a)",
        host,
    )
    dialog.unstoppable_struct_keep_owner_checkbox = QCheckBox(
        "Copy ownership (+o)",
        host,
    )
    dialog.unstoppable_struct_keep_time_checkbox = QCheckBox(
        "Copy date/time (+t)",
        host,
    )
    dialog.unstoppable_struct_overwrite_checkbox = QCheckBox(
        "Overwrite existing (+e)",
        host,
    )
    dialog.unstoppable_struct_include_subdirs_checkbox = QCheckBox(
        "Include subfolders (+i)",
        host,
    )
    dialog.unstoppable_struct_resume_checkbox = QCheckBox(
        "Recover and resume (+r)",
        host,
    )
    dialog.unstoppable_struct_copy_newer_checkbox = QCheckBox(
        "Copy newer only (+c)",
        host,
    )
    dialog.unstoppable_struct_skip_damaged_checkbox = QCheckBox(
        "Auto-skip damaged (+s)",
        host,
    )
    dialog.unstoppable_struct_undamaged_first_checkbox = QCheckBox(
        "Undamaged first (+u)",
        host,
    )
    dialog.unstoppable_struct_overwrite_readonly_checkbox = QCheckBox(
        "Overwrite read-only (+w)",
        host,
    )
    dialog.unstoppable_struct_copy_empty_folders_checkbox = QCheckBox(
        "Copy empty folders (+f)",
        host,
    )
    dialog.unstoppable_struct_eta_checkbox = QCheckBox("Show ETA (+z)", host)
    dialog.unstoppable_struct_power_down_checkbox = QCheckBox(
        "Power down after completion (+p)",
        host,
    )
    dialog.unstoppable_struct_extra_args_edit = QLineEdit(host)
    dialog.unstoppable_struct_extra_args_edit.setPlaceholderText("Extra args")
    dialog.unstoppable_struct_extra_args_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    for widget in [
        dialog.unstoppable_struct_defaults_checkbox,
        dialog.unstoppable_struct_keep_attributes_checkbox,
        dialog.unstoppable_struct_keep_owner_checkbox,
        dialog.unstoppable_struct_keep_time_checkbox,
        dialog.unstoppable_struct_overwrite_checkbox,
        dialog.unstoppable_struct_include_subdirs_checkbox,
        dialog.unstoppable_struct_resume_checkbox,
        dialog.unstoppable_struct_copy_newer_checkbox,
        dialog.unstoppable_struct_skip_damaged_checkbox,
        dialog.unstoppable_struct_undamaged_first_checkbox,
        dialog.unstoppable_struct_overwrite_readonly_checkbox,
        dialog.unstoppable_struct_copy_empty_folders_checkbox,
        dialog.unstoppable_struct_eta_checkbox,
        dialog.unstoppable_struct_power_down_checkbox,
        dialog.use_extended_paths_unstoppable_checkbox,
    ]:
        widget.toggled.connect(dialog.on_controls_changed)

    grid.addWidget(dialog.unstoppable_struct_defaults_checkbox, 0, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_keep_attributes_checkbox, 1, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_keep_owner_checkbox, 2, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_keep_time_checkbox, 3, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_overwrite_checkbox, 4, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_include_subdirs_checkbox, 5, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_resume_checkbox, 6, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_copy_newer_checkbox, 7, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_skip_damaged_checkbox, 8, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_undamaged_first_checkbox, 9, 0, 1, 2)
    grid.addWidget(
        dialog.unstoppable_struct_overwrite_readonly_checkbox,
        10,
        0,
        1,
        2,
    )
    grid.addWidget(
        dialog.unstoppable_struct_copy_empty_folders_checkbox,
        11,
        0,
        1,
        2,
    )
    grid.addWidget(dialog.unstoppable_struct_eta_checkbox, 12, 0, 1, 2)
    grid.addWidget(dialog.unstoppable_struct_power_down_checkbox, 13, 0, 1, 2)
    grid.addWidget(QLabel("Extra args", host), 14, 0)
    grid.addWidget(dialog.unstoppable_struct_extra_args_edit, 14, 1)
    grid.addWidget(dialog.use_extended_paths_unstoppable_checkbox, 15, 1)
    grid.setColumnStretch(1, 1)
    return grid


def _build_unstoppable_actions(
    dialog: SettingsDialog,
    host: QWidget,
) -> QWidget:
    """Build the Unstoppable Copier action row."""

    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    dialog.unstoppable_reset_backend_btn.clicked.connect(
        dialog.reset_unstoppable_backend_defaults
    )
    dialog.unstoppable_test_btn.clicked.connect(
        lambda: dialog.test_backend("copy", "unstoppable")
    )
    actions_layout.addWidget(dialog.unstoppable_reset_backend_btn)
    actions_layout.addWidget(dialog.unstoppable_test_btn)
    return actions


def build_external_copymove_settings_card(dialog: SettingsDialog) -> QWidget:
    """Build the structured external copy/move settings card."""

    host = QWidget(dialog)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(
        control_builders.build_backend_executable_controls(
            dialog,
            executable_edit=dialog.generic_copymove_executable_edit,
            default_executable=SettingsManager.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE,
            discover_default_executable="",
            enable_find=False,
        )
    )

    grid = QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)
    dialog.external_copymove_struct_include_operation_checkbox = QCheckBox(
        "Include {operation} placeholder",
        host,
    )
    dialog.external_copymove_struct_include_sources_checkbox = QCheckBox(
        "Include {sources} placeholder",
        host,
    )
    dialog.external_copymove_struct_include_target_checkbox = QCheckBox(
        "Include {target} placeholder",
        host,
    )
    dialog.external_copymove_struct_extra_args_edit = QLineEdit(host)
    dialog.external_copymove_struct_extra_args_edit.setPlaceholderText("Extra args")
    dialog.external_copymove_struct_extra_args_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    for widget in [
        dialog.external_copymove_struct_include_operation_checkbox,
        dialog.external_copymove_struct_include_sources_checkbox,
        dialog.external_copymove_struct_include_target_checkbox,
        dialog.use_extended_paths_external_copymove_checkbox,
    ]:
        widget.toggled.connect(dialog.on_controls_changed)
    grid.addWidget(
        dialog.external_copymove_struct_include_operation_checkbox,
        0,
        0,
        1,
        2,
    )
    grid.addWidget(
        dialog.external_copymove_struct_include_sources_checkbox,
        1,
        0,
        1,
        2,
    )
    grid.addWidget(
        dialog.external_copymove_struct_include_target_checkbox,
        2,
        0,
        1,
        2,
    )
    grid.addWidget(QLabel("Extra args", host), 3, 0)
    grid.addWidget(dialog.external_copymove_struct_extra_args_edit, 3, 1)
    grid.addWidget(dialog.use_extended_paths_external_copymove_checkbox, 4, 1)
    grid.setColumnStretch(1, 1)
    layout.addLayout(grid)

    dialog.external_copymove_preview_label = control_builders.build_preview_label(
        dialog
    )
    layout.addWidget(dialog.external_copymove_preview_label)

    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    dialog.external_copymove_reset_backend_btn.clicked.connect(
        dialog.reset_external_copymove_backend_defaults
    )
    dialog.generic_copymove_test_btn.clicked.connect(
        lambda: dialog.test_backend("copy", "external_copymove")
    )
    actions_layout.addWidget(dialog.external_copymove_reset_backend_btn)
    actions_layout.addWidget(dialog.generic_copymove_test_btn)
    layout.addWidget(actions)
    return host
