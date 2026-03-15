"""Preference loading and control-sync helpers for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from ..._operations.discovery import resolve_system_command_paths
from ..._settings.models import UiPreferences
from . import backend_state, open_overrides_state

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLabel

    from ..settings_dialog import SettingsDialog


def sync_font_override_controls(dialog: SettingsDialog) -> None:
    """Enable or disable font override controls based on checkbox state."""

    file_list_override_enabled = not dialog.file_list_use_app_font_checkbox.isChecked()
    dialog.file_list_font_family_combo.setEnabled(file_list_override_enabled)
    dialog.file_list_font_size_spin.setEnabled(file_list_override_enabled)

    navigation_override_enabled = not (
        dialog.navigation_use_app_font_checkbox.isChecked()
    )
    dialog.navigation_font_family_combo.setEnabled(navigation_override_enabled)
    dialog.navigation_font_size_spin.setEnabled(navigation_override_enabled)


def sync_byte_format_controls(dialog: SettingsDialog) -> None:
    """Enable custom-template edits only for custom byte-format modes."""

    dialog.file_list_byte_custom_template_edit.setEnabled(
        str(dialog.file_list_byte_format_mode_combo.currentData()) == "custom"
    )
    dialog.status_bar_byte_custom_template_edit.setEnabled(
        str(dialog.status_bar_byte_format_mode_combo.currentData()) == "custom"
    )
    dialog.properties_byte_custom_template_edit.setEnabled(
        str(dialog.properties_byte_format_mode_combo.currentData()) == "custom"
    )


def load_panel_preferences(dialog: SettingsDialog, preferences: UiPreferences) -> None:
    """Load panel behavior and byte-display preferences into controls."""

    dialog.set_combo_value(dialog.new_context_combo, preferences.new_context_mode)
    dialog.context_scan_cap_spin.setValue(preferences.context_immediate_child_scan_cap)
    dialog.show_hidden_checkbox.setChecked(preferences.show_hidden_default)
    dialog.show_root_dropdown_checkbox.setChecked(preferences.show_root_dropdown)
    dialog.set_combo_value(
        dialog.column_width_auto_align_mode_combo,
        preferences.column_width_auto_align_mode,
    )
    dialog.autofit_columns_checkbox.setChecked(preferences.autofit_columns)
    dialog.show_refresh_button_checkbox.setChecked(preferences.show_refresh_button)
    dialog.show_root_buttons_checkbox.setChecked(preferences.show_root_buttons)
    dialog.show_address_bar_checkbox.setChecked(preferences.show_address_bar)
    dialog.show_navigation_buttons_checkbox.setChecked(
        preferences.show_navigation_buttons
    )
    dialog.show_storage_overview_status_row_checkbox.setChecked(
        preferences.show_storage_overview_status_row
    )
    dialog.byte_thousands_separator_edit.setText(preferences.byte_thousands_separator)
    dialog.byte_decimal_separator_edit.setText(preferences.byte_decimal_separator)
    dialog.set_combo_value(
        dialog.file_list_byte_format_mode_combo,
        preferences.file_list_byte_format_mode,
    )
    dialog.file_list_byte_custom_template_edit.setText(
        preferences.file_list_byte_custom_template
    )
    dialog.set_combo_value(
        dialog.status_bar_byte_format_mode_combo,
        preferences.status_bar_byte_format_mode,
    )
    dialog.status_bar_byte_custom_template_edit.setText(
        preferences.status_bar_byte_custom_template
    )
    dialog.status_bar_storage_label_template_edit.setText(
        preferences.status_bar_storage_label_template
    )
    dialog.set_combo_value(
        dialog.properties_byte_format_mode_combo,
        preferences.properties_byte_format_mode,
    )
    dialog.properties_byte_custom_template_edit.setText(
        preferences.properties_byte_custom_template
    )


def load_operations_preferences(
    dialog: SettingsDialog, preferences: UiPreferences
) -> None:
    """Load operation backend, queue, and diagnostics preferences."""

    dialog.set_combo_value(
        dialog.default_copy_move_backend_combo,
        preferences.default_copy_move_backend,
    )
    dialog.set_combo_value(
        dialog.default_delete_backend_combo,
        preferences.default_delete_backend,
    )
    dialog.set_combo_value(
        dialog.default_dispatch_mode_combo,
        preferences.default_operation_dispatch_mode,
    )
    dialog.set_combo_value(
        dialog.default_conflict_policy_combo,
        preferences.default_operation_conflict_policy,
    )
    dialog.set_combo_value(
        dialog.operation_shortcut_behavior_combo,
        preferences.operation_shortcut_behavior,
    )
    dialog.set_combo_value(
        dialog.operation_queue_view_mode_combo,
        preferences.operation_queue_view_mode,
    )
    dialog.default_editor_executable_edit.setText(preferences.default_editor_executable)
    dialog.default_viewer_executable_edit.setText(preferences.default_viewer_executable)
    dialog.context_code_editor_executable_edit.setText(
        preferences.context_tool_code_editor_exe_path
    )
    dialog.context_code_editor_args_edit.setText(
        preferences.context_tool_code_editor_args_template
    )
    dialog.context_git_gui_executable_edit.setText(
        preferences.context_tool_git_gui_exe_path
    )
    dialog.context_git_gui_args_edit.setText(
        preferences.context_tool_git_gui_args_template
    )
    dialog.total_commander_executable_edit.setText(
        preferences.total_commander_executable
    )
    dialog.total_commander_source_args_edit.setText(
        preferences.total_commander_source_args_template
    )
    dialog.total_commander_source_target_args_edit.setText(
        preferences.total_commander_source_target_args_template
    )
    dialog.double_commander_executable_edit.setText(
        preferences.double_commander_executable
    )
    dialog.double_commander_source_args_edit.setText(
        preferences.double_commander_source_args_template
    )
    dialog.double_commander_source_target_args_edit.setText(
        preferences.double_commander_source_target_args_template
    )
    open_overrides_state.load_file_open_overrides(
        dialog,
        preferences.file_open_overrides_json,
    )
    dialog.use_extended_paths_robocopy_checkbox.setChecked(
        preferences.use_extended_paths_robocopy
    )
    dialog.use_extended_paths_teracopy_checkbox.setChecked(
        preferences.use_extended_paths_teracopy
    )
    dialog.use_extended_paths_unstoppable_checkbox.setChecked(
        preferences.use_extended_paths_unstoppable
    )
    dialog.use_extended_paths_external_copymove_checkbox.setChecked(
        preferences.use_extended_paths_external_copymove
    )
    dialog.use_extended_paths_cmd_delete_checkbox.setChecked(
        preferences.use_extended_paths_cmd_delete
    )
    dialog.use_extended_paths_powershell_delete_checkbox.setChecked(
        preferences.use_extended_paths_powershell_delete
    )
    dialog.use_extended_paths_rimraf_checkbox.setChecked(
        preferences.use_extended_paths_rimraf
    )
    dialog.use_extended_paths_external_delete_checkbox.setChecked(
        preferences.use_extended_paths_external_delete
    )
    dialog.teracopy_executable_edit.setText(preferences.teracopy_executable)
    dialog.unstoppable_executable_edit.setText(preferences.unstoppable_executable)
    dialog.generic_copymove_executable_edit.setText(
        preferences.generic_copymove_executable
    )
    dialog.generic_delete_executable_edit.setText(preferences.generic_delete_executable)
    dialog.generic_delete_args_edit.setText(preferences.generic_delete_args_template)
    backend_state.apply_robocopy_structured_options_to_controls(
        dialog, preferences.robocopy_structured_options
    )
    backend_state.apply_teracopy_structured_options_to_controls(
        dialog, preferences.teracopy_structured_options
    )
    backend_state.apply_unstoppable_structured_options_to_controls(
        dialog, preferences.unstoppable_structured_options
    )
    backend_state.apply_external_copymove_structured_options_to_controls(
        dialog, preferences.external_copymove_structured_options
    )
    dialog.cmd_delete_args_edit.setText(preferences.cmd_delete_args)
    dialog.powershell_delete_args_edit.setText(preferences.powershell_delete_args)
    dialog.rimraf_executable_edit.setText(preferences.rimraf_executable)
    dialog.rimraf_args_edit.setText(preferences.rimraf_args_template)
    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    dialog.resolved_cmd_path_label.setText(f"ComSpec: {resolved_cmd}")
    dialog.resolved_robocopy_path_label.setText(f"Robocopy: {resolved_robocopy}")
    dialog.resolved_cmd_path_label.setToolTip(resolved_cmd)
    dialog.resolved_robocopy_path_label.setToolTip(resolved_robocopy)


def load_typography_preferences(
    dialog: SettingsDialog, preferences: UiPreferences
) -> None:
    """Load app and panel font preferences into controls."""

    dialog.set_combo_value(dialog.app_font_family_combo, preferences.app_font_family)
    dialog.app_font_size_spin.setValue(preferences.app_font_size_pt)
    dialog.file_list_use_app_font_checkbox.setChecked(
        preferences.file_list_use_app_font
    )
    dialog.set_combo_value(
        dialog.file_list_font_family_combo,
        preferences.file_list_font_family,
    )
    dialog.file_list_font_size_spin.setValue(preferences.file_list_font_size_pt)
    dialog.navigation_use_app_font_checkbox.setChecked(
        preferences.navigation_use_app_font
    )
    dialog.set_combo_value(
        dialog.navigation_font_family_combo,
        preferences.navigation_font_family,
    )
    dialog.navigation_font_size_spin.setValue(preferences.navigation_font_size_pt)


def sync_slider_value_labels(dialog: SettingsDialog) -> None:
    """Refresh the intensity labels that mirror slider values."""

    dialog.active_intensity_value.setText(f"{dialog.active_intensity_slider.value()}%")
    dialog.target_intensity_value.setText(f"{dialog.target_intensity_slider.value()}%")


def sync_color_preview(target: QLabel, color_hex: str) -> None:
    """Refresh a tint color preview label."""

    target.setStyleSheet(f"background: {color_hex}; border: 1px solid #777;")
    target.setText(color_hex)
    target.setAlignment(Qt.AlignmentFlag.AlignCenter)


def collect_preferences_from_controls(dialog: SettingsDialog) -> UiPreferences:
    """Collect the current dialog control state into UI preferences."""

    return UiPreferences(
        new_context_mode=str(dialog.new_context_combo.currentData()),
        show_hidden_default=dialog.show_hidden_checkbox.isChecked(),
        show_root_dropdown=dialog.show_root_dropdown_checkbox.isChecked(),
        column_width_auto_align_mode=str(
            dialog.column_width_auto_align_mode_combo.currentData()
        ),
        autofit_columns=dialog.autofit_columns_checkbox.isChecked(),
        context_immediate_child_scan_cap=dialog.context_scan_cap_spin.value(),
        show_refresh_button=dialog.show_refresh_button_checkbox.isChecked(),
        show_root_buttons=dialog.show_root_buttons_checkbox.isChecked(),
        show_address_bar=dialog.show_address_bar_checkbox.isChecked(),
        show_navigation_buttons=dialog.show_navigation_buttons_checkbox.isChecked(),
        show_storage_overview_status_row=dialog.show_storage_overview_status_row_checkbox.isChecked(),
        byte_thousands_separator=dialog.byte_thousands_separator_edit.text(),
        byte_decimal_separator=dialog.byte_decimal_separator_edit.text(),
        file_list_byte_format_mode=str(
            dialog.file_list_byte_format_mode_combo.currentData()
        ),
        file_list_byte_custom_template=dialog.file_list_byte_custom_template_edit.text(),
        status_bar_byte_format_mode=str(
            dialog.status_bar_byte_format_mode_combo.currentData()
        ),
        status_bar_byte_custom_template=dialog.status_bar_byte_custom_template_edit.text(),
        status_bar_storage_label_template=dialog.status_bar_storage_label_template_edit.text(),
        properties_byte_format_mode=str(
            dialog.properties_byte_format_mode_combo.currentData()
        ),
        properties_byte_custom_template=dialog.properties_byte_custom_template_edit.text(),
        default_copy_move_backend=str(
            dialog.default_copy_move_backend_combo.currentData()
        ),
        default_delete_backend=str(dialog.default_delete_backend_combo.currentData()),
        default_operation_dispatch_mode=str(
            dialog.default_dispatch_mode_combo.currentData()
        ),
        default_operation_conflict_policy=str(
            dialog.default_conflict_policy_combo.currentData()
        ),
        operation_shortcut_behavior=str(
            dialog.operation_shortcut_behavior_combo.currentData()
        ),
        operation_queue_view_mode=str(
            dialog.operation_queue_view_mode_combo.currentData()
        ),
        default_editor_executable=dialog.default_editor_executable_edit.text().strip(),
        default_viewer_executable=dialog.default_viewer_executable_edit.text().strip(),
        context_tool_code_editor_exe_path=dialog.context_code_editor_executable_edit.text().strip(),
        context_tool_code_editor_args_template=dialog.context_code_editor_args_edit.text().strip(),
        context_tool_git_gui_exe_path=dialog.context_git_gui_executable_edit.text().strip(),
        context_tool_git_gui_args_template=dialog.context_git_gui_args_edit.text().strip(),
        total_commander_executable=dialog.total_commander_executable_edit.text().strip(),
        total_commander_source_args_template=dialog.total_commander_source_args_edit.text().strip(),
        total_commander_source_target_args_template=dialog.total_commander_source_target_args_edit.text().strip(),
        double_commander_executable=dialog.double_commander_executable_edit.text().strip(),
        double_commander_source_args_template=dialog.double_commander_source_args_edit.text().strip(),
        double_commander_source_target_args_template=dialog.double_commander_source_target_args_edit.text().strip(),
        file_open_overrides_json=open_overrides_state.serialize_file_open_overrides(
            dialog
        ),
        use_extended_paths_robocopy=dialog.use_extended_paths_robocopy_checkbox.isChecked(),
        use_extended_paths_teracopy=dialog.use_extended_paths_teracopy_checkbox.isChecked(),
        use_extended_paths_unstoppable=dialog.use_extended_paths_unstoppable_checkbox.isChecked(),
        use_extended_paths_external_copymove=dialog.use_extended_paths_external_copymove_checkbox.isChecked(),
        use_extended_paths_cmd_delete=dialog.use_extended_paths_cmd_delete_checkbox.isChecked(),
        use_extended_paths_powershell_delete=dialog.use_extended_paths_powershell_delete_checkbox.isChecked(),
        use_extended_paths_rimraf=dialog.use_extended_paths_rimraf_checkbox.isChecked(),
        use_extended_paths_external_delete=dialog.use_extended_paths_external_delete_checkbox.isChecked(),
        teracopy_executable=dialog.teracopy_executable_edit.text().strip(),
        unstoppable_executable=dialog.unstoppable_executable_edit.text().strip(),
        generic_copymove_executable=dialog.generic_copymove_executable_edit.text().strip(),
        generic_delete_executable=dialog.generic_delete_executable_edit.text().strip(),
        generic_delete_args_template=dialog.generic_delete_args_edit.text().strip(),
        robocopy_structured_options=backend_state.robocopy_structured_options_from_controls(
            dialog
        ),
        teracopy_structured_options=backend_state.teracopy_structured_options_from_controls(
            dialog
        ),
        unstoppable_structured_options=backend_state.unstoppable_structured_options_from_controls(
            dialog
        ),
        external_copymove_structured_options=(
            backend_state.external_copymove_structured_options_from_controls(dialog)
        ),
        cmd_delete_args=dialog.cmd_delete_args_edit.text().strip(),
        powershell_delete_args=dialog.powershell_delete_args_edit.text().strip(),
        rimraf_executable=dialog.rimraf_executable_edit.text().strip(),
        rimraf_args_template=dialog.rimraf_args_edit.text().strip(),
        app_font_family=str(dialog.app_font_family_combo.currentData() or ""),
        app_font_size_pt=dialog.app_font_size_spin.value(),
        file_list_use_app_font=dialog.file_list_use_app_font_checkbox.isChecked(),
        file_list_font_family=str(
            dialog.file_list_font_family_combo.currentData() or ""
        ),
        file_list_font_size_pt=dialog.file_list_font_size_spin.value(),
        navigation_use_app_font=dialog.navigation_use_app_font_checkbox.isChecked(),
        navigation_font_family=str(
            dialog.navigation_font_family_combo.currentData() or ""
        ),
        navigation_font_size_pt=dialog.navigation_font_size_spin.value(),
        active_panel_tint_color_hex=dialog.active_color_hex,
        active_panel_tint_intensity_percent=dialog.active_intensity_slider.value(),
        target_panel_tint_color_hex=dialog.target_color_hex,
        target_panel_tint_intensity_percent=dialog.target_intensity_slider.value(),
    )
