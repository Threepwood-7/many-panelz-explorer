from __future__ import annotations

import json

from many_panelz_explorer._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
)
from many_panelz_explorer._settings import normalize as settings_normalize
from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer._settings.models import UiPreferences
from many_panelz_explorer.external_file_managers import (
    DEFAULT_DOUBLE_COMMANDER_EXECUTABLE,
    DEFAULT_DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE,
    DEFAULT_DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE,
    DEFAULT_TOTAL_COMMANDER_EXECUTABLE,
    DEFAULT_TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE,
    DEFAULT_TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE,
)


def _tracked_keys() -> list[str]:
    return [
        SettingsManager.NEW_CONTEXT_MODE_KEY,
        SettingsManager.SHOW_HIDDEN_DEFAULT_KEY,
        SettingsManager.SHOW_ROOT_DROPDOWN_KEY,
        SettingsManager.SHOW_STORAGE_OVERVIEW_STATUS_ROW_KEY,
        SettingsManager.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY,
        SettingsManager.AUTOFIT_COLUMNS_KEY,
        SettingsManager.SHOW_REFRESH_BUTTON_KEY,
        SettingsManager.SHOW_ROOT_BUTTONS_KEY,
        SettingsManager.SHOW_ADDRESS_BAR_KEY,
        SettingsManager.SHOW_NAVIGATION_BUTTONS_KEY,
        SettingsManager.BYTES_THOUSANDS_SEPARATOR_KEY,
        SettingsManager.BYTES_DECIMAL_SEPARATOR_KEY,
        SettingsManager.FILE_LIST_BYTE_FORMAT_MODE_KEY,
        SettingsManager.FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY,
        SettingsManager.STATUS_BAR_BYTE_FORMAT_MODE_KEY,
        SettingsManager.STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY,
        SettingsManager.STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY,
        SettingsManager.PROPERTIES_BYTE_FORMAT_MODE_KEY,
        SettingsManager.PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY,
        SettingsManager.APP_FONT_FAMILY_KEY,
        SettingsManager.APP_FONT_SIZE_PT_KEY,
        SettingsManager.FILE_LIST_USE_APP_FONT_KEY,
        SettingsManager.FILE_LIST_FONT_FAMILY_KEY,
        SettingsManager.FILE_LIST_FONT_SIZE_PT_KEY,
        SettingsManager.NAVIGATION_USE_APP_FONT_KEY,
        SettingsManager.NAVIGATION_FONT_FAMILY_KEY,
        SettingsManager.NAVIGATION_FONT_SIZE_PT_KEY,
        SettingsManager.CONTEXT_IMMEDIATE_CHILD_SCAN_CAP_KEY,
        SettingsManager.CONTEXT_TOOL_CODE_EDITOR_EXE_PATH_KEY,
        SettingsManager.CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE_KEY,
        SettingsManager.CONTEXT_TOOL_GIT_GUI_EXE_PATH_KEY,
        SettingsManager.CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE_KEY,
        SettingsManager.ACTIVE_PANEL_TINT_COLOR_KEY,
        SettingsManager.ACTIVE_PANEL_TINT_INTENSITY_KEY,
        SettingsManager.TARGET_PANEL_TINT_COLOR_KEY,
        SettingsManager.TARGET_PANEL_TINT_INTENSITY_KEY,
        SettingsManager.DEFAULT_COPY_MOVE_BACKEND_KEY,
        SettingsManager.DEFAULT_DELETE_BACKEND_KEY,
        SettingsManager.DEFAULT_OPERATION_DISPATCH_MODE_KEY,
        SettingsManager.DEFAULT_OPERATION_CONFLICT_POLICY_KEY,
        SettingsManager.OPERATION_SHORTCUT_BEHAVIOR_KEY,
        SettingsManager.OPERATION_QUEUE_VIEW_MODE_KEY,
        SettingsManager.DEFAULT_EDITOR_EXECUTABLE_KEY,
        SettingsManager.DEFAULT_VIEWER_EXECUTABLE_KEY,
        SettingsManager.DEFAULT_TERMINAL_LAUNCHER_KEY,
        SettingsManager.COMSPEC_TERMINAL_EXECUTABLE_KEY,
        SettingsManager.COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE_KEY,
        SettingsManager.COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY,
        SettingsManager.COMSPEC_TERMINAL_STARTUP_POSITION_KEY,
        SettingsManager.PWSH_TERMINAL_EXECUTABLE_KEY,
        SettingsManager.PWSH_TERMINAL_OPEN_ARGS_TEMPLATE_KEY,
        SettingsManager.PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY,
        SettingsManager.PWSH_TERMINAL_STARTUP_POSITION_KEY,
        SettingsManager.POWERSHELL5_TERMINAL_EXECUTABLE_KEY,
        SettingsManager.POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE_KEY,
        SettingsManager.POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY,
        SettingsManager.POWERSHELL5_TERMINAL_STARTUP_POSITION_KEY,
        SettingsManager.FILE_OPEN_OVERRIDES_JSON_KEY,
        SettingsManager.TOTAL_COMMANDER_EXECUTABLE_KEY,
        SettingsManager.TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE_KEY,
        SettingsManager.TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE_KEY,
        SettingsManager.DOUBLE_COMMANDER_EXECUTABLE_KEY,
        SettingsManager.DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE_KEY,
        SettingsManager.DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_ROBOCOPY_KEY,
        SettingsManager.USE_EXTENDED_PATHS_TERACOPY_KEY,
        SettingsManager.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_CMD_DELETE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_RIMRAF_KEY,
        SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY,
        SettingsManager.TERACOPY_EXECUTABLE_KEY,
        SettingsManager.UNSTOPPABLE_EXECUTABLE_KEY,
        SettingsManager.GENERIC_COPYMOVE_EXECUTABLE_KEY,
        SettingsManager.GENERIC_DELETE_EXECUTABLE_KEY,
        SettingsManager.GENERIC_DELETE_ARGS_TEMPLATE_KEY,
        SettingsManager.ROBOCOPY_STRUCTURED_OPTIONS_KEY,
        SettingsManager.TERACOPY_STRUCTURED_OPTIONS_KEY,
        SettingsManager.UNSTOPPABLE_STRUCTURED_OPTIONS_KEY,
        SettingsManager.EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS_KEY,
        SettingsManager.CMD_DELETE_ARGS_KEY,
        SettingsManager.POWERSHELL_DELETE_ARGS_KEY,
        SettingsManager.RIMRAF_EXECUTABLE_KEY,
        SettingsManager.RIMRAF_ARGS_TEMPLATE_KEY,
        SettingsManager.OPS_COMPANION_BOOTSTRAP_DONE_KEY,
        SettingsManager.SETTINGS_DIALOG_LAST_SECTION_KEY,
        SettingsManager.SETTINGS_DIALOG_LAST_SUBSECTION_KEY,
    ]


def _snapshot(settings: SettingsManager) -> dict[str, object]:
    return {key: settings.value(key, None) for key in _tracked_keys()}


def _restore(settings: SettingsManager, snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        if value is None:
            settings.remove(key)
        else:
            settings.set_value(key, value)
    settings.sync()


def test_ui_preferences_round_trip() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        expected = UiPreferences(
            new_context_mode="cwd",
            show_hidden_default=False,
            show_root_dropdown=True,
            show_storage_overview_status_row=False,
            column_width_auto_align_mode="all_windows_panels_tabs",
            autofit_columns=True,
            show_refresh_button=False,
            show_root_buttons=False,
            show_address_bar=False,
            show_navigation_buttons=False,
            byte_thousands_separator=" ",
            byte_decimal_separator=",",
            file_list_byte_format_mode="custom",
            file_list_byte_custom_template="{b} ({MiB:.2f})",
            status_bar_byte_format_mode="always_mib",
            status_bar_byte_custom_template="",
            status_bar_storage_label_template=(
                "{disk_root} {disk_label} {used_space}/{total_space} {usage_indicator}"
            ),
            properties_byte_format_mode="always_mb",
            properties_byte_custom_template="",
            app_font_family="Consolas",
            app_font_size_pt=11,
            file_list_use_app_font=False,
            file_list_font_family="Cascadia Mono",
            file_list_font_size_pt=13,
            navigation_use_app_font=False,
            navigation_font_family="Segoe UI",
            navigation_font_size_pt=12,
            context_immediate_child_scan_cap=55,
            context_tool_code_editor_exe_path=r"C:\tools\code.exe",
            context_tool_code_editor_args_template="--folder {folder}",
            context_tool_git_gui_exe_path=r"C:\tools\gitgui.exe",
            context_tool_git_gui_args_template="--path {folder}",
            active_panel_tint_color_hex="#ABCDEF",
            active_panel_tint_intensity_percent=80,
            target_panel_tint_color_hex="#123456",
            target_panel_tint_intensity_percent=33,
            default_copy_move_backend="robocopy",
            default_delete_backend="powershell_delete",
            default_operation_dispatch_mode="run_now_wait",
            default_operation_conflict_policy="overwrite",
            operation_shortcut_behavior="always_dialog",
            operation_queue_view_mode="both",
            default_editor_executable=r"C:\tools\editor.exe",
            default_viewer_executable=r"C:\tools\viewer.exe",
            default_terminal_launcher="powershell5",
            comspec_terminal_executable="%ComSpec%",
            comspec_terminal_open_args_template="/K cd /d {folder}",
            comspec_terminal_command_args_template="/K {shell_command}",
            comspec_terminal_startup_position="maximized",
            pwsh_terminal_executable=r"C:\Program Files\PowerShell\7\pwsh.exe",
            pwsh_terminal_open_args_template=(
                "-NoExit -Command Set-Location -LiteralPath {folder}"
            ),
            pwsh_terminal_command_args_template="-NoExit -Command {shell_command}",
            pwsh_terminal_startup_position="right_of_screen",
            powershell5_terminal_executable=(
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            ),
            powershell5_terminal_open_args_template=(
                "-NoExit -Command Set-Location -LiteralPath {folder}"
            ),
            powershell5_terminal_command_args_template=(
                "-NoExit -Command {shell_command}"
            ),
            powershell5_terminal_startup_position="left_of_screen",
            file_open_overrides_json=(
                '{".txt": {"editor": "txtedit.exe", "viewer": "txtview.exe"}}'
            ),
            total_commander_executable=r"C:\tools\totalcmd64.exe",
            total_commander_source_args_template="/N /L={source}",
            total_commander_source_target_args_template=("/N /L={source} /R={target}"),
            double_commander_executable=r"C:\tools\doublecmd.exe",
            double_commander_source_args_template="--client -L {source}",
            double_commander_source_target_args_template=(
                "--client -L {source} -R {target}"
            ),
            use_extended_paths_robocopy=True,
            use_extended_paths_teracopy=True,
            use_extended_paths_unstoppable=True,
            use_extended_paths_external_copymove=True,
            use_extended_paths_cmd_delete=True,
            use_extended_paths_powershell_delete=True,
            use_extended_paths_rimraf=True,
            use_extended_paths_external_delete=True,
            teracopy_executable="TeraCopy.exe",
            unstoppable_executable="UnstoppableCopier.exe",
            generic_copymove_executable="my-copy.exe",
            generic_delete_executable="my-del.exe",
            generic_delete_args_template="{operation} {sources}",
            robocopy_structured_options=RobocopyBackendOptions(
                include_subdirectories=True,
                mirror_target=False,
                move_files_for_move=True,
                restartable_mode=True,
                backup_mode=False,
                list_only=False,
                suppress_logs=False,
                retry_count=4,
                wait_seconds=2,
                use_multithreading=True,
                multithread_count=16,
                extra_args="/XO",
            ),
            teracopy_structured_options=TeraCopyBackendOptions(
                close_on_finish=True,
                keep_open=False,
                verify_after_copy=True,
                no_sound=True,
                conflict_mode="/SkipAll",
                extra_args="/NoHistory",
            ),
            unstoppable_structured_options=UnstoppableBackendOptions(
                use_defaults=True,
                keep_attributes=True,
                keep_owner=False,
                keep_time=True,
                overwrite_existing=True,
                include_subfolders=True,
                recover_and_resume=True,
                copy_newer_only=False,
                skip_damaged=True,
                undamaged_first=False,
                overwrite_readonly=False,
                copy_empty_folders=True,
                show_eta=True,
                power_down_when_done=False,
                extra_args="+x",
            ),
            external_copymove_structured_options=ExternalCopyMoveBackendOptions(
                include_operation_token=True,
                include_sources=True,
                include_target=False,
                extra_args="--mode fast",
            ),
            cmd_delete_args="/Q",
            powershell_delete_args="-Force",
            rimraf_executable="rimraf",
            rimraf_args_template="--glob=false",
        )
        settings.set_ui_preferences(expected)
        settings.sync()
        assert settings.ui_preferences() == expected
    finally:
        _restore(settings, before)


def test_windows_executable_paths_normalize_to_backslashes() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_value(
            SettingsManager.UNSTOPPABLE_EXECUTABLE_KEY,
            "C:/bin/roadkil/UnstopCpy_5_2_Win2K_UP.exe",
        )
        settings.set_value(
            SettingsManager.DEFAULT_EDITOR_EXECUTABLE_KEY,
            "C:/tools/editor.exe",
        )
        settings.set_value(
            SettingsManager.PWSH_TERMINAL_EXECUTABLE_KEY,
            "C:/Program Files/PowerShell/7/pwsh.exe",
        )
        settings.set_value(
            SettingsManager.TOTAL_COMMANDER_EXECUTABLE_KEY,
            "C:/tools/totalcmd64.exe",
        )
        settings.set_value(
            SettingsManager.DOUBLE_COMMANDER_EXECUTABLE_KEY,
            "C:/tools/doublecmd.exe",
        )
        settings.set_value(
            SettingsManager.FILE_OPEN_OVERRIDES_JSON_KEY,
            json.dumps(
                {
                    ".log": {
                        "editor": "C:/tools/logedit.exe",
                        "viewer": "C:/tools/logview.exe",
                    }
                }
            ),
        )
        settings.sync()

        assert (
            settings.unstoppable_executable
            == r"C:\bin\roadkil\UnstopCpy_5_2_Win2K_UP.exe"
        )
        assert settings.default_editor_executable == r"C:\tools\editor.exe"
        assert (
            settings.pwsh_terminal_executable
            == r"C:\Program Files\PowerShell\7\pwsh.exe"
        )
        assert settings.total_commander_executable == r"C:\tools\totalcmd64.exe"
        assert settings.double_commander_executable == r"C:\tools\doublecmd.exe"
        overrides = json.loads(settings.file_open_overrides_json)
        assert overrides[".log"]["editor"] == r"C:\tools\logedit.exe"
        assert overrides[".log"]["viewer"] == r"C:\tools\logview.exe"
    finally:
        _restore(settings, before)


def test_normalize_file_open_override_mapping_rejects_non_mapping_input() -> None:
    assert settings_normalize.normalize_file_open_override_mapping([".txt"]) is None


def test_normalize_file_open_override_mapping_normalizes_extensions_and_paths() -> None:
    normalized = settings_normalize.normalize_file_open_override_mapping(
        {
            "TXT": {
                "editor": "C:/tools/editor.exe",
                "viewer": "C:/tools/viewer.exe",
            },
            ".log": "not-a-mapping",
        }
    )

    assert normalized == {
        ".txt": {
            "editor": r"C:\tools\editor.exe",
            "viewer": r"C:\tools\viewer.exe",
        },
        ".log": {"editor": "", "viewer": ""},
    }


def test_normalize_file_open_override_mapping_coerces_non_string_keys() -> None:
    normalized = settings_normalize.normalize_file_open_override_mapping(
        {
            7: {
                "editor": "C:/tools/editor.exe",
                "viewer": "C:/tools/viewer.exe",
            }
        }
    )

    assert normalized == {
        ".7": {
            "editor": r"C:\tools\editor.exe",
            "viewer": r"C:\tools\viewer.exe",
        }
    }


def test_ui_preferences_invalid_values_fallback_to_defaults() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_value(SettingsManager.NEW_CONTEXT_MODE_KEY, "invalid-mode")
        settings.remove(SettingsManager.SHOW_ROOT_DROPDOWN_KEY)
        settings.remove(SettingsManager.SHOW_STORAGE_OVERVIEW_STATUS_ROW_KEY)
        settings.set_value(
            SettingsManager.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY, "invalid-align-mode"
        )
        settings.remove(SettingsManager.AUTOFIT_COLUMNS_KEY)
        settings.remove(SettingsManager.SHOW_REFRESH_BUTTON_KEY)
        settings.remove(SettingsManager.SHOW_ROOT_BUTTONS_KEY)
        settings.remove(SettingsManager.SHOW_ADDRESS_BAR_KEY)
        settings.remove(SettingsManager.SHOW_NAVIGATION_BUTTONS_KEY)
        settings.set_value(SettingsManager.BYTES_THOUSANDS_SEPARATOR_KEY, ",")
        settings.set_value(SettingsManager.BYTES_DECIMAL_SEPARATOR_KEY, ",")
        settings.set_value(SettingsManager.FILE_LIST_BYTE_FORMAT_MODE_KEY, "invalid")
        settings.remove(SettingsManager.FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY)
        settings.set_value(SettingsManager.STATUS_BAR_BYTE_FORMAT_MODE_KEY, "INVALID")
        settings.remove(SettingsManager.STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY)
        settings.set_value(
            SettingsManager.STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY, "plain text"
        )
        settings.set_value(SettingsManager.PROPERTIES_BYTE_FORMAT_MODE_KEY, "bad")
        settings.remove(SettingsManager.PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY)
        settings.remove(SettingsManager.APP_FONT_FAMILY_KEY)
        settings.remove(SettingsManager.APP_FONT_SIZE_PT_KEY)
        settings.remove(SettingsManager.FILE_LIST_USE_APP_FONT_KEY)
        settings.remove(SettingsManager.FILE_LIST_FONT_FAMILY_KEY)
        settings.remove(SettingsManager.FILE_LIST_FONT_SIZE_PT_KEY)
        settings.remove(SettingsManager.NAVIGATION_USE_APP_FONT_KEY)
        settings.remove(SettingsManager.NAVIGATION_FONT_FAMILY_KEY)
        settings.remove(SettingsManager.NAVIGATION_FONT_SIZE_PT_KEY)
        settings.set_value(
            SettingsManager.CONTEXT_IMMEDIATE_CHILD_SCAN_CAP_KEY, "invalid"
        )
        settings.remove(SettingsManager.CONTEXT_TOOL_CODE_EDITOR_EXE_PATH_KEY)
        settings.remove(SettingsManager.CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.CONTEXT_TOOL_GIT_GUI_EXE_PATH_KEY)
        settings.remove(SettingsManager.CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE_KEY)
        settings.set_value(SettingsManager.ACTIVE_PANEL_TINT_COLOR_KEY, "blue")
        settings.set_value(SettingsManager.TARGET_PANEL_TINT_COLOR_KEY, "#12")
        settings.set_value(SettingsManager.ACTIVE_PANEL_TINT_INTENSITY_KEY, "oops")
        settings.set_value(SettingsManager.TARGET_PANEL_TINT_INTENSITY_KEY, "nope")
        settings.set_value(SettingsManager.DEFAULT_COPY_MOVE_BACKEND_KEY, "invalid")
        settings.set_value(SettingsManager.DEFAULT_DELETE_BACKEND_KEY, "invalid")
        settings.set_value(
            SettingsManager.DEFAULT_OPERATION_DISPATCH_MODE_KEY, "invalid"
        )
        settings.set_value(
            SettingsManager.DEFAULT_OPERATION_CONFLICT_POLICY_KEY, "invalid"
        )
        settings.set_value(SettingsManager.OPERATION_SHORTCUT_BEHAVIOR_KEY, "invalid")
        settings.set_value(SettingsManager.OPERATION_QUEUE_VIEW_MODE_KEY, "invalid")
        settings.remove(SettingsManager.DEFAULT_EDITOR_EXECUTABLE_KEY)
        settings.remove(SettingsManager.DEFAULT_VIEWER_EXECUTABLE_KEY)
        settings.set_value(SettingsManager.DEFAULT_TERMINAL_LAUNCHER_KEY, "invalid")
        settings.remove(SettingsManager.COMSPEC_TERMINAL_EXECUTABLE_KEY)
        settings.remove(SettingsManager.COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY)
        settings.set_value(
            SettingsManager.COMSPEC_TERMINAL_STARTUP_POSITION_KEY,
            "invalid",
        )
        settings.remove(SettingsManager.PWSH_TERMINAL_EXECUTABLE_KEY)
        settings.remove(SettingsManager.PWSH_TERMINAL_OPEN_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY)
        settings.set_value(
            SettingsManager.PWSH_TERMINAL_STARTUP_POSITION_KEY,
            "invalid",
        )
        settings.remove(SettingsManager.POWERSHELL5_TERMINAL_EXECUTABLE_KEY)
        settings.remove(SettingsManager.POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE_KEY)
        settings.set_value(
            SettingsManager.POWERSHELL5_TERMINAL_STARTUP_POSITION_KEY,
            "invalid",
        )
        settings.set_value(SettingsManager.FILE_OPEN_OVERRIDES_JSON_KEY, "not-json")
        settings.remove(SettingsManager.TOTAL_COMMANDER_EXECUTABLE_KEY)
        settings.remove(SettingsManager.TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.DOUBLE_COMMANDER_EXECUTABLE_KEY)
        settings.remove(SettingsManager.DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE_KEY)
        settings.remove(
            SettingsManager.DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE_KEY
        )
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_ROBOCOPY_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_TERACOPY_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_CMD_DELETE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_RIMRAF_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY, "")
        settings.remove(SettingsManager.TERACOPY_EXECUTABLE_KEY)
        settings.remove(SettingsManager.UNSTOPPABLE_EXECUTABLE_KEY)
        settings.remove(SettingsManager.GENERIC_COPYMOVE_EXECUTABLE_KEY)
        settings.remove(SettingsManager.GENERIC_DELETE_EXECUTABLE_KEY)
        settings.remove(SettingsManager.GENERIC_DELETE_ARGS_TEMPLATE_KEY)
        settings.set_value(SettingsManager.ROBOCOPY_STRUCTURED_OPTIONS_KEY, "bad")
        settings.set_value(SettingsManager.TERACOPY_STRUCTURED_OPTIONS_KEY, "bad")
        settings.set_value(SettingsManager.UNSTOPPABLE_STRUCTURED_OPTIONS_KEY, "bad")
        settings.set_value(
            SettingsManager.EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS_KEY, "bad"
        )
        settings.remove(SettingsManager.CMD_DELETE_ARGS_KEY)
        settings.remove(SettingsManager.POWERSHELL_DELETE_ARGS_KEY)
        settings.remove(SettingsManager.RIMRAF_EXECUTABLE_KEY)
        settings.remove(SettingsManager.RIMRAF_ARGS_TEMPLATE_KEY)

        loaded = settings.ui_preferences()
        assert loaded.new_context_mode == "clone_active_path"
        assert loaded.show_root_dropdown is False
        assert (
            loaded.show_storage_overview_status_row
            == SettingsManager.DEFAULT_SHOW_STORAGE_OVERVIEW_STATUS_ROW
        )
        assert (
            loaded.column_width_auto_align_mode
            == SettingsManager.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        )
        assert loaded.autofit_columns == SettingsManager.DEFAULT_AUTOFIT_COLUMNS
        assert loaded.show_refresh_button is True
        assert loaded.show_root_buttons is True
        assert loaded.show_address_bar is True
        assert loaded.show_navigation_buttons is True
        assert (
            loaded.byte_thousands_separator
            == SettingsManager.DEFAULT_BYTES_THOUSANDS_SEPARATOR
        )
        assert (
            loaded.byte_decimal_separator
            == SettingsManager.DEFAULT_BYTES_DECIMAL_SEPARATOR
        )
        assert (
            loaded.file_list_byte_format_mode
            == SettingsManager.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE
        )
        assert (
            loaded.file_list_byte_custom_template
            == SettingsManager.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE
        )
        assert (
            loaded.status_bar_byte_format_mode
            == SettingsManager.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE
        )
        assert (
            loaded.status_bar_byte_custom_template
            == SettingsManager.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE
        )
        assert (
            loaded.status_bar_storage_label_template
            == SettingsManager.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE
        )
        assert (
            loaded.properties_byte_format_mode
            == SettingsManager.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE
        )
        assert (
            loaded.properties_byte_custom_template
            == SettingsManager.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE
        )
        assert loaded.app_font_family == SettingsManager.DEFAULT_APP_FONT_FAMILY
        assert loaded.app_font_size_pt == SettingsManager.DEFAULT_APP_FONT_SIZE_PT
        assert (
            loaded.file_list_use_app_font
            == SettingsManager.DEFAULT_FILE_LIST_USE_APP_FONT
        )
        assert (
            loaded.file_list_font_family
            == SettingsManager.DEFAULT_FILE_LIST_FONT_FAMILY
        )
        assert (
            loaded.file_list_font_size_pt
            == SettingsManager.DEFAULT_FILE_LIST_FONT_SIZE_PT
        )
        assert (
            loaded.navigation_use_app_font
            == SettingsManager.DEFAULT_NAVIGATION_USE_APP_FONT
        )
        assert (
            loaded.navigation_font_family
            == SettingsManager.DEFAULT_NAVIGATION_FONT_FAMILY
        )
        assert (
            loaded.navigation_font_size_pt
            == SettingsManager.DEFAULT_NAVIGATION_FONT_SIZE_PT
        )
        assert (
            loaded.context_immediate_child_scan_cap
            == SettingsManager.DEFAULT_CONTEXT_IMMEDIATE_CHILD_SCAN_CAP
        )
        assert (
            loaded.context_tool_code_editor_exe_path
            == SettingsManager.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH
        )
        assert (
            loaded.context_tool_code_editor_args_template
            == SettingsManager.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE
        )
        assert (
            loaded.context_tool_git_gui_exe_path
            == SettingsManager.DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH
        )
        assert (
            loaded.context_tool_git_gui_args_template
            == SettingsManager.DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE
        )
        assert (
            loaded.active_panel_tint_color_hex
            == SettingsManager.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX
        )
        assert (
            loaded.target_panel_tint_color_hex
            == SettingsManager.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX
        )
        assert (
            loaded.active_panel_tint_intensity_percent
            == SettingsManager.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT
        )
        assert (
            loaded.target_panel_tint_intensity_percent
            == SettingsManager.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT
        )
        assert (
            loaded.default_copy_move_backend
            == SettingsManager.DEFAULT_COPY_MOVE_BACKEND
        )
        assert loaded.default_delete_backend == SettingsManager.DEFAULT_DELETE_BACKEND
        assert (
            loaded.default_operation_dispatch_mode
            == SettingsManager.DEFAULT_OPERATION_DISPATCH_MODE
        )
        assert (
            loaded.default_operation_conflict_policy
            == SettingsManager.DEFAULT_OPERATION_CONFLICT_POLICY
        )
        assert (
            loaded.operation_shortcut_behavior
            == SettingsManager.DEFAULT_OPERATION_SHORTCUT_BEHAVIOR
        )
        assert (
            loaded.operation_queue_view_mode
            == SettingsManager.DEFAULT_OPERATION_QUEUE_VIEW_MODE
        )
        assert (
            loaded.default_editor_executable
            == SettingsManager.DEFAULT_DEFAULT_EDITOR_EXECUTABLE
        )
        assert (
            loaded.default_viewer_executable
            == SettingsManager.DEFAULT_DEFAULT_VIEWER_EXECUTABLE
        )
        assert (
            loaded.default_terminal_launcher
            == SettingsManager.DEFAULT_DEFAULT_TERMINAL_LAUNCHER
        )
        assert (
            loaded.comspec_terminal_executable
            == SettingsManager.DEFAULT_COMSPEC_TERMINAL_EXECUTABLE
        )
        assert (
            loaded.comspec_terminal_open_args_template
            == SettingsManager.DEFAULT_COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE
        )
        assert (
            loaded.comspec_terminal_command_args_template
            == SettingsManager.DEFAULT_COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE
        )
        assert (
            loaded.comspec_terminal_startup_position
            == SettingsManager.DEFAULT_COMSPEC_TERMINAL_STARTUP_POSITION
        )
        assert (
            loaded.pwsh_terminal_executable
            == SettingsManager.DEFAULT_PWSH_TERMINAL_EXECUTABLE
        )
        assert (
            loaded.pwsh_terminal_open_args_template
            == SettingsManager.DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE
        )
        assert (
            loaded.pwsh_terminal_command_args_template
            == SettingsManager.DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE
        )
        assert (
            loaded.pwsh_terminal_startup_position
            == SettingsManager.DEFAULT_PWSH_TERMINAL_STARTUP_POSITION
        )
        assert (
            loaded.powershell5_terminal_executable
            == SettingsManager.DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE
        )
        assert (
            loaded.powershell5_terminal_open_args_template
            == SettingsManager.DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE
        )
        assert (
            loaded.powershell5_terminal_command_args_template
            == SettingsManager.DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE
        )
        assert (
            loaded.powershell5_terminal_startup_position
            == SettingsManager.DEFAULT_POWERSHELL5_TERMINAL_STARTUP_POSITION
        )
        assert (
            loaded.file_open_overrides_json
            == SettingsManager.DEFAULT_FILE_OPEN_OVERRIDES_JSON
        )
        assert loaded.total_commander_executable == DEFAULT_TOTAL_COMMANDER_EXECUTABLE
        assert (
            loaded.total_commander_source_args_template
            == DEFAULT_TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE
        )
        assert (
            loaded.total_commander_source_target_args_template
            == DEFAULT_TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE
        )
        assert loaded.double_commander_executable == DEFAULT_DOUBLE_COMMANDER_EXECUTABLE
        assert (
            loaded.double_commander_source_args_template
            == DEFAULT_DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE
        )
        assert (
            loaded.double_commander_source_target_args_template
            == DEFAULT_DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE
        )
        assert loaded.use_extended_paths_robocopy is False
        assert loaded.use_extended_paths_teracopy is False
        assert loaded.use_extended_paths_unstoppable is False
        assert loaded.use_extended_paths_external_copymove is False
        assert loaded.use_extended_paths_cmd_delete is False
        assert loaded.use_extended_paths_powershell_delete is False
        assert loaded.use_extended_paths_rimraf is False
        assert loaded.use_extended_paths_external_delete is False
        assert loaded.robocopy_structured_options == RobocopyBackendOptions()
        assert loaded.teracopy_structured_options == TeraCopyBackendOptions()
        assert loaded.unstoppable_structured_options == UnstoppableBackendOptions()
        assert (
            loaded.external_copymove_structured_options
            == ExternalCopyMoveBackendOptions()
        )
    finally:
        _restore(settings, before)


def test_ui_preferences_font_size_clamps_to_range() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_value(SettingsManager.APP_FONT_SIZE_PT_KEY, -12)
        settings.set_value(SettingsManager.FILE_LIST_FONT_SIZE_PT_KEY, 2)
        settings.set_value(SettingsManager.NAVIGATION_FONT_SIZE_PT_KEY, 120)
        loaded = settings.ui_preferences()
        assert loaded.app_font_size_pt == 0
        assert loaded.file_list_font_size_pt == 6
        assert loaded.navigation_font_size_pt == 32
    finally:
        _restore(settings, before)


def test_ui_preferences_intensity_clamps_to_range() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_value(SettingsManager.ACTIVE_PANEL_TINT_INTENSITY_KEY, -5)
        settings.set_value(SettingsManager.TARGET_PANEL_TINT_INTENSITY_KEY, 1000)
        loaded = settings.ui_preferences()
        assert loaded.active_panel_tint_intensity_percent == 0
        assert loaded.target_panel_tint_intensity_percent == 100
    finally:
        _restore(settings, before)


def test_ui_preferences_column_auto_align_mode_defaults_when_unset() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.remove(SettingsManager.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY)
        loaded = settings.ui_preferences()
        assert (
            loaded.column_width_auto_align_mode
            == SettingsManager.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        )
    finally:
        _restore(settings, before)


def test_ui_preferences_autofit_columns_defaults_when_unset() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.remove(SettingsManager.AUTOFIT_COLUMNS_KEY)
        loaded = settings.ui_preferences()
        assert loaded.autofit_columns == SettingsManager.DEFAULT_AUTOFIT_COLUMNS
    finally:
        _restore(settings, before)


def test_ui_preferences_column_auto_align_mode_invalid_value_uses_default() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_value(
            SettingsManager.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY,
            "all_panels_tabs",
        )
        loaded = settings.ui_preferences()
        assert (
            loaded.column_width_auto_align_mode
            == SettingsManager.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        )
    finally:
        _restore(settings, before)


def test_ops_companion_bootstrap_flag_round_trip() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.remove(SettingsManager.OPS_COMPANION_BOOTSTRAP_DONE_KEY)
        assert settings.ops_companion_bootstrap_done is False
        settings.ops_companion_bootstrap_done = True
        assert settings.ops_companion_bootstrap_done is True
    finally:
        _restore(settings, before)


def test_settings_dialog_navigation_location_round_trip() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.remove(SettingsManager.SETTINGS_DIALOG_LAST_SECTION_KEY)
        settings.remove(SettingsManager.SETTINGS_DIALOG_LAST_SUBSECTION_KEY)
        assert settings.settings_dialog_last_section == ""
        assert settings.settings_dialog_last_subsection == ""

        settings.settings_dialog_last_section = "operations"
        settings.settings_dialog_last_subsection = "operations/backend_commands"
        assert settings.settings_dialog_last_section == "operations"
        assert settings.settings_dialog_last_subsection == "operations/backend_commands"

        settings.set_value(SettingsManager.SETTINGS_DIALOG_LAST_SECTION_KEY, None)
        settings.set_value(SettingsManager.SETTINGS_DIALOG_LAST_SUBSECTION_KEY, None)
        assert settings.settings_dialog_last_section == ""
        assert settings.settings_dialog_last_subsection == ""
    finally:
        _restore(settings, before)


def test_settings_clear_all_removes_known_and_unknown_keys() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    unknown_key = "custom/test_unknown_key"
    unknown_before = settings.value(unknown_key, None)
    window_tabs_key = settings.window_key("unit-reset", "tabs")
    window_tree_key = settings.window_key("unit-reset", "panel_tree")
    window_geometry_key = settings.window_key("unit-reset", "geometry")
    window_tabs_before = settings.value(window_tabs_key, None)
    window_tree_before = settings.value(window_tree_key, None)
    window_geometry_before = settings.value(window_geometry_key, None)
    try:
        settings.show_hidden_default = False
        settings.default_copy_move_backend = "robocopy"
        settings.settings_dialog_last_section = "operations"
        settings.settings_dialog_last_subsection = "operations/backend_args"
        settings.set_session_window_ids(["unit-reset"])
        settings.set_saved_view("Unit View", {"tabs": {}, "panel_tree": {}})
        settings.set_json(window_tabs_key, {"active_panel_id": 1, "panels": {}})
        settings.set_json(window_tree_key, {"type": "leaf", "panel_id": 1})
        settings.set_value(window_geometry_key, "raw-geometry")
        settings.set_value(unknown_key, "survive?")
        settings.sync()

        settings.clear_all()
        settings.sync()

        assert settings.value(SettingsManager.SHOW_HIDDEN_DEFAULT_KEY, None) is None
        assert (
            settings.value(SettingsManager.DEFAULT_COPY_MOVE_BACKEND_KEY, None) is None
        )
        assert settings.value(SettingsManager.SESSION_WINDOWS_KEY, None) is None
        assert settings.value(SettingsManager.SAVED_VIEWS_KEY, None) is None
        assert settings.value(window_tabs_key, None) is None
        assert settings.value(window_tree_key, None) is None
        assert settings.value(window_geometry_key, None) is None
        assert settings.value(unknown_key, None) is None

        loaded = settings.ui_preferences()
        assert loaded == UiPreferences()
    finally:
        _restore(settings, before)
        if unknown_before is None:
            settings.remove(unknown_key)
        else:
            settings.set_value(unknown_key, unknown_before)
        if window_tabs_before is None:
            settings.remove(window_tabs_key)
        else:
            settings.set_value(window_tabs_key, window_tabs_before)
        if window_tree_before is None:
            settings.remove(window_tree_key)
        else:
            settings.set_value(window_tree_key, window_tree_before)
        if window_geometry_before is None:
            settings.remove(window_geometry_key)
        else:
            settings.set_value(window_geometry_key, window_geometry_before)
        settings.sync()


def test_saved_view_round_trip_normalizes_payload_shape() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_saved_view(
            "Legacy View",
            {
                "window_id": 9,
                "panel_tree": {"root": {"type": "leaf", "panel_id": "3"}},
                "tabs": {"3": {"panel_id": "3", "tabs": [{"path": 123}]}},
                "active_panel_id": "3",
                "on_top": "yes",
                "maximized": "1",
            },
        )

        assert settings.get_saved_view("Legacy View") == {
            "window_id": "9",
            "panel_tree": {"root": {"type": "leaf", "panel_id": 3}},
            "tabs": {3: {"panel_id": 3, "tabs": [{"path": "123"}]}},
            "active_panel_id": 3,
            "on_top": True,
            "maximized": True,
        }
    finally:
        _restore(settings, before)
