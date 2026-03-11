from __future__ import annotations

from dataclasses import dataclass

from many_panelz_explorer._operations.types import (
    BACKEND_PYTHON,
    BACKEND_RECYCLE_BIN,
    DEFAULT_CMD_DELETE_ARGS,
    DEFAULT_GENERIC_COPYMOVE_ARGS,
    DEFAULT_GENERIC_COPYMOVE_EXE,
    DEFAULT_GENERIC_DELETE_ARGS,
    DEFAULT_GENERIC_DELETE_EXE,
    DEFAULT_POWERSHELL_DELETE_ARGS,
    DEFAULT_RIMRAF_ARGS,
    DEFAULT_RIMRAF_EXE,
    DEFAULT_ROBOCOPY_COPY_ARGS,
    DEFAULT_ROBOCOPY_MOVE_ARGS,
    DEFAULT_TERA_COPY_ARGS,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_ARGS,
    DEFAULT_UNSTOPPABLE_EXE,
    DISPATCH_MODE_QUEUE,
    QUEUE_VIEW_DOCK,
    SHORTCUT_BEHAVIOR_DIRECT,
)


@dataclass(frozen=True)
class UiPreferences:
    new_context_mode: str = "clone_active_path"
    show_hidden_default: bool = True
    show_root_dropdown: bool = False
    show_storage_overview_status_row: bool = True
    column_width_auto_align_mode: str = "current_panel_tabs"
    show_refresh_button: bool = True
    show_root_buttons: bool = True
    show_address_bar: bool = True
    show_navigation_buttons: bool = True
    byte_thousands_separator: str = ","
    byte_decimal_separator: str = "."
    file_list_byte_format_mode: str = "bytes"
    file_list_byte_custom_template: str = ""
    status_bar_byte_format_mode: str = "bytes"
    status_bar_byte_custom_template: str = ""
    status_bar_storage_label_template: str = (
        "{disk_root} {disk_label} {used_space}/{total_space}"
    )
    properties_byte_format_mode: str = "bytes"
    properties_byte_custom_template: str = ""
    app_font_family: str = ""
    app_font_size_pt: int = 0
    file_list_use_app_font: bool = True
    file_list_font_family: str = ""
    file_list_font_size_pt: int = 10
    navigation_use_app_font: bool = True
    navigation_font_family: str = ""
    navigation_font_size_pt: int = 10
    context_immediate_child_scan_cap: int = 33
    context_tool_code_editor_exe_path: str = ""
    context_tool_code_editor_args_template: str = "{folder}"
    context_tool_git_gui_exe_path: str = ""
    context_tool_git_gui_args_template: str = "{folder}"
    active_panel_tint_color_hex: str = "#A8B6C4"
    active_panel_tint_intensity_percent: int = 24
    target_panel_tint_color_hex: str = "#D2CCAA"
    target_panel_tint_intensity_percent: int = 28
    default_copy_move_backend: str = BACKEND_PYTHON
    default_delete_backend: str = BACKEND_RECYCLE_BIN
    default_operation_dispatch_mode: str = DISPATCH_MODE_QUEUE
    default_operation_conflict_policy: str = "rename"
    operation_shortcut_behavior: str = SHORTCUT_BEHAVIOR_DIRECT
    operation_queue_view_mode: str = QUEUE_VIEW_DOCK
    default_editor_executable: str = ""
    default_viewer_executable: str = ""
    file_open_overrides_json: str = "{}"
    use_extended_paths_robocopy: bool = False
    use_extended_paths_teracopy: bool = False
    use_extended_paths_unstoppable: bool = False
    use_extended_paths_external_copymove: bool = False
    use_extended_paths_cmd_delete: bool = False
    use_extended_paths_powershell_delete: bool = False
    use_extended_paths_rimraf: bool = False
    use_extended_paths_external_delete: bool = False
    script_editor_executable: str = ""
    teracopy_executable: str = DEFAULT_TERA_COPY_EXE
    teracopy_args_template: str = DEFAULT_TERA_COPY_ARGS
    unstoppable_executable: str = DEFAULT_UNSTOPPABLE_EXE
    unstoppable_args_template: str = DEFAULT_UNSTOPPABLE_ARGS
    generic_copymove_executable: str = DEFAULT_GENERIC_COPYMOVE_EXE
    generic_copymove_args_template: str = DEFAULT_GENERIC_COPYMOVE_ARGS
    generic_delete_executable: str = DEFAULT_GENERIC_DELETE_EXE
    generic_delete_args_template: str = DEFAULT_GENERIC_DELETE_ARGS
    robocopy_copy_args: str = DEFAULT_ROBOCOPY_COPY_ARGS
    robocopy_move_args: str = DEFAULT_ROBOCOPY_MOVE_ARGS
    cmd_delete_args: str = DEFAULT_CMD_DELETE_ARGS
    powershell_delete_args: str = DEFAULT_POWERSHELL_DELETE_ARGS
    rimraf_executable: str = DEFAULT_RIMRAF_EXE
    rimraf_args_template: str = DEFAULT_RIMRAF_ARGS
