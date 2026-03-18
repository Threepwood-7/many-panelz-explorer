"""Settings manager facade for UI, operation, and session preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

from threep_commons.settings import (
    QSettingsValueStore,
    SettingsManagerBase,
    delegate_domain_property,
)

from many_panelz_explorer.constants import APP_IDENTITY

from .models import UiPreferences
from .ops_domain import OpsSettingsDomain
from .registry import SettingsRegistry
from .session_domain import SessionSettingsDomain
from .ui_domain import UiSettingsDomain

if TYPE_CHECKING:
    from many_panelz_explorer.ui.window.state_types import SavedViewState


class SettingsManager(SettingsManagerBase, SettingsRegistry):
    """Settings facade composed from UI, operations, and session domains."""

    def __init__(self) -> None:
        super().__init__(QSettingsValueStore.from_identity(APP_IDENTITY))
        self.ui = UiSettingsDomain(self._storage)
        self.ops = OpsSettingsDomain(self._storage)
        self.session = SessionSettingsDomain(self._storage)

    new_context_mode = delegate_domain_property("ui", "new_context_mode")
    show_hidden_default = delegate_domain_property("ui", "show_hidden_default")
    show_root_dropdown = delegate_domain_property("ui", "show_root_dropdown")
    show_storage_overview_status_row = delegate_domain_property(
        "ui", "show_storage_overview_status_row"
    )
    column_width_auto_align_mode = delegate_domain_property(
        "ui", "column_width_auto_align_mode"
    )
    autofit_columns = delegate_domain_property("ui", "autofit_columns")
    show_refresh_button = delegate_domain_property("ui", "show_refresh_button")
    show_root_buttons = delegate_domain_property("ui", "show_root_buttons")
    show_address_bar = delegate_domain_property("ui", "show_address_bar")
    show_navigation_buttons = delegate_domain_property("ui", "show_navigation_buttons")
    show_tab_close_buttons = delegate_domain_property("ui", "show_tab_close_buttons")
    byte_thousands_separator = delegate_domain_property(
        "ui", "byte_thousands_separator"
    )
    byte_decimal_separator = delegate_domain_property("ui", "byte_decimal_separator")
    file_list_byte_format_mode = delegate_domain_property(
        "ui", "file_list_byte_format_mode"
    )
    file_list_byte_custom_template = delegate_domain_property(
        "ui", "file_list_byte_custom_template"
    )
    status_bar_byte_format_mode = delegate_domain_property(
        "ui", "status_bar_byte_format_mode"
    )
    status_bar_byte_custom_template = delegate_domain_property(
        "ui", "status_bar_byte_custom_template"
    )
    status_bar_storage_label_template = delegate_domain_property(
        "ui", "status_bar_storage_label_template"
    )
    properties_byte_format_mode = delegate_domain_property(
        "ui", "properties_byte_format_mode"
    )
    properties_byte_custom_template = delegate_domain_property(
        "ui", "properties_byte_custom_template"
    )
    app_font_family = delegate_domain_property("ui", "app_font_family")
    app_font_size_pt = delegate_domain_property("ui", "app_font_size_pt")
    file_list_use_app_font = delegate_domain_property("ui", "file_list_use_app_font")
    file_list_font_family = delegate_domain_property("ui", "file_list_font_family")
    file_list_font_size_pt = delegate_domain_property("ui", "file_list_font_size_pt")
    navigation_use_app_font = delegate_domain_property("ui", "navigation_use_app_font")
    navigation_font_family = delegate_domain_property("ui", "navigation_font_family")
    navigation_font_size_pt = delegate_domain_property("ui", "navigation_font_size_pt")
    context_immediate_child_scan_cap = delegate_domain_property(
        "ui", "context_immediate_child_scan_cap"
    )
    context_tool_code_editor_exe_path = delegate_domain_property(
        "ui", "context_tool_code_editor_exe_path"
    )
    context_tool_code_editor_args_template = delegate_domain_property(
        "ui", "context_tool_code_editor_args_template"
    )
    context_tool_git_gui_exe_path = delegate_domain_property(
        "ui", "context_tool_git_gui_exe_path"
    )
    context_tool_git_gui_args_template = delegate_domain_property(
        "ui", "context_tool_git_gui_args_template"
    )
    active_panel_tint_color_hex = delegate_domain_property(
        "ui", "active_panel_tint_color_hex"
    )
    active_panel_tint_intensity_percent = delegate_domain_property(
        "ui", "active_panel_tint_intensity_percent"
    )
    target_panel_tint_color_hex = delegate_domain_property(
        "ui", "target_panel_tint_color_hex"
    )
    target_panel_tint_intensity_percent = delegate_domain_property(
        "ui", "target_panel_tint_intensity_percent"
    )

    default_copy_move_backend = delegate_domain_property(
        "ops", "default_copy_move_backend"
    )
    default_delete_backend = delegate_domain_property("ops", "default_delete_backend")
    default_operation_dispatch_mode = delegate_domain_property(
        "ops", "default_operation_dispatch_mode"
    )
    default_operation_conflict_policy = delegate_domain_property(
        "ops", "default_operation_conflict_policy"
    )
    operation_shortcut_behavior = delegate_domain_property(
        "ops", "operation_shortcut_behavior"
    )
    operation_queue_view_mode = delegate_domain_property(
        "ops", "operation_queue_view_mode"
    )
    default_editor_executable = delegate_domain_property(
        "ops", "default_editor_executable"
    )
    default_viewer_executable = delegate_domain_property(
        "ops", "default_viewer_executable"
    )
    default_terminal_launcher = delegate_domain_property(
        "ops", "default_terminal_launcher"
    )
    comspec_terminal_executable = delegate_domain_property(
        "ops", "comspec_terminal_executable"
    )
    comspec_terminal_open_args_template = delegate_domain_property(
        "ops", "comspec_terminal_open_args_template"
    )
    comspec_terminal_command_args_template = delegate_domain_property(
        "ops", "comspec_terminal_command_args_template"
    )
    comspec_terminal_startup_position = delegate_domain_property(
        "ops", "comspec_terminal_startup_position"
    )
    pwsh_terminal_executable = delegate_domain_property(
        "ops", "pwsh_terminal_executable"
    )
    pwsh_terminal_open_args_template = delegate_domain_property(
        "ops", "pwsh_terminal_open_args_template"
    )
    pwsh_terminal_command_args_template = delegate_domain_property(
        "ops", "pwsh_terminal_command_args_template"
    )
    pwsh_terminal_startup_position = delegate_domain_property(
        "ops", "pwsh_terminal_startup_position"
    )
    powershell5_terminal_executable = delegate_domain_property(
        "ops", "powershell5_terminal_executable"
    )
    powershell5_terminal_open_args_template = delegate_domain_property(
        "ops", "powershell5_terminal_open_args_template"
    )
    powershell5_terminal_command_args_template = delegate_domain_property(
        "ops", "powershell5_terminal_command_args_template"
    )
    powershell5_terminal_startup_position = delegate_domain_property(
        "ops", "powershell5_terminal_startup_position"
    )
    file_open_overrides_json = delegate_domain_property(
        "ops", "file_open_overrides_json"
    )
    total_commander_executable = delegate_domain_property(
        "ops", "total_commander_executable"
    )
    total_commander_source_args_template = delegate_domain_property(
        "ops", "total_commander_source_args_template"
    )
    total_commander_source_target_args_template = delegate_domain_property(
        "ops", "total_commander_source_target_args_template"
    )
    double_commander_executable = delegate_domain_property(
        "ops", "double_commander_executable"
    )
    double_commander_source_args_template = delegate_domain_property(
        "ops", "double_commander_source_args_template"
    )
    double_commander_source_target_args_template = delegate_domain_property(
        "ops", "double_commander_source_target_args_template"
    )
    use_extended_paths_robocopy = delegate_domain_property(
        "ops", "use_extended_paths_robocopy"
    )
    use_extended_paths_teracopy = delegate_domain_property(
        "ops", "use_extended_paths_teracopy"
    )
    use_extended_paths_unstoppable = delegate_domain_property(
        "ops", "use_extended_paths_unstoppable"
    )
    use_extended_paths_external_copymove = delegate_domain_property(
        "ops", "use_extended_paths_external_copymove"
    )
    use_extended_paths_cmd_delete = delegate_domain_property(
        "ops", "use_extended_paths_cmd_delete"
    )
    use_extended_paths_powershell_delete = delegate_domain_property(
        "ops", "use_extended_paths_powershell_delete"
    )
    use_extended_paths_rimraf = delegate_domain_property(
        "ops", "use_extended_paths_rimraf"
    )
    use_extended_paths_external_delete = delegate_domain_property(
        "ops", "use_extended_paths_external_delete"
    )
    teracopy_executable = delegate_domain_property("ops", "teracopy_executable")
    unstoppable_executable = delegate_domain_property("ops", "unstoppable_executable")
    generic_copymove_executable = delegate_domain_property(
        "ops", "generic_copymove_executable"
    )
    generic_delete_executable = delegate_domain_property(
        "ops", "generic_delete_executable"
    )
    generic_delete_args_template = delegate_domain_property(
        "ops", "generic_delete_args_template"
    )
    robocopy_structured_options = delegate_domain_property(
        "ops", "robocopy_structured_options"
    )
    teracopy_structured_options = delegate_domain_property(
        "ops", "teracopy_structured_options"
    )
    unstoppable_structured_options = delegate_domain_property(
        "ops", "unstoppable_structured_options"
    )
    external_copymove_structured_options = delegate_domain_property(
        "ops", "external_copymove_structured_options"
    )
    cmd_delete_args = delegate_domain_property("ops", "cmd_delete_args")
    powershell_delete_args = delegate_domain_property("ops", "powershell_delete_args")
    rimraf_executable = delegate_domain_property("ops", "rimraf_executable")
    rimraf_args_template = delegate_domain_property("ops", "rimraf_args_template")
    ops_companion_bootstrap_done = delegate_domain_property(
        "ops", "ops_companion_bootstrap_done"
    )
    settings_dialog_last_section = delegate_domain_property(
        "session", "settings_dialog_last_section"
    )
    settings_dialog_last_subsection = delegate_domain_property(
        "session", "settings_dialog_last_subsection"
    )

    def ui_preferences(self) -> UiPreferences:
        return UiPreferences(
            new_context_mode=self.new_context_mode,
            show_hidden_default=self.show_hidden_default,
            show_root_dropdown=self.show_root_dropdown,
            show_storage_overview_status_row=self.show_storage_overview_status_row,
            column_width_auto_align_mode=self.column_width_auto_align_mode,
            autofit_columns=self.autofit_columns,
            show_refresh_button=self.show_refresh_button,
            show_root_buttons=self.show_root_buttons,
            show_address_bar=self.show_address_bar,
            show_navigation_buttons=self.show_navigation_buttons,
            show_tab_close_buttons=self.show_tab_close_buttons,
            byte_thousands_separator=self.byte_thousands_separator,
            byte_decimal_separator=self.byte_decimal_separator,
            file_list_byte_format_mode=self.file_list_byte_format_mode,
            file_list_byte_custom_template=self.file_list_byte_custom_template,
            status_bar_byte_format_mode=self.status_bar_byte_format_mode,
            status_bar_byte_custom_template=self.status_bar_byte_custom_template,
            status_bar_storage_label_template=self.status_bar_storage_label_template,
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
            default_terminal_launcher=self.default_terminal_launcher,
            comspec_terminal_executable=self.comspec_terminal_executable,
            comspec_terminal_open_args_template=self.comspec_terminal_open_args_template,
            comspec_terminal_command_args_template=(
                self.comspec_terminal_command_args_template
            ),
            comspec_terminal_startup_position=self.comspec_terminal_startup_position,
            pwsh_terminal_executable=self.pwsh_terminal_executable,
            pwsh_terminal_open_args_template=self.pwsh_terminal_open_args_template,
            pwsh_terminal_command_args_template=(
                self.pwsh_terminal_command_args_template
            ),
            pwsh_terminal_startup_position=self.pwsh_terminal_startup_position,
            powershell5_terminal_executable=self.powershell5_terminal_executable,
            powershell5_terminal_open_args_template=(
                self.powershell5_terminal_open_args_template
            ),
            powershell5_terminal_command_args_template=(
                self.powershell5_terminal_command_args_template
            ),
            powershell5_terminal_startup_position=(
                self.powershell5_terminal_startup_position
            ),
            file_open_overrides_json=self.file_open_overrides_json,
            total_commander_executable=self.total_commander_executable,
            total_commander_source_args_template=self.total_commander_source_args_template,
            total_commander_source_target_args_template=(
                self.total_commander_source_target_args_template
            ),
            double_commander_executable=self.double_commander_executable,
            double_commander_source_args_template=(
                self.double_commander_source_args_template
            ),
            double_commander_source_target_args_template=(
                self.double_commander_source_target_args_template
            ),
            use_extended_paths_robocopy=self.use_extended_paths_robocopy,
            use_extended_paths_teracopy=self.use_extended_paths_teracopy,
            use_extended_paths_unstoppable=self.use_extended_paths_unstoppable,
            use_extended_paths_external_copymove=self.use_extended_paths_external_copymove,
            use_extended_paths_cmd_delete=self.use_extended_paths_cmd_delete,
            use_extended_paths_powershell_delete=self.use_extended_paths_powershell_delete,
            use_extended_paths_rimraf=self.use_extended_paths_rimraf,
            use_extended_paths_external_delete=self.use_extended_paths_external_delete,
            teracopy_executable=self.teracopy_executable,
            unstoppable_executable=self.unstoppable_executable,
            generic_copymove_executable=self.generic_copymove_executable,
            generic_delete_executable=self.generic_delete_executable,
            generic_delete_args_template=self.generic_delete_args_template,
            robocopy_structured_options=self.robocopy_structured_options,
            teracopy_structured_options=self.teracopy_structured_options,
            unstoppable_structured_options=self.unstoppable_structured_options,
            external_copymove_structured_options=self.external_copymove_structured_options,
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
        self.autofit_columns = preferences.autofit_columns
        self.show_refresh_button = preferences.show_refresh_button
        self.show_root_buttons = preferences.show_root_buttons
        self.show_address_bar = preferences.show_address_bar
        self.show_navigation_buttons = preferences.show_navigation_buttons
        self.show_tab_close_buttons = preferences.show_tab_close_buttons
        self.ui.set_byte_separators(
            preferences.byte_thousands_separator,
            preferences.byte_decimal_separator,
        )
        self.file_list_byte_format_mode = preferences.file_list_byte_format_mode
        self.file_list_byte_custom_template = preferences.file_list_byte_custom_template
        self.status_bar_byte_format_mode = preferences.status_bar_byte_format_mode
        self.status_bar_byte_custom_template = (
            preferences.status_bar_byte_custom_template
        )
        self.status_bar_storage_label_template = (
            preferences.status_bar_storage_label_template
        )
        self.properties_byte_format_mode = preferences.properties_byte_format_mode
        self.properties_byte_custom_template = (
            preferences.properties_byte_custom_template
        )
        self.app_font_family = preferences.app_font_family
        self.app_font_size_pt = preferences.app_font_size_pt
        self.file_list_use_app_font = preferences.file_list_use_app_font
        self.file_list_font_family = preferences.file_list_font_family
        self.file_list_font_size_pt = preferences.file_list_font_size_pt
        self.navigation_use_app_font = preferences.navigation_use_app_font
        self.navigation_font_family = preferences.navigation_font_family
        self.navigation_font_size_pt = preferences.navigation_font_size_pt
        self.context_immediate_child_scan_cap = (
            preferences.context_immediate_child_scan_cap
        )
        self.context_tool_code_editor_exe_path = (
            preferences.context_tool_code_editor_exe_path
        )
        self.context_tool_code_editor_args_template = (
            preferences.context_tool_code_editor_args_template
        )
        self.context_tool_git_gui_exe_path = preferences.context_tool_git_gui_exe_path
        self.context_tool_git_gui_args_template = (
            preferences.context_tool_git_gui_args_template
        )
        self.active_panel_tint_color_hex = preferences.active_panel_tint_color_hex
        self.active_panel_tint_intensity_percent = (
            preferences.active_panel_tint_intensity_percent
        )
        self.target_panel_tint_color_hex = preferences.target_panel_tint_color_hex
        self.target_panel_tint_intensity_percent = (
            preferences.target_panel_tint_intensity_percent
        )
        self.default_copy_move_backend = preferences.default_copy_move_backend
        self.default_delete_backend = preferences.default_delete_backend
        self.default_operation_dispatch_mode = (
            preferences.default_operation_dispatch_mode
        )
        self.default_operation_conflict_policy = (
            preferences.default_operation_conflict_policy
        )
        self.operation_shortcut_behavior = preferences.operation_shortcut_behavior
        self.operation_queue_view_mode = preferences.operation_queue_view_mode
        self.default_editor_executable = preferences.default_editor_executable
        self.default_viewer_executable = preferences.default_viewer_executable
        self.default_terminal_launcher = preferences.default_terminal_launcher
        self.comspec_terminal_executable = preferences.comspec_terminal_executable
        self.comspec_terminal_open_args_template = (
            preferences.comspec_terminal_open_args_template
        )
        self.comspec_terminal_command_args_template = (
            preferences.comspec_terminal_command_args_template
        )
        self.comspec_terminal_startup_position = (
            preferences.comspec_terminal_startup_position
        )
        self.pwsh_terminal_executable = preferences.pwsh_terminal_executable
        self.pwsh_terminal_open_args_template = (
            preferences.pwsh_terminal_open_args_template
        )
        self.pwsh_terminal_command_args_template = (
            preferences.pwsh_terminal_command_args_template
        )
        self.pwsh_terminal_startup_position = preferences.pwsh_terminal_startup_position
        self.powershell5_terminal_executable = (
            preferences.powershell5_terminal_executable
        )
        self.powershell5_terminal_open_args_template = (
            preferences.powershell5_terminal_open_args_template
        )
        self.powershell5_terminal_command_args_template = (
            preferences.powershell5_terminal_command_args_template
        )
        self.powershell5_terminal_startup_position = (
            preferences.powershell5_terminal_startup_position
        )
        self.file_open_overrides_json = preferences.file_open_overrides_json
        self.total_commander_executable = preferences.total_commander_executable
        self.total_commander_source_args_template = (
            preferences.total_commander_source_args_template
        )
        self.total_commander_source_target_args_template = (
            preferences.total_commander_source_target_args_template
        )
        self.double_commander_executable = preferences.double_commander_executable
        self.double_commander_source_args_template = (
            preferences.double_commander_source_args_template
        )
        self.double_commander_source_target_args_template = (
            preferences.double_commander_source_target_args_template
        )
        self.use_extended_paths_robocopy = preferences.use_extended_paths_robocopy
        self.use_extended_paths_teracopy = preferences.use_extended_paths_teracopy
        self.use_extended_paths_unstoppable = preferences.use_extended_paths_unstoppable
        self.use_extended_paths_external_copymove = (
            preferences.use_extended_paths_external_copymove
        )
        self.use_extended_paths_cmd_delete = preferences.use_extended_paths_cmd_delete
        self.use_extended_paths_powershell_delete = (
            preferences.use_extended_paths_powershell_delete
        )
        self.use_extended_paths_rimraf = preferences.use_extended_paths_rimraf
        self.use_extended_paths_external_delete = (
            preferences.use_extended_paths_external_delete
        )
        self.teracopy_executable = preferences.teracopy_executable
        self.unstoppable_executable = preferences.unstoppable_executable
        self.generic_copymove_executable = preferences.generic_copymove_executable
        self.generic_delete_executable = preferences.generic_delete_executable
        self.generic_delete_args_template = preferences.generic_delete_args_template
        self.robocopy_structured_options = preferences.robocopy_structured_options
        self.teracopy_structured_options = preferences.teracopy_structured_options
        self.unstoppable_structured_options = preferences.unstoppable_structured_options
        self.external_copymove_structured_options = (
            preferences.external_copymove_structured_options
        )
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

    def get_saved_view(self, name: str) -> SavedViewState | None:
        return self.session.get_saved_view(name)

    def set_saved_view(self, name: str, payload: object) -> None:
        self.session.set_saved_view(name, payload)
