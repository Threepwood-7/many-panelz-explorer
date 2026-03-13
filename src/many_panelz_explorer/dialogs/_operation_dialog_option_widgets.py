"""Backend-specific option widget builders for the operation dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)


@dataclass(frozen=True)
class RobocopyOptionWidgets:
    """Bundle the Robocopy option widgets created for the dialog."""

    group: QWidget
    include_subdirs_checkbox: QCheckBox
    mirror_checkbox: QCheckBox
    move_checkbox: QCheckBox
    restartable_checkbox: QCheckBox
    backup_mode_checkbox: QCheckBox
    list_only_checkbox: QCheckBox
    quiet_checkbox: QCheckBox
    retry_spin: QSpinBox
    wait_spin: QSpinBox
    multithread_checkbox: QCheckBox
    multithread_spin: QSpinBox
    extra_args_edit: QLineEdit


@dataclass(frozen=True)
class TeraCopyOptionWidgets:
    """Bundle the TeraCopy option widgets created for the dialog."""

    group: QWidget
    close_checkbox: QCheckBox
    no_close_checkbox: QCheckBox
    conflict_combo: QComboBox
    extra_args_edit: QLineEdit


@dataclass(frozen=True)
class UnstoppableOptionWidgets:
    """Bundle the Unstoppable Copier option widgets created for the dialog."""

    group: QWidget
    defaults_checkbox: QCheckBox
    keep_attributes_checkbox: QCheckBox
    keep_owner_checkbox: QCheckBox
    keep_time_checkbox: QCheckBox
    overwrite_checkbox: QCheckBox
    include_subdirs_checkbox: QCheckBox
    resume_checkbox: QCheckBox
    copy_newer_checkbox: QCheckBox
    skip_damaged_checkbox: QCheckBox
    undamaged_first_checkbox: QCheckBox
    overwrite_readonly_checkbox: QCheckBox
    copy_empty_folders_checkbox: QCheckBox
    eta_checkbox: QCheckBox
    power_down_checkbox: QCheckBox
    extra_args_edit: QLineEdit


@dataclass(frozen=True)
class ExternalOptionWidgets:
    """Bundle the external-command option widgets created for the dialog."""

    group: QWidget
    extra_args_edit: QLineEdit


def build_robocopy_options_group(
    parent: QWidget,
    *,
    kind: str,
) -> RobocopyOptionWidgets:
    """Create the Robocopy option controls."""
    group = QWidget(parent)
    layout = QGridLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)

    include_subdirs_checkbox = QCheckBox("Copy subdirectories (/E)", group)
    include_subdirs_checkbox.setChecked(True)
    mirror_checkbox = QCheckBox("Mirror target (/MIR)", group)
    move_checkbox = QCheckBox("Move files (/MOVE)", group)
    move_checkbox.setChecked(kind == "move")
    move_checkbox.setEnabled(kind == "move")
    restartable_checkbox = QCheckBox("Restartable mode (/Z)", group)
    backup_mode_checkbox = QCheckBox("Backup mode (/B)", group)
    list_only_checkbox = QCheckBox("List only dry-run (/L)", group)
    quiet_checkbox = QCheckBox(
        "Suppress detailed logs (/NFL /NDL /NJH /NJS /NP)",
        group,
    )
    retry_spin = QSpinBox(group)
    retry_spin.setRange(0, 1_000_000)
    wait_spin = QSpinBox(group)
    wait_spin.setRange(0, 3600)
    multithread_checkbox = QCheckBox("Multi-threaded copy (/MT)", group)
    multithread_spin = QSpinBox(group)
    multithread_spin.setRange(1, 128)
    multithread_spin.setValue(8)
    multithread_spin.setEnabled(False)
    multithread_checkbox.toggled.connect(multithread_spin.setEnabled)
    extra_args_edit = QLineEdit(group)
    extra_args_edit.setPlaceholderText("Additional Robocopy args")

    layout.addWidget(include_subdirs_checkbox, 0, 0, 1, 2)
    layout.addWidget(mirror_checkbox, 1, 0, 1, 2)
    layout.addWidget(move_checkbox, 2, 0, 1, 2)
    layout.addWidget(restartable_checkbox, 3, 0, 1, 2)
    layout.addWidget(backup_mode_checkbox, 4, 0, 1, 2)
    layout.addWidget(list_only_checkbox, 5, 0, 1, 2)
    layout.addWidget(quiet_checkbox, 6, 0, 1, 2)
    layout.addWidget(QLabel("Retry count (/R)", group), 7, 0)
    layout.addWidget(retry_spin, 7, 1)
    layout.addWidget(QLabel("Wait seconds (/W)", group), 8, 0)
    layout.addWidget(wait_spin, 8, 1)
    layout.addWidget(multithread_checkbox, 9, 0)
    layout.addWidget(multithread_spin, 9, 1)
    layout.addWidget(QLabel("Extra args", group), 10, 0)
    layout.addWidget(extra_args_edit, 10, 1)
    layout.setColumnStretch(1, 1)

    return RobocopyOptionWidgets(
        group=group,
        include_subdirs_checkbox=include_subdirs_checkbox,
        mirror_checkbox=mirror_checkbox,
        move_checkbox=move_checkbox,
        restartable_checkbox=restartable_checkbox,
        backup_mode_checkbox=backup_mode_checkbox,
        list_only_checkbox=list_only_checkbox,
        quiet_checkbox=quiet_checkbox,
        retry_spin=retry_spin,
        wait_spin=wait_spin,
        multithread_checkbox=multithread_checkbox,
        multithread_spin=multithread_spin,
        extra_args_edit=extra_args_edit,
    )


def build_teracopy_options_group(parent: QWidget) -> TeraCopyOptionWidgets:
    """Create the TeraCopy option controls."""
    group = QWidget(parent)
    layout = QGridLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)

    close_checkbox = QCheckBox("Close on completion (/Close)", group)
    no_close_checkbox = QCheckBox("Keep window open (/NoClose)", group)
    conflict_combo = QComboBox(group)
    conflict_combo.addItem("No explicit override", "")
    conflict_combo.addItem("Overwrite All", "/OverwriteAll")
    conflict_combo.addItem("Skip All", "/SkipAll")
    conflict_combo.addItem("Rename All", "/RenameAll")
    conflict_combo.addItem("Overwrite Older", "/OverwriteOlder")
    conflict_combo.addItem("Overwrite Different Size", "/OverwriteDiffSize")
    conflict_combo.addItem("Rename Copied", "/RenameCopied")
    conflict_combo.addItem("Rename Destination", "/RenameDestination")
    extra_args_edit = QLineEdit(group)
    extra_args_edit.setPlaceholderText("Additional TeraCopy args")

    layout.addWidget(close_checkbox, 0, 0, 1, 2)
    layout.addWidget(no_close_checkbox, 1, 0, 1, 2)
    layout.addWidget(QLabel("Conflict override", group), 2, 0)
    layout.addWidget(conflict_combo, 2, 1)
    layout.addWidget(QLabel("Extra args", group), 3, 0)
    layout.addWidget(extra_args_edit, 3, 1)
    layout.setColumnStretch(1, 1)

    return TeraCopyOptionWidgets(
        group=group,
        close_checkbox=close_checkbox,
        no_close_checkbox=no_close_checkbox,
        conflict_combo=conflict_combo,
        extra_args_edit=extra_args_edit,
    )


def build_unstoppable_options_group(parent: QWidget) -> UnstoppableOptionWidgets:
    """Create the Unstoppable Copier option controls."""
    group = QWidget(parent)
    layout = QGridLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)

    defaults_checkbox = QCheckBox("Use program defaults (+d)", group)
    defaults_checkbox.setChecked(True)
    keep_attributes_checkbox = QCheckBox("Copy attributes (+a)", group)
    keep_attributes_checkbox.setChecked(True)
    keep_owner_checkbox = QCheckBox("Copy ownership (+o)", group)
    keep_owner_checkbox.setChecked(True)
    keep_time_checkbox = QCheckBox("Copy date/time (+t)", group)
    keep_time_checkbox.setChecked(True)
    overwrite_checkbox = QCheckBox("Overwrite existing (+e)", group)
    overwrite_checkbox.setChecked(True)
    include_subdirs_checkbox = QCheckBox("Include subfolders (+i)", group)
    include_subdirs_checkbox.setChecked(True)
    resume_checkbox = QCheckBox("Recover damaged and resume (+r)", group)
    copy_newer_checkbox = QCheckBox("Copy only if source newer (+c)", group)
    skip_damaged_checkbox = QCheckBox("Auto-skip damaged files (+s)", group)
    undamaged_first_checkbox = QCheckBox("Undamaged files first (+u)", group)
    overwrite_readonly_checkbox = QCheckBox("Overwrite read-only files (+w)", group)
    copy_empty_folders_checkbox = QCheckBox("Copy empty folders (+f)", group)
    eta_checkbox = QCheckBox("Show remaining time (+z)", group)
    power_down_checkbox = QCheckBox("Power down after completion (+p)", group)
    extra_args_edit = QLineEdit(group)
    extra_args_edit.setPlaceholderText("Additional Unstoppable Copier args")

    layout.addWidget(defaults_checkbox, 0, 0, 1, 2)
    layout.addWidget(keep_attributes_checkbox, 1, 0, 1, 2)
    layout.addWidget(keep_owner_checkbox, 2, 0, 1, 2)
    layout.addWidget(keep_time_checkbox, 3, 0, 1, 2)
    layout.addWidget(overwrite_checkbox, 4, 0, 1, 2)
    layout.addWidget(include_subdirs_checkbox, 5, 0, 1, 2)
    layout.addWidget(resume_checkbox, 6, 0, 1, 2)
    layout.addWidget(copy_newer_checkbox, 7, 0, 1, 2)
    layout.addWidget(skip_damaged_checkbox, 8, 0, 1, 2)
    layout.addWidget(undamaged_first_checkbox, 9, 0, 1, 2)
    layout.addWidget(overwrite_readonly_checkbox, 10, 0, 1, 2)
    layout.addWidget(copy_empty_folders_checkbox, 11, 0, 1, 2)
    layout.addWidget(eta_checkbox, 12, 0, 1, 2)
    layout.addWidget(power_down_checkbox, 13, 0, 1, 2)
    layout.addWidget(QLabel("Extra args", group), 14, 0)
    layout.addWidget(extra_args_edit, 14, 1)
    layout.setColumnStretch(1, 1)

    return UnstoppableOptionWidgets(
        group=group,
        defaults_checkbox=defaults_checkbox,
        keep_attributes_checkbox=keep_attributes_checkbox,
        keep_owner_checkbox=keep_owner_checkbox,
        keep_time_checkbox=keep_time_checkbox,
        overwrite_checkbox=overwrite_checkbox,
        include_subdirs_checkbox=include_subdirs_checkbox,
        resume_checkbox=resume_checkbox,
        copy_newer_checkbox=copy_newer_checkbox,
        skip_damaged_checkbox=skip_damaged_checkbox,
        undamaged_first_checkbox=undamaged_first_checkbox,
        overwrite_readonly_checkbox=overwrite_readonly_checkbox,
        copy_empty_folders_checkbox=copy_empty_folders_checkbox,
        eta_checkbox=eta_checkbox,
        power_down_checkbox=power_down_checkbox,
        extra_args_edit=extra_args_edit,
    )


def build_external_options_group(parent: QWidget) -> ExternalOptionWidgets:
    """Create the external command option controls."""
    group = QWidget(parent)
    layout = QHBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    extra_args_edit = QLineEdit(group)
    extra_args_edit.setPlaceholderText("Optional args appended to command")
    layout.addWidget(QLabel("Extra args", group))
    layout.addWidget(extra_args_edit, 1)
    return ExternalOptionWidgets(group=group, extra_args_edit=extra_args_edit)
