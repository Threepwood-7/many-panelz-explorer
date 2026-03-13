"""Backend state helpers for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    generate_external_copymove_args_template,
    generate_robocopy_args,
    generate_teracopy_args_template,
    generate_unstoppable_args_template,
    resolve_copy_move_backend_args,
)
from ..._settings.manager import SettingsManager

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def robocopy_structured_options_from_controls(
    dialog: SettingsDialog,
) -> RobocopyBackendOptions:
    """Build Robocopy structured options from dialog controls."""

    return RobocopyBackendOptions(
        include_subdirectories=dialog.robocopy_struct_include_subdirs_checkbox.isChecked(),
        mirror_target=dialog.robocopy_struct_mirror_checkbox.isChecked(),
        move_files_for_move=dialog.robocopy_struct_move_checkbox.isChecked(),
        restartable_mode=dialog.robocopy_struct_restartable_checkbox.isChecked(),
        backup_mode=dialog.robocopy_struct_backup_checkbox.isChecked(),
        list_only=dialog.robocopy_struct_list_only_checkbox.isChecked(),
        suppress_logs=dialog.robocopy_struct_quiet_checkbox.isChecked(),
        retry_count=dialog.robocopy_struct_retry_spin.value(),
        wait_seconds=dialog.robocopy_struct_wait_spin.value(),
        use_multithreading=dialog.robocopy_struct_multithread_checkbox.isChecked(),
        multithread_count=dialog.robocopy_struct_multithread_spin.value(),
        extra_args=dialog.robocopy_struct_extra_args_edit.text().strip(),
    )


def teracopy_structured_options_from_controls(
    dialog: SettingsDialog,
) -> TeraCopyBackendOptions:
    """Build TeraCopy structured options from dialog controls."""

    return TeraCopyBackendOptions(
        close_on_finish=dialog.teracopy_struct_close_checkbox.isChecked(),
        keep_open=dialog.teracopy_struct_keep_open_checkbox.isChecked(),
        verify_after_copy=dialog.teracopy_struct_verify_checkbox.isChecked(),
        no_sound=dialog.teracopy_struct_no_sound_checkbox.isChecked(),
        conflict_mode=str(dialog.teracopy_struct_conflict_combo.currentData() or ""),
        extra_args=dialog.teracopy_struct_extra_args_edit.text().strip(),
    )


def unstoppable_structured_options_from_controls(
    dialog: SettingsDialog,
) -> UnstoppableBackendOptions:
    """Build Unstoppable Copier structured options from dialog controls."""

    return UnstoppableBackendOptions(
        use_defaults=dialog.unstoppable_struct_defaults_checkbox.isChecked(),
        keep_attributes=dialog.unstoppable_struct_keep_attributes_checkbox.isChecked(),
        keep_owner=dialog.unstoppable_struct_keep_owner_checkbox.isChecked(),
        keep_time=dialog.unstoppable_struct_keep_time_checkbox.isChecked(),
        overwrite_existing=dialog.unstoppable_struct_overwrite_checkbox.isChecked(),
        include_subfolders=dialog.unstoppable_struct_include_subdirs_checkbox.isChecked(),
        recover_and_resume=dialog.unstoppable_struct_resume_checkbox.isChecked(),
        copy_newer_only=dialog.unstoppable_struct_copy_newer_checkbox.isChecked(),
        skip_damaged=dialog.unstoppable_struct_skip_damaged_checkbox.isChecked(),
        undamaged_first=dialog.unstoppable_struct_undamaged_first_checkbox.isChecked(),
        overwrite_readonly=dialog.unstoppable_struct_overwrite_readonly_checkbox.isChecked(),
        copy_empty_folders=dialog.unstoppable_struct_copy_empty_folders_checkbox.isChecked(),
        show_eta=dialog.unstoppable_struct_eta_checkbox.isChecked(),
        power_down_when_done=dialog.unstoppable_struct_power_down_checkbox.isChecked(),
        extra_args=dialog.unstoppable_struct_extra_args_edit.text().strip(),
    )


def external_copymove_structured_options_from_controls(
    dialog: SettingsDialog,
) -> ExternalCopyMoveBackendOptions:
    """Build external copy/move structured options from dialog controls."""

    return ExternalCopyMoveBackendOptions(
        include_operation_token=dialog.external_copymove_struct_include_operation_checkbox.isChecked(),
        include_sources=dialog.external_copymove_struct_include_sources_checkbox.isChecked(),
        include_target=dialog.external_copymove_struct_include_target_checkbox.isChecked(),
        extra_args=dialog.external_copymove_struct_extra_args_edit.text().strip(),
    )


def apply_robocopy_structured_options_to_controls(
    dialog: SettingsDialog,
    options: RobocopyBackendOptions,
) -> None:
    """Apply Robocopy structured options to dialog controls."""

    dialog.robocopy_struct_include_subdirs_checkbox.setChecked(
        options.include_subdirectories
    )
    dialog.robocopy_struct_mirror_checkbox.setChecked(options.mirror_target)
    dialog.robocopy_struct_move_checkbox.setChecked(options.move_files_for_move)
    dialog.robocopy_struct_restartable_checkbox.setChecked(options.restartable_mode)
    dialog.robocopy_struct_backup_checkbox.setChecked(options.backup_mode)
    dialog.robocopy_struct_list_only_checkbox.setChecked(options.list_only)
    dialog.robocopy_struct_quiet_checkbox.setChecked(options.suppress_logs)
    dialog.robocopy_struct_retry_spin.setValue(options.retry_count)
    dialog.robocopy_struct_wait_spin.setValue(options.wait_seconds)
    dialog.robocopy_struct_multithread_checkbox.setChecked(options.use_multithreading)
    dialog.robocopy_struct_multithread_spin.setValue(options.multithread_count)
    dialog.robocopy_struct_extra_args_edit.setText(options.extra_args)


def apply_teracopy_structured_options_to_controls(
    dialog: SettingsDialog,
    options: TeraCopyBackendOptions,
) -> None:
    """Apply TeraCopy structured options to dialog controls."""

    dialog.teracopy_struct_close_checkbox.setChecked(options.close_on_finish)
    dialog.teracopy_struct_keep_open_checkbox.setChecked(options.keep_open)
    dialog.teracopy_struct_verify_checkbox.setChecked(options.verify_after_copy)
    dialog.teracopy_struct_no_sound_checkbox.setChecked(options.no_sound)
    dialog.set_combo_value(dialog.teracopy_struct_conflict_combo, options.conflict_mode)
    dialog.teracopy_struct_extra_args_edit.setText(options.extra_args)


def apply_unstoppable_structured_options_to_controls(
    dialog: SettingsDialog,
    options: UnstoppableBackendOptions,
) -> None:
    """Apply Unstoppable Copier structured options to dialog controls."""

    dialog.unstoppable_struct_defaults_checkbox.setChecked(options.use_defaults)
    dialog.unstoppable_struct_keep_attributes_checkbox.setChecked(
        options.keep_attributes
    )
    dialog.unstoppable_struct_keep_owner_checkbox.setChecked(options.keep_owner)
    dialog.unstoppable_struct_keep_time_checkbox.setChecked(options.keep_time)
    dialog.unstoppable_struct_overwrite_checkbox.setChecked(options.overwrite_existing)
    dialog.unstoppable_struct_include_subdirs_checkbox.setChecked(
        options.include_subfolders
    )
    dialog.unstoppable_struct_resume_checkbox.setChecked(options.recover_and_resume)
    dialog.unstoppable_struct_copy_newer_checkbox.setChecked(options.copy_newer_only)
    dialog.unstoppable_struct_skip_damaged_checkbox.setChecked(options.skip_damaged)
    dialog.unstoppable_struct_undamaged_first_checkbox.setChecked(
        options.undamaged_first
    )
    dialog.unstoppable_struct_overwrite_readonly_checkbox.setChecked(
        options.overwrite_readonly
    )
    dialog.unstoppable_struct_copy_empty_folders_checkbox.setChecked(
        options.copy_empty_folders
    )
    dialog.unstoppable_struct_eta_checkbox.setChecked(options.show_eta)
    dialog.unstoppable_struct_power_down_checkbox.setChecked(
        options.power_down_when_done
    )
    dialog.unstoppable_struct_extra_args_edit.setText(options.extra_args)


def apply_external_copymove_structured_options_to_controls(
    dialog: SettingsDialog,
    options: ExternalCopyMoveBackendOptions,
) -> None:
    """Apply external copy/move structured options to dialog controls."""

    dialog.external_copymove_struct_include_operation_checkbox.setChecked(
        options.include_operation_token
    )
    dialog.external_copymove_struct_include_sources_checkbox.setChecked(
        options.include_sources
    )
    dialog.external_copymove_struct_include_target_checkbox.setChecked(
        options.include_target
    )
    dialog.external_copymove_struct_extra_args_edit.setText(options.extra_args)


def reset_robocopy_backend_defaults(dialog: SettingsDialog) -> None:
    """Reset Robocopy controls to their default state."""

    apply_robocopy_structured_options_to_controls(dialog, RobocopyBackendOptions())
    dialog.on_controls_changed()


def reset_teracopy_backend_defaults(dialog: SettingsDialog) -> None:
    """Reset TeraCopy controls to their default state."""

    apply_teracopy_structured_options_to_controls(dialog, TeraCopyBackendOptions())
    dialog.teracopy_executable_edit.setText(SettingsManager.DEFAULT_TERACOPY_EXECUTABLE)
    dialog.on_controls_changed()


def reset_unstoppable_backend_defaults(dialog: SettingsDialog) -> None:
    """Reset Unstoppable Copier controls to their default state."""

    apply_unstoppable_structured_options_to_controls(
        dialog,
        UnstoppableBackendOptions(),
    )
    dialog.unstoppable_executable_edit.setText(
        SettingsManager.DEFAULT_UNSTOPPABLE_EXECUTABLE
    )
    dialog.on_controls_changed()


def reset_external_copymove_backend_defaults(dialog: SettingsDialog) -> None:
    """Reset external copy/move controls to their default state."""

    apply_external_copymove_structured_options_to_controls(
        dialog,
        ExternalCopyMoveBackendOptions(),
    )
    dialog.generic_copymove_executable_edit.setText(
        SettingsManager.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE
    )
    dialog.on_controls_changed()


def update_backend_generated_previews(dialog: SettingsDialog) -> None:
    """Refresh generated command preview labels for backend settings."""

    robocopy_options = robocopy_structured_options_from_controls(dialog)
    teracopy_options = teracopy_structured_options_from_controls(dialog)
    unstoppable_options = unstoppable_structured_options_from_controls(dialog)
    external_options = external_copymove_structured_options_from_controls(dialog)
    resolved = resolve_copy_move_backend_args(
        robocopy_options=robocopy_options,
        teracopy_options=teracopy_options,
        unstoppable_options=unstoppable_options,
        external_copymove_options=external_options,
    )
    generated_robocopy_copy = generate_robocopy_args(robocopy_options, kind="copy")
    generated_robocopy_move = generate_robocopy_args(robocopy_options, kind="move")
    generated_teracopy = generate_teracopy_args_template(teracopy_options)
    generated_unstoppable = generate_unstoppable_args_template(unstoppable_options)
    generated_external = generate_external_copymove_args_template(external_options)

    dialog.robocopy_preview_label.setText(
        "Generated copy args: "
        f"{generated_robocopy_copy or '(empty)'}\n"
        "Generated move args: "
        f"{generated_robocopy_move or '(empty)'}\n"
        "Effective copy args: "
        f"{resolved.robocopy_copy_args}\n"
        "Effective move args: "
        f"{resolved.robocopy_move_args}"
    )
    dialog.teracopy_preview_label.setText(
        "Generated args template: "
        f"{generated_teracopy or '(empty)'}\n"
        "Effective args template: "
        f"{resolved.teracopy_args_template}"
    )
    generated_unstoppable_preview = (
        f"{generated_unstoppable} {{job_file}}\n"
        if generated_unstoppable
        else "{job_file}\n"
    )
    effective_unstoppable_preview = (
        f"{resolved.unstoppable_args_template} {{job_file}}"
        if resolved.unstoppable_args_template
        else "{job_file}"
    )
    dialog.unstoppable_preview_label.setText(
        "Generated args template: "
        f"{generated_unstoppable_preview}"
        "Effective args template: "
        f"{effective_unstoppable_preview}"
    )
    dialog.external_copymove_preview_label.setText(
        "Generated args template: "
        f"{generated_external or '(empty)'}\n"
        "Effective args template: "
        f"{resolved.external_copymove_args_template}"
    )
