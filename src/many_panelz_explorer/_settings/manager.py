from __future__ import annotations

from typing import Any, TypeVar

from .domains import OpsSettingsDomain, SessionSettingsDomain, UiSettingsDomain
from .models import UiPreferences
from .registry import SettingsRegistry
from .storage import SettingsStorage


_Domain = TypeVar("_Domain")


def _delegate_property(domain_attr: str, name: str) -> property:
    return property(
        lambda self: getattr(getattr(self, domain_attr), name),
        lambda self, value: setattr(getattr(self, domain_attr), name, value),
    )


class SettingsManager(SettingsRegistry):
    """Settings facade composed from UI, operations, and session domains."""

    def __init__(self) -> None:
        self._storage = SettingsStorage()
        self.ui = UiSettingsDomain(self._storage)
        self.ops = OpsSettingsDomain(self._storage)
        self.session = SessionSettingsDomain(self._storage)
        self.settings_path = self._storage.settings_path

    def sync(self) -> None:
        self._storage.sync()

    def value(self, key: str, default: Any = None) -> Any:
        return self._storage.value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self._storage.set_value(key, value)

    def remove(self, key: str) -> None:
        self._storage.remove(key)

    def set_json(self, key: str, value: Any) -> None:
        self._storage.set_json(key, value)

    def get_json(self, key: str, default: Any) -> Any:
        return self._storage.get_json(key, default)

    new_context_mode = _delegate_property("ui", "new_context_mode")
    show_hidden_default = _delegate_property("ui", "show_hidden_default")
    show_root_dropdown = _delegate_property("ui", "show_root_dropdown")
    show_storage_overview_status_row = _delegate_property(
        "ui", "show_storage_overview_status_row"
    )
    column_width_auto_align_mode = _delegate_property("ui", "column_width_auto_align_mode")
    show_refresh_button = _delegate_property("ui", "show_refresh_button")
    show_root_buttons = _delegate_property("ui", "show_root_buttons")
    show_address_bar = _delegate_property("ui", "show_address_bar")
    show_navigation_buttons = _delegate_property("ui", "show_navigation_buttons")
    byte_thousands_separator = _delegate_property("ui", "byte_thousands_separator")
    byte_decimal_separator = _delegate_property("ui", "byte_decimal_separator")
    file_list_byte_format_mode = _delegate_property("ui", "file_list_byte_format_mode")
    file_list_byte_custom_template = _delegate_property("ui", "file_list_byte_custom_template")
    status_bar_byte_format_mode = _delegate_property("ui", "status_bar_byte_format_mode")
    status_bar_byte_custom_template = _delegate_property("ui", "status_bar_byte_custom_template")
    properties_byte_format_mode = _delegate_property("ui", "properties_byte_format_mode")
    properties_byte_custom_template = _delegate_property("ui", "properties_byte_custom_template")
    app_font_family = _delegate_property("ui", "app_font_family")
    app_font_size_pt = _delegate_property("ui", "app_font_size_pt")
    file_list_use_app_font = _delegate_property("ui", "file_list_use_app_font")
    file_list_font_family = _delegate_property("ui", "file_list_font_family")
    file_list_font_size_pt = _delegate_property("ui", "file_list_font_size_pt")
    navigation_use_app_font = _delegate_property("ui", "navigation_use_app_font")
    navigation_font_family = _delegate_property("ui", "navigation_font_family")
    navigation_font_size_pt = _delegate_property("ui", "navigation_font_size_pt")
    context_immediate_child_scan_cap = _delegate_property("ui", "context_immediate_child_scan_cap")
    context_tool_code_editor_exe_path = _delegate_property("ui", "context_tool_code_editor_exe_path")
    context_tool_code_editor_args_template = _delegate_property("ui", "context_tool_code_editor_args_template")
    context_tool_git_gui_exe_path = _delegate_property("ui", "context_tool_git_gui_exe_path")
    context_tool_git_gui_args_template = _delegate_property("ui", "context_tool_git_gui_args_template")
    active_panel_tint_color_hex = _delegate_property("ui", "active_panel_tint_color_hex")
    active_panel_tint_intensity_percent = _delegate_property(
        "ui", "active_panel_tint_intensity_percent"
    )
    target_panel_tint_color_hex = _delegate_property("ui", "target_panel_tint_color_hex")
    target_panel_tint_intensity_percent = _delegate_property(
        "ui", "target_panel_tint_intensity_percent"
    )

    default_copy_move_backend = _delegate_property("ops", "default_copy_move_backend")
    default_delete_backend = _delegate_property("ops", "default_delete_backend")
    default_operation_dispatch_mode = _delegate_property("ops", "default_operation_dispatch_mode")
    default_operation_conflict_policy = _delegate_property("ops", "default_operation_conflict_policy")
    operation_shortcut_behavior = _delegate_property("ops", "operation_shortcut_behavior")
    operation_queue_view_mode = _delegate_property("ops", "operation_queue_view_mode")
    default_editor_executable = _delegate_property("ops", "default_editor_executable")
    default_viewer_executable = _delegate_property("ops", "default_viewer_executable")
    file_open_overrides_json = _delegate_property("ops", "file_open_overrides_json")
    use_extended_paths_robocopy = _delegate_property("ops", "use_extended_paths_robocopy")
    use_extended_paths_teracopy = _delegate_property("ops", "use_extended_paths_teracopy")
    use_extended_paths_unstoppable = _delegate_property("ops", "use_extended_paths_unstoppable")
    use_extended_paths_external_copymove = _delegate_property(
        "ops", "use_extended_paths_external_copymove"
    )
    use_extended_paths_cmd_delete = _delegate_property("ops", "use_extended_paths_cmd_delete")
    use_extended_paths_powershell_delete = _delegate_property(
        "ops", "use_extended_paths_powershell_delete"
    )
    use_extended_paths_rimraf = _delegate_property("ops", "use_extended_paths_rimraf")
    use_extended_paths_external_delete = _delegate_property("ops", "use_extended_paths_external_delete")
    script_editor_executable = _delegate_property("ops", "script_editor_executable")
    teracopy_executable = _delegate_property("ops", "teracopy_executable")
    teracopy_args_template = _delegate_property("ops", "teracopy_args_template")
    unstoppable_executable = _delegate_property("ops", "unstoppable_executable")
    unstoppable_args_template = _delegate_property("ops", "unstoppable_args_template")
    generic_copymove_executable = _delegate_property("ops", "generic_copymove_executable")
    generic_copymove_args_template = _delegate_property("ops", "generic_copymove_args_template")
    generic_delete_executable = _delegate_property("ops", "generic_delete_executable")
    generic_delete_args_template = _delegate_property("ops", "generic_delete_args_template")
    robocopy_copy_args = _delegate_property("ops", "robocopy_copy_args")
    robocopy_move_args = _delegate_property("ops", "robocopy_move_args")
    cmd_delete_args = _delegate_property("ops", "cmd_delete_args")
    powershell_delete_args = _delegate_property("ops", "powershell_delete_args")
    rimraf_executable = _delegate_property("ops", "rimraf_executable")
    rimraf_args_template = _delegate_property("ops", "rimraf_args_template")
    ops_companion_bootstrap_done = _delegate_property("ops", "ops_companion_bootstrap_done")

    def ui_preferences(self) -> UiPreferences:
        return UiPreferences(
            new_context_mode=self.new_context_mode,
            show_hidden_default=self.show_hidden_default,
            show_root_dropdown=self.show_root_dropdown,
            show_storage_overview_status_row=self.show_storage_overview_status_row,
            column_width_auto_align_mode=self.column_width_auto_align_mode,
            show_refresh_button=self.show_refresh_button,
            show_root_buttons=self.show_root_buttons,
            show_address_bar=self.show_address_bar,
            show_navigation_buttons=self.show_navigation_buttons,
            byte_thousands_separator=self.byte_thousands_separator,
            byte_decimal_separator=self.byte_decimal_separator,
            file_list_byte_format_mode=self.file_list_byte_format_mode,
            file_list_byte_custom_template=self.file_list_byte_custom_template,
            status_bar_byte_format_mode=self.status_bar_byte_format_mode,
            status_bar_byte_custom_template=self.status_bar_byte_custom_template,
            properties_byte_format_mode=self.properties_byte_format_mode,
            properties_byte_custom_template=self.properties_byte_custom_template,
            app_font_family=self.app_font_family,
            app_font_size_pt=self.app_font_size_pt,
            file_list_use_app_font=self.file_list_use_app_font,
            file_list_font_family=self.file_list_font_family,
            file_list_font_size_pt=self.file_list_font_size_pt,
            navigation_use_app_font=self.navigation_use_app_font,
            navigation_font_family=self.navigation_font_family,
            navigation_font_size_pt=self.navigation_font_size_pt,
            context_immediate_child_scan_cap=self.context_immediate_child_scan_cap,
            context_tool_code_editor_exe_path=self.context_tool_code_editor_exe_path,
            context_tool_code_editor_args_template=self.context_tool_code_editor_args_template,
            context_tool_git_gui_exe_path=self.context_tool_git_gui_exe_path,
            context_tool_git_gui_args_template=self.context_tool_git_gui_args_template,
            active_panel_tint_color_hex=self.active_panel_tint_color_hex,
            active_panel_tint_intensity_percent=self.active_panel_tint_intensity_percent,
            target_panel_tint_color_hex=self.target_panel_tint_color_hex,
            target_panel_tint_intensity_percent=self.target_panel_tint_intensity_percent,
            default_copy_move_backend=self.default_copy_move_backend,
            default_delete_backend=self.default_delete_backend,
            default_operation_dispatch_mode=self.default_operation_dispatch_mode,
            default_operation_conflict_policy=self.default_operation_conflict_policy,
            operation_shortcut_behavior=self.operation_shortcut_behavior,
            operation_queue_view_mode=self.operation_queue_view_mode,
            default_editor_executable=self.default_editor_executable,
            default_viewer_executable=self.default_viewer_executable,
            file_open_overrides_json=self.file_open_overrides_json,
            use_extended_paths_robocopy=self.use_extended_paths_robocopy,
            use_extended_paths_teracopy=self.use_extended_paths_teracopy,
            use_extended_paths_unstoppable=self.use_extended_paths_unstoppable,
            use_extended_paths_external_copymove=self.use_extended_paths_external_copymove,
            use_extended_paths_cmd_delete=self.use_extended_paths_cmd_delete,
            use_extended_paths_powershell_delete=self.use_extended_paths_powershell_delete,
            use_extended_paths_rimraf=self.use_extended_paths_rimraf,
            use_extended_paths_external_delete=self.use_extended_paths_external_delete,
            script_editor_executable=self.script_editor_executable,
            teracopy_executable=self.teracopy_executable,
            teracopy_args_template=self.teracopy_args_template,
            unstoppable_executable=self.unstoppable_executable,
            unstoppable_args_template=self.unstoppable_args_template,
            generic_copymove_executable=self.generic_copymove_executable,
            generic_copymove_args_template=self.generic_copymove_args_template,
            generic_delete_executable=self.generic_delete_executable,
            generic_delete_args_template=self.generic_delete_args_template,
            robocopy_copy_args=self.robocopy_copy_args,
            robocopy_move_args=self.robocopy_move_args,
            cmd_delete_args=self.cmd_delete_args,
            powershell_delete_args=self.powershell_delete_args,
            rimraf_executable=self.rimraf_executable,
            rimraf_args_template=self.rimraf_args_template,
        )

    def set_ui_preferences(self, preferences: UiPreferences) -> None:
        self.new_context_mode = preferences.new_context_mode
        self.show_hidden_default = preferences.show_hidden_default
        self.show_root_dropdown = preferences.show_root_dropdown
        self.show_storage_overview_status_row = (
            preferences.show_storage_overview_status_row
        )
        self.column_width_auto_align_mode = preferences.column_width_auto_align_mode
        self.show_refresh_button = preferences.show_refresh_button
        self.show_root_buttons = preferences.show_root_buttons
        self.show_address_bar = preferences.show_address_bar
        self.show_navigation_buttons = preferences.show_navigation_buttons
        self.byte_thousands_separator = preferences.byte_thousands_separator
        self.byte_decimal_separator = preferences.byte_decimal_separator
        self.file_list_byte_format_mode = preferences.file_list_byte_format_mode
        self.file_list_byte_custom_template = preferences.file_list_byte_custom_template
        self.status_bar_byte_format_mode = preferences.status_bar_byte_format_mode
        self.status_bar_byte_custom_template = preferences.status_bar_byte_custom_template
        self.properties_byte_format_mode = preferences.properties_byte_format_mode
        self.properties_byte_custom_template = preferences.properties_byte_custom_template
        self.app_font_family = preferences.app_font_family
        self.app_font_size_pt = preferences.app_font_size_pt
        self.file_list_use_app_font = preferences.file_list_use_app_font
        self.file_list_font_family = preferences.file_list_font_family
        self.file_list_font_size_pt = preferences.file_list_font_size_pt
        self.navigation_use_app_font = preferences.navigation_use_app_font
        self.navigation_font_family = preferences.navigation_font_family
        self.navigation_font_size_pt = preferences.navigation_font_size_pt
        self.context_immediate_child_scan_cap = preferences.context_immediate_child_scan_cap
        self.context_tool_code_editor_exe_path = preferences.context_tool_code_editor_exe_path
        self.context_tool_code_editor_args_template = (
            preferences.context_tool_code_editor_args_template
        )
        self.context_tool_git_gui_exe_path = preferences.context_tool_git_gui_exe_path
        self.context_tool_git_gui_args_template = preferences.context_tool_git_gui_args_template
        self.active_panel_tint_color_hex = preferences.active_panel_tint_color_hex
        self.active_panel_tint_intensity_percent = preferences.active_panel_tint_intensity_percent
        self.target_panel_tint_color_hex = preferences.target_panel_tint_color_hex
        self.target_panel_tint_intensity_percent = preferences.target_panel_tint_intensity_percent
        self.default_copy_move_backend = preferences.default_copy_move_backend
        self.default_delete_backend = preferences.default_delete_backend
        self.default_operation_dispatch_mode = preferences.default_operation_dispatch_mode
        self.default_operation_conflict_policy = preferences.default_operation_conflict_policy
        self.operation_shortcut_behavior = preferences.operation_shortcut_behavior
        self.operation_queue_view_mode = preferences.operation_queue_view_mode
        self.default_editor_executable = preferences.default_editor_executable
        self.default_viewer_executable = preferences.default_viewer_executable
        self.file_open_overrides_json = preferences.file_open_overrides_json
        self.use_extended_paths_robocopy = preferences.use_extended_paths_robocopy
        self.use_extended_paths_teracopy = preferences.use_extended_paths_teracopy
        self.use_extended_paths_unstoppable = preferences.use_extended_paths_unstoppable
        self.use_extended_paths_external_copymove = preferences.use_extended_paths_external_copymove
        self.use_extended_paths_cmd_delete = preferences.use_extended_paths_cmd_delete
        self.use_extended_paths_powershell_delete = preferences.use_extended_paths_powershell_delete
        self.use_extended_paths_rimraf = preferences.use_extended_paths_rimraf
        self.use_extended_paths_external_delete = preferences.use_extended_paths_external_delete
        self.script_editor_executable = preferences.script_editor_executable
        self.teracopy_executable = preferences.teracopy_executable
        self.teracopy_args_template = preferences.teracopy_args_template
        self.unstoppable_executable = preferences.unstoppable_executable
        self.unstoppable_args_template = preferences.unstoppable_args_template
        self.generic_copymove_executable = preferences.generic_copymove_executable
        self.generic_copymove_args_template = preferences.generic_copymove_args_template
        self.generic_delete_executable = preferences.generic_delete_executable
        self.generic_delete_args_template = preferences.generic_delete_args_template
        self.robocopy_copy_args = preferences.robocopy_copy_args
        self.robocopy_move_args = preferences.robocopy_move_args
        self.cmd_delete_args = preferences.cmd_delete_args
        self.powershell_delete_args = preferences.powershell_delete_args
        self.rimraf_executable = preferences.rimraf_executable
        self.rimraf_args_template = preferences.rimraf_args_template

    def window_key(self, window_id: str, suffix: str) -> str:
        return self.session.window_key(window_id, suffix)

    def session_window_ids(self) -> list[str]:
        return self.session.session_window_ids()

    def set_session_window_ids(self, window_ids: list[str]) -> None:
        self.session.set_session_window_ids(window_ids)

    def list_saved_views(self) -> list[str]:
        return self.session.list_saved_views()

    def get_saved_view(self, name: str) -> dict[str, Any] | None:
        return self.session.get_saved_view(name)

    def set_saved_view(self, name: str, payload: dict[str, Any]) -> None:
        self.session.set_saved_view(name, payload)
