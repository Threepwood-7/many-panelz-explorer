"""Shared settings keys, defaults, and allowed value sets."""

from __future__ import annotations

from typing import ClassVar

from many_panelz_explorer._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    external_copymove_options_payload,
    robocopy_options_payload,
    teracopy_options_payload,
    unstoppable_options_payload,
)
from many_panelz_explorer._operations.types import (
    BACKEND_PYTHON,
    BACKEND_RECYCLE_BIN,
    DEFAULT_CMD_DELETE_ARGS,
    DEFAULT_COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE,
    DEFAULT_COMSPEC_TERMINAL_EXECUTABLE,
    DEFAULT_COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE,
    DEFAULT_GENERIC_COPYMOVE_EXE,
    DEFAULT_GENERIC_DELETE_ARGS,
    DEFAULT_GENERIC_DELETE_EXE,
    DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE,
    DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE,
    DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE,
    DEFAULT_POWERSHELL_DELETE_ARGS,
    DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE,
    DEFAULT_PWSH_TERMINAL_EXECUTABLE,
    DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE,
    DEFAULT_RIMRAF_ARGS,
    DEFAULT_RIMRAF_EXE,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_TERMINAL_LAUNCHER,
    DEFAULT_UNSTOPPABLE_EXE,
    DISPATCH_MODE_QUEUE,
    QUEUE_VIEW_DOCK,
    SHORTCUT_BEHAVIOR_DIRECT,
)
from many_panelz_explorer.external_file_managers import (
    DEFAULT_DOUBLE_COMMANDER_EXECUTABLE,
    DEFAULT_DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE,
    DEFAULT_DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE,
    DEFAULT_TOTAL_COMMANDER_EXECUTABLE,
    DEFAULT_TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE,
    DEFAULT_TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE,
)


class SettingsRegistry:
    """Central registry of persisted settings keys and default values."""

    NEW_CONTEXT_MODE_KEY = "config/new_context_mode"
    SHOW_HIDDEN_DEFAULT_KEY = "ui/show_hidden_default"
    SHOW_ROOT_DROPDOWN_KEY = "ui/show_root_dropdown"
    SHOW_STORAGE_OVERVIEW_STATUS_ROW_KEY = "ui/show_storage_overview_status_row"
    COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY = "ui/file_list/column_width_auto_align_mode"
    AUTOFIT_COLUMNS_KEY = "ui/file_list/autofit_columns"
    SHOW_REFRESH_BUTTON_KEY = "ui/show_refresh_button"
    SHOW_ROOT_BUTTONS_KEY = "ui/show_root_buttons"
    SHOW_ADDRESS_BAR_KEY = "ui/show_address_bar"
    SHOW_NAVIGATION_BUTTONS_KEY = "ui/show_navigation_buttons"
    BYTES_THOUSANDS_SEPARATOR_KEY = "ui/bytes/separators/thousands"
    BYTES_DECIMAL_SEPARATOR_KEY = "ui/bytes/separators/decimal"
    FILE_LIST_BYTE_FORMAT_MODE_KEY = "ui/bytes/file_list/mode"
    FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY = "ui/bytes/file_list/custom_template"
    STATUS_BAR_BYTE_FORMAT_MODE_KEY = "ui/bytes/status_bar/mode"
    STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY = "ui/bytes/status_bar/custom_template"
    STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY = "ui/status_bar/storage/label_template"
    PROPERTIES_BYTE_FORMAT_MODE_KEY = "ui/bytes/properties/mode"
    PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY = "ui/bytes/properties/custom_template"
    APP_FONT_FAMILY_KEY = "ui/font/app/family"
    APP_FONT_SIZE_PT_KEY = "ui/font/app/size_pt"
    FILE_LIST_USE_APP_FONT_KEY = "ui/font/file_list/use_app_font"
    FILE_LIST_FONT_FAMILY_KEY = "ui/font/file_list/family"
    FILE_LIST_FONT_SIZE_PT_KEY = "ui/font/file_list/size_pt"
    NAVIGATION_USE_APP_FONT_KEY = "ui/font/navigation/use_app_font"
    NAVIGATION_FONT_FAMILY_KEY = "ui/font/navigation/family"
    NAVIGATION_FONT_SIZE_PT_KEY = "ui/font/navigation/size_pt"
    CONTEXT_IMMEDIATE_CHILD_SCAN_CAP_KEY = "context/detection/immediate_child_scan_cap"
    CONTEXT_TOOL_CODE_EDITOR_EXE_PATH_KEY = "context/tools/code_editor/exe_path"
    CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE_KEY = (
        "context/tools/code_editor/args_template"
    )
    CONTEXT_TOOL_GIT_GUI_EXE_PATH_KEY = "context/tools/git_gui/exe_path"
    CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE_KEY = "context/tools/git_gui/args_template"
    ACTIVE_PANEL_TINT_COLOR_KEY = "ui/panel_tint/active_color_hex"
    ACTIVE_PANEL_TINT_INTENSITY_KEY = "ui/panel_tint/active_intensity_percent"
    TARGET_PANEL_TINT_COLOR_KEY = "ui/panel_tint/target_color_hex"
    TARGET_PANEL_TINT_INTENSITY_KEY = "ui/panel_tint/target_intensity_percent"
    DEFAULT_COPY_MOVE_BACKEND_KEY = "ops/default_copy_move_backend"
    DEFAULT_DELETE_BACKEND_KEY = "ops/default_delete_backend"
    DEFAULT_OPERATION_DISPATCH_MODE_KEY = "ops/default_dispatch_mode"
    DEFAULT_OPERATION_CONFLICT_POLICY_KEY = "ops/default_conflict_policy"
    OPERATION_SHORTCUT_BEHAVIOR_KEY = "ops/shortcut_behavior"
    OPERATION_QUEUE_VIEW_MODE_KEY = "ops/queue_view_mode"
    DEFAULT_EDITOR_EXECUTABLE_KEY = "ops/open/default_editor_executable"
    DEFAULT_VIEWER_EXECUTABLE_KEY = "ops/open/default_viewer_executable"
    DEFAULT_TERMINAL_LAUNCHER_KEY = "ops/open/default_terminal_launcher"
    COMSPEC_TERMINAL_EXECUTABLE_KEY = "ops/open/comspec_terminal/executable"
    COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE_KEY = (
        "ops/open/comspec_terminal/open_args_template"
    )
    COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY = (
        "ops/open/comspec_terminal/command_args_template"
    )
    PWSH_TERMINAL_EXECUTABLE_KEY = "ops/open/pwsh_terminal/executable"
    PWSH_TERMINAL_OPEN_ARGS_TEMPLATE_KEY = "ops/open/pwsh_terminal/open_args_template"
    PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY = (
        "ops/open/pwsh_terminal/command_args_template"
    )
    POWERSHELL5_TERMINAL_EXECUTABLE_KEY = (
        "ops/open/powershell5_terminal/executable"
    )
    POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE_KEY = (
        "ops/open/powershell5_terminal/open_args_template"
    )
    POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY = (
        "ops/open/powershell5_terminal/command_args_template"
    )
    FILE_OPEN_OVERRIDES_JSON_KEY = "ops/open/file_open_overrides_json"
    TOTAL_COMMANDER_EXECUTABLE_KEY = "ops/open/total_commander/executable"
    TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE_KEY = (
        "ops/open/total_commander/source_args_template"
    )
    TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE_KEY = (
        "ops/open/total_commander/source_target_args_template"
    )
    DOUBLE_COMMANDER_EXECUTABLE_KEY = "ops/open/double_commander/executable"
    DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE_KEY = (
        "ops/open/double_commander/source_args_template"
    )
    DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE_KEY = (
        "ops/open/double_commander/source_target_args_template"
    )
    USE_EXTENDED_PATHS_ROBOCOPY_KEY = "ops/backends/robocopy/use_extended_paths"
    USE_EXTENDED_PATHS_TERACOPY_KEY = "ops/backends/teracopy/use_extended_paths"
    USE_EXTENDED_PATHS_UNSTOPPABLE_KEY = "ops/backends/unstoppable/use_extended_paths"
    USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY = (
        "ops/backends/external_copymove/use_extended_paths"
    )
    USE_EXTENDED_PATHS_CMD_DELETE_KEY = "ops/backends/cmd_delete/use_extended_paths"
    USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY = (
        "ops/backends/powershell_delete/use_extended_paths"
    )
    USE_EXTENDED_PATHS_RIMRAF_KEY = "ops/backends/rimraf/use_extended_paths"
    USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY = (
        "ops/backends/external_delete/use_extended_paths"
    )
    TERACOPY_EXECUTABLE_KEY = "ops/backends/teracopy/executable"
    UNSTOPPABLE_EXECUTABLE_KEY = "ops/backends/unstoppable/executable"
    GENERIC_COPYMOVE_EXECUTABLE_KEY = "ops/backends/generic_copymove/executable"
    GENERIC_DELETE_EXECUTABLE_KEY = "ops/backends/generic_delete/executable"
    GENERIC_DELETE_ARGS_TEMPLATE_KEY = "ops/backends/generic_delete/args_template"
    ROBOCOPY_STRUCTURED_OPTIONS_KEY = "ops/backends/robocopy/structured_options"
    TERACOPY_STRUCTURED_OPTIONS_KEY = "ops/backends/teracopy/structured_options"
    UNSTOPPABLE_STRUCTURED_OPTIONS_KEY = "ops/backends/unstoppable/structured_options"
    EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS_KEY = (
        "ops/backends/external_copymove/structured_options"
    )
    CMD_DELETE_ARGS_KEY = "ops/backends/cmd_delete/args"
    POWERSHELL_DELETE_ARGS_KEY = "ops/backends/powershell_delete/args"
    RIMRAF_EXECUTABLE_KEY = "ops/backends/rimraf/executable"
    RIMRAF_ARGS_TEMPLATE_KEY = "ops/backends/rimraf/args_template"
    OPS_COMPANION_BOOTSTRAP_DONE_KEY = "ops/internal/companion_bootstrap_done"
    SESSION_WINDOWS_KEY = "prefs/session_windows"
    SAVED_VIEWS_KEY = "prefs/saved_views"
    SETTINGS_DIALOG_LAST_SECTION_KEY = "prefs/settings_dialog/last_section"
    SETTINGS_DIALOG_LAST_SUBSECTION_KEY = "prefs/settings_dialog/last_subsection"

    DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX = "#A8B6C4"
    DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT = 24
    DEFAULT_TARGET_PANEL_TINT_COLOR_HEX = "#D2CCAA"
    DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT = 28
    DEFAULT_APP_FONT_FAMILY = ""
    DEFAULT_APP_FONT_SIZE_PT = 0
    DEFAULT_FILE_LIST_USE_APP_FONT = True
    DEFAULT_FILE_LIST_FONT_FAMILY = ""
    DEFAULT_FILE_LIST_FONT_SIZE_PT = 10
    DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE = "current_panel_tabs"
    DEFAULT_AUTOFIT_COLUMNS = False
    DEFAULT_NAVIGATION_USE_APP_FONT = True
    DEFAULT_NAVIGATION_FONT_FAMILY = ""
    DEFAULT_NAVIGATION_FONT_SIZE_PT = 10
    DEFAULT_SHOW_STORAGE_OVERVIEW_STATUS_ROW = True
    DEFAULT_BYTES_THOUSANDS_SEPARATOR = ","
    DEFAULT_BYTES_DECIMAL_SEPARATOR = "."
    DEFAULT_FILE_LIST_BYTE_FORMAT_MODE = "bytes"
    DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE = ""
    DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE = "bytes"
    DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE = ""
    DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE = (
        "{disk_root} {disk_label} {used_space}/{total_space}"
    )
    DEFAULT_PROPERTIES_BYTE_FORMAT_MODE = "bytes"
    DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE = ""
    DEFAULT_CONTEXT_IMMEDIATE_CHILD_SCAN_CAP = 33
    DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH = ""
    DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE = "{folder}"
    DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH = ""
    DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE = "{folder}"
    DEFAULT_COPY_MOVE_BACKEND = BACKEND_PYTHON
    DEFAULT_DELETE_BACKEND = BACKEND_RECYCLE_BIN
    DEFAULT_OPERATION_DISPATCH_MODE = DISPATCH_MODE_QUEUE
    DEFAULT_OPERATION_CONFLICT_POLICY = "rename"
    DEFAULT_OPERATION_SHORTCUT_BEHAVIOR = SHORTCUT_BEHAVIOR_DIRECT
    DEFAULT_OPERATION_QUEUE_VIEW_MODE = QUEUE_VIEW_DOCK
    DEFAULT_DEFAULT_EDITOR_EXECUTABLE = ""
    DEFAULT_DEFAULT_VIEWER_EXECUTABLE = ""
    DEFAULT_DEFAULT_TERMINAL_LAUNCHER = DEFAULT_TERMINAL_LAUNCHER
    DEFAULT_COMSPEC_TERMINAL_EXECUTABLE = DEFAULT_COMSPEC_TERMINAL_EXECUTABLE
    DEFAULT_COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE = (
        DEFAULT_COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE
    )
    DEFAULT_COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE = (
        DEFAULT_COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    DEFAULT_PWSH_TERMINAL_EXECUTABLE = DEFAULT_PWSH_TERMINAL_EXECUTABLE
    DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE = (
        DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE
    )
    DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE = (
        DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE = DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE
    DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE = (
        DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE
    )
    DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE = (
        DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    DEFAULT_FILE_OPEN_OVERRIDES_JSON = "{}"
    DEFAULT_TOTAL_COMMANDER_EXECUTABLE = DEFAULT_TOTAL_COMMANDER_EXECUTABLE
    DEFAULT_TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE = (
        DEFAULT_TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE
    )
    DEFAULT_TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE = (
        DEFAULT_TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE
    )
    DEFAULT_DOUBLE_COMMANDER_EXECUTABLE = DEFAULT_DOUBLE_COMMANDER_EXECUTABLE
    DEFAULT_DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE = (
        DEFAULT_DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE
    )
    DEFAULT_DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE = (
        DEFAULT_DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE
    )
    DEFAULT_USE_EXTENDED_PATHS_ROBOCOPY = False
    DEFAULT_USE_EXTENDED_PATHS_TERACOPY = False
    DEFAULT_USE_EXTENDED_PATHS_UNSTOPPABLE = False
    DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE = False
    DEFAULT_USE_EXTENDED_PATHS_CMD_DELETE = False
    DEFAULT_USE_EXTENDED_PATHS_POWERSHELL_DELETE = False
    DEFAULT_USE_EXTENDED_PATHS_RIMRAF = False
    DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_DELETE = False
    DEFAULT_TERACOPY_EXECUTABLE = DEFAULT_TERA_COPY_EXE
    DEFAULT_UNSTOPPABLE_EXECUTABLE = DEFAULT_UNSTOPPABLE_EXE
    DEFAULT_GENERIC_COPYMOVE_EXECUTABLE = DEFAULT_GENERIC_COPYMOVE_EXE
    DEFAULT_GENERIC_DELETE_EXECUTABLE = DEFAULT_GENERIC_DELETE_EXE
    DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE = DEFAULT_GENERIC_DELETE_ARGS
    DEFAULT_ROBOCOPY_STRUCTURED_OPTIONS = robocopy_options_payload(
        RobocopyBackendOptions()
    )
    DEFAULT_TERACOPY_STRUCTURED_OPTIONS = teracopy_options_payload(
        TeraCopyBackendOptions()
    )
    DEFAULT_UNSTOPPABLE_STRUCTURED_OPTIONS = unstoppable_options_payload(
        UnstoppableBackendOptions()
    )
    DEFAULT_EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS = external_copymove_options_payload(
        ExternalCopyMoveBackendOptions()
    )
    DEFAULT_CMD_DELETE_ARGS = DEFAULT_CMD_DELETE_ARGS
    DEFAULT_POWERSHELL_DELETE_ARGS = DEFAULT_POWERSHELL_DELETE_ARGS
    DEFAULT_RIMRAF_EXECUTABLE = DEFAULT_RIMRAF_EXE
    DEFAULT_RIMRAF_ARGS_TEMPLATE = DEFAULT_RIMRAF_ARGS
    DEFAULT_SETTINGS_DIALOG_LAST_SECTION = ""
    DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION = ""

    ALLOWED_NEW_CONTEXT_MODES: ClassVar[set[str]] = {"clone_active_path", "home", "cwd"}
    ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES: ClassVar[set[str]] = {
        "current_panel_tabs",
        "current_window_panels_tabs",
        "all_windows_panels_tabs",
        "none",
    }
    ALLOWED_BYTE_FORMAT_MODES: ClassVar[set[str]] = {
        "human_readable",
        "always_mb",
        "always_mib",
        "bytes",
        "custom",
    }
