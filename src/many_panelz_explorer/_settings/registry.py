from __future__ import annotations

from typing import ClassVar

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


class SettingsRegistry:
    NEW_CONTEXT_MODE_KEY = "config/new_context_mode"
    SHOW_HIDDEN_DEFAULT_KEY = "ui/show_hidden_default"
    SHOW_ROOT_DROPDOWN_KEY = "ui/show_root_dropdown"
    COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY = "ui/file_list/column_width_auto_align_mode"
    SHOW_REFRESH_BUTTON_KEY = "ui/show_refresh_button"
    SHOW_ROOT_BUTTONS_KEY = "ui/show_root_buttons"
    SHOW_ADDRESS_BAR_KEY = "ui/show_address_bar"
    SHOW_NAVIGATION_BUTTONS_KEY = "ui/show_navigation_buttons"
    APP_FONT_FAMILY_KEY = "ui/font/app/family"
    APP_FONT_SIZE_PT_KEY = "ui/font/app/size_pt"
    FILE_LIST_USE_APP_FONT_KEY = "ui/font/file_list/use_app_font"
    FILE_LIST_FONT_FAMILY_KEY = "ui/font/file_list/family"
    FILE_LIST_FONT_SIZE_PT_KEY = "ui/font/file_list/size_pt"
    NAVIGATION_USE_APP_FONT_KEY = "ui/font/navigation/use_app_font"
    NAVIGATION_FONT_FAMILY_KEY = "ui/font/navigation/family"
    NAVIGATION_FONT_SIZE_PT_KEY = "ui/font/navigation/size_pt"
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
    FILE_OPEN_OVERRIDES_JSON_KEY = "ops/open/file_open_overrides_json"
    USE_EXTENDED_PATHS_ROBOCOPY_KEY = "ops/backends/robocopy/use_extended_paths"
    USE_EXTENDED_PATHS_TERACOPY_KEY = "ops/backends/teracopy/use_extended_paths"
    USE_EXTENDED_PATHS_UNSTOPPABLE_KEY = "ops/backends/unstoppable/use_extended_paths"
    USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY = "ops/backends/external_copymove/use_extended_paths"
    USE_EXTENDED_PATHS_CMD_DELETE_KEY = "ops/backends/cmd_delete/use_extended_paths"
    USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY = "ops/backends/powershell_delete/use_extended_paths"
    USE_EXTENDED_PATHS_RIMRAF_KEY = "ops/backends/rimraf/use_extended_paths"
    USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY = "ops/backends/external_delete/use_extended_paths"
    SCRIPT_EDITOR_EXECUTABLE_KEY = "ops/script_editor/executable"
    TERACOPY_EXECUTABLE_KEY = "ops/backends/teracopy/executable"
    TERACOPY_ARGS_TEMPLATE_KEY = "ops/backends/teracopy/args_template"
    UNSTOPPABLE_EXECUTABLE_KEY = "ops/backends/unstoppable/executable"
    UNSTOPPABLE_ARGS_TEMPLATE_KEY = "ops/backends/unstoppable/args_template"
    GENERIC_COPYMOVE_EXECUTABLE_KEY = "ops/backends/generic_copymove/executable"
    GENERIC_COPYMOVE_ARGS_TEMPLATE_KEY = "ops/backends/generic_copymove/args_template"
    GENERIC_DELETE_EXECUTABLE_KEY = "ops/backends/generic_delete/executable"
    GENERIC_DELETE_ARGS_TEMPLATE_KEY = "ops/backends/generic_delete/args_template"
    ROBOCOPY_COPY_ARGS_KEY = "ops/backends/robocopy/copy_args"
    ROBOCOPY_MOVE_ARGS_KEY = "ops/backends/robocopy/move_args"
    CMD_DELETE_ARGS_KEY = "ops/backends/cmd_delete/args"
    POWERSHELL_DELETE_ARGS_KEY = "ops/backends/powershell_delete/args"
    RIMRAF_EXECUTABLE_KEY = "ops/backends/rimraf/executable"
    RIMRAF_ARGS_TEMPLATE_KEY = "ops/backends/rimraf/args_template"
    OPS_COMPANION_BOOTSTRAP_DONE_KEY = "ops/internal/companion_bootstrap_done"
    SESSION_WINDOWS_KEY = "prefs/session_windows"
    SAVED_VIEWS_KEY = "prefs/saved_views"

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
    DEFAULT_NAVIGATION_USE_APP_FONT = True
    DEFAULT_NAVIGATION_FONT_FAMILY = ""
    DEFAULT_NAVIGATION_FONT_SIZE_PT = 10
    DEFAULT_COPY_MOVE_BACKEND = BACKEND_PYTHON
    DEFAULT_DELETE_BACKEND = BACKEND_RECYCLE_BIN
    DEFAULT_OPERATION_DISPATCH_MODE = DISPATCH_MODE_QUEUE
    DEFAULT_OPERATION_CONFLICT_POLICY = "rename"
    DEFAULT_OPERATION_SHORTCUT_BEHAVIOR = SHORTCUT_BEHAVIOR_DIRECT
    DEFAULT_OPERATION_QUEUE_VIEW_MODE = QUEUE_VIEW_DOCK
    DEFAULT_DEFAULT_EDITOR_EXECUTABLE = ""
    DEFAULT_DEFAULT_VIEWER_EXECUTABLE = ""
    DEFAULT_FILE_OPEN_OVERRIDES_JSON = "{}"
    DEFAULT_USE_EXTENDED_PATHS_ROBOCOPY = False
    DEFAULT_USE_EXTENDED_PATHS_TERACOPY = False
    DEFAULT_USE_EXTENDED_PATHS_UNSTOPPABLE = False
    DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE = False
    DEFAULT_USE_EXTENDED_PATHS_CMD_DELETE = False
    DEFAULT_USE_EXTENDED_PATHS_POWERSHELL_DELETE = False
    DEFAULT_USE_EXTENDED_PATHS_RIMRAF = False
    DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_DELETE = False
    DEFAULT_SCRIPT_EDITOR_EXECUTABLE = ""
    DEFAULT_TERACOPY_EXECUTABLE = DEFAULT_TERA_COPY_EXE
    DEFAULT_TERACOPY_ARGS_TEMPLATE = DEFAULT_TERA_COPY_ARGS
    DEFAULT_UNSTOPPABLE_EXECUTABLE = DEFAULT_UNSTOPPABLE_EXE
    DEFAULT_UNSTOPPABLE_ARGS_TEMPLATE = DEFAULT_UNSTOPPABLE_ARGS
    DEFAULT_GENERIC_COPYMOVE_EXECUTABLE = DEFAULT_GENERIC_COPYMOVE_EXE
    DEFAULT_GENERIC_COPYMOVE_ARGS_TEMPLATE = DEFAULT_GENERIC_COPYMOVE_ARGS
    DEFAULT_GENERIC_DELETE_EXECUTABLE = DEFAULT_GENERIC_DELETE_EXE
    DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE = DEFAULT_GENERIC_DELETE_ARGS
    DEFAULT_ROBOCOPY_COPY_ARGS = DEFAULT_ROBOCOPY_COPY_ARGS
    DEFAULT_ROBOCOPY_MOVE_ARGS = DEFAULT_ROBOCOPY_MOVE_ARGS
    DEFAULT_CMD_DELETE_ARGS = DEFAULT_CMD_DELETE_ARGS
    DEFAULT_POWERSHELL_DELETE_ARGS = DEFAULT_POWERSHELL_DELETE_ARGS
    DEFAULT_RIMRAF_EXECUTABLE = DEFAULT_RIMRAF_EXE
    DEFAULT_RIMRAF_ARGS_TEMPLATE = DEFAULT_RIMRAF_ARGS

    ALLOWED_NEW_CONTEXT_MODES: ClassVar[set[str]] = {"clone_active_path", "home", "cwd"}
    ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES: ClassVar[set[str]] = {
        "all_panels_tabs",
        "current_panel_tabs",
        "none",
    }
