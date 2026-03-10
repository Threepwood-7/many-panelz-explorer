from __future__ import annotations

from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer._settings.models import UiPreferences


def _tracked_keys() -> list[str]:
    return [
        SettingsManager.NEW_CONTEXT_MODE_KEY,
        SettingsManager.SHOW_HIDDEN_DEFAULT_KEY,
        SettingsManager.SHOW_ROOT_DROPDOWN_KEY,
        SettingsManager.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY,
        SettingsManager.SHOW_REFRESH_BUTTON_KEY,
        SettingsManager.SHOW_ROOT_BUTTONS_KEY,
        SettingsManager.SHOW_ADDRESS_BAR_KEY,
        SettingsManager.SHOW_NAVIGATION_BUTTONS_KEY,
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
        SettingsManager.FILE_OPEN_OVERRIDES_JSON_KEY,
        SettingsManager.USE_EXTENDED_PATHS_ROBOCOPY_KEY,
        SettingsManager.USE_EXTENDED_PATHS_TERACOPY_KEY,
        SettingsManager.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_CMD_DELETE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY,
        SettingsManager.USE_EXTENDED_PATHS_RIMRAF_KEY,
        SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY,
        SettingsManager.SCRIPT_EDITOR_EXECUTABLE_KEY,
        SettingsManager.TERACOPY_EXECUTABLE_KEY,
        SettingsManager.TERACOPY_ARGS_TEMPLATE_KEY,
        SettingsManager.UNSTOPPABLE_EXECUTABLE_KEY,
        SettingsManager.UNSTOPPABLE_ARGS_TEMPLATE_KEY,
        SettingsManager.GENERIC_COPYMOVE_EXECUTABLE_KEY,
        SettingsManager.GENERIC_COPYMOVE_ARGS_TEMPLATE_KEY,
        SettingsManager.GENERIC_DELETE_EXECUTABLE_KEY,
        SettingsManager.GENERIC_DELETE_ARGS_TEMPLATE_KEY,
        SettingsManager.ROBOCOPY_COPY_ARGS_KEY,
        SettingsManager.ROBOCOPY_MOVE_ARGS_KEY,
        SettingsManager.CMD_DELETE_ARGS_KEY,
        SettingsManager.POWERSHELL_DELETE_ARGS_KEY,
        SettingsManager.RIMRAF_EXECUTABLE_KEY,
        SettingsManager.RIMRAF_ARGS_TEMPLATE_KEY,
        SettingsManager.OPS_COMPANION_BOOTSTRAP_DONE_KEY,
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
            column_width_auto_align_mode="all_panels_tabs",
            show_refresh_button=False,
            show_root_buttons=False,
            show_address_bar=False,
            show_navigation_buttons=False,
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
            file_open_overrides_json='{".txt": {"editor": "txtedit.exe", "viewer": "txtview.exe"}}',
            use_extended_paths_robocopy=True,
            use_extended_paths_teracopy=True,
            use_extended_paths_unstoppable=True,
            use_extended_paths_external_copymove=True,
            use_extended_paths_cmd_delete=True,
            use_extended_paths_powershell_delete=True,
            use_extended_paths_rimraf=True,
            use_extended_paths_external_delete=True,
            script_editor_executable=r"C:\tools\my-editor.exe",
            teracopy_executable="TeraCopy.exe",
            teracopy_args_template="{operation} {sources} {target} /close",
            unstoppable_executable="UnstoppableCopier.exe",
            unstoppable_args_template="{operation} {sources} {target}",
            generic_copymove_executable="my-copy.exe",
            generic_copymove_args_template="{operation} {sources} {target}",
            generic_delete_executable="my-del.exe",
            generic_delete_args_template="{operation} {sources}",
            robocopy_copy_args="/E /R:0 /W:0",
            robocopy_move_args="/E /MOVE /R:0 /W:0",
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


def test_ui_preferences_invalid_values_fallback_to_defaults() -> None:
    settings = SettingsManager()
    before = _snapshot(settings)
    try:
        settings.set_value(SettingsManager.NEW_CONTEXT_MODE_KEY, "invalid-mode")
        settings.remove(SettingsManager.SHOW_ROOT_DROPDOWN_KEY)
        settings.set_value(
            SettingsManager.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY, "invalid-align-mode"
        )
        settings.remove(SettingsManager.SHOW_REFRESH_BUTTON_KEY)
        settings.remove(SettingsManager.SHOW_ROOT_BUTTONS_KEY)
        settings.remove(SettingsManager.SHOW_ADDRESS_BAR_KEY)
        settings.remove(SettingsManager.SHOW_NAVIGATION_BUTTONS_KEY)
        settings.remove(SettingsManager.APP_FONT_FAMILY_KEY)
        settings.remove(SettingsManager.APP_FONT_SIZE_PT_KEY)
        settings.remove(SettingsManager.FILE_LIST_USE_APP_FONT_KEY)
        settings.remove(SettingsManager.FILE_LIST_FONT_FAMILY_KEY)
        settings.remove(SettingsManager.FILE_LIST_FONT_SIZE_PT_KEY)
        settings.remove(SettingsManager.NAVIGATION_USE_APP_FONT_KEY)
        settings.remove(SettingsManager.NAVIGATION_FONT_FAMILY_KEY)
        settings.remove(SettingsManager.NAVIGATION_FONT_SIZE_PT_KEY)
        settings.set_value(SettingsManager.CONTEXT_IMMEDIATE_CHILD_SCAN_CAP_KEY, "invalid")
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
        settings.set_value(SettingsManager.DEFAULT_OPERATION_DISPATCH_MODE_KEY, "invalid")
        settings.set_value(SettingsManager.DEFAULT_OPERATION_CONFLICT_POLICY_KEY, "invalid")
        settings.set_value(SettingsManager.OPERATION_SHORTCUT_BEHAVIOR_KEY, "invalid")
        settings.set_value(SettingsManager.OPERATION_QUEUE_VIEW_MODE_KEY, "invalid")
        settings.remove(SettingsManager.DEFAULT_EDITOR_EXECUTABLE_KEY)
        settings.remove(SettingsManager.DEFAULT_VIEWER_EXECUTABLE_KEY)
        settings.set_value(SettingsManager.FILE_OPEN_OVERRIDES_JSON_KEY, "not-json")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_ROBOCOPY_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_TERACOPY_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_CMD_DELETE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_RIMRAF_KEY, "")
        settings.set_value(SettingsManager.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY, "")
        settings.remove(SettingsManager.SCRIPT_EDITOR_EXECUTABLE_KEY)
        settings.remove(SettingsManager.TERACOPY_EXECUTABLE_KEY)
        settings.remove(SettingsManager.TERACOPY_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.UNSTOPPABLE_EXECUTABLE_KEY)
        settings.remove(SettingsManager.UNSTOPPABLE_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.GENERIC_COPYMOVE_EXECUTABLE_KEY)
        settings.remove(SettingsManager.GENERIC_COPYMOVE_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.GENERIC_DELETE_EXECUTABLE_KEY)
        settings.remove(SettingsManager.GENERIC_DELETE_ARGS_TEMPLATE_KEY)
        settings.remove(SettingsManager.ROBOCOPY_COPY_ARGS_KEY)
        settings.remove(SettingsManager.ROBOCOPY_MOVE_ARGS_KEY)
        settings.remove(SettingsManager.CMD_DELETE_ARGS_KEY)
        settings.remove(SettingsManager.POWERSHELL_DELETE_ARGS_KEY)
        settings.remove(SettingsManager.RIMRAF_EXECUTABLE_KEY)
        settings.remove(SettingsManager.RIMRAF_ARGS_TEMPLATE_KEY)

        loaded = settings.ui_preferences()
        assert loaded.new_context_mode == "clone_active_path"
        assert loaded.show_root_dropdown is False
        assert (
            loaded.column_width_auto_align_mode
            == SettingsManager.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        )
        assert loaded.show_refresh_button is True
        assert loaded.show_root_buttons is True
        assert loaded.show_address_bar is True
        assert loaded.show_navigation_buttons is True
        assert loaded.app_font_family == SettingsManager.DEFAULT_APP_FONT_FAMILY
        assert loaded.app_font_size_pt == SettingsManager.DEFAULT_APP_FONT_SIZE_PT
        assert (
            loaded.file_list_use_app_font
            == SettingsManager.DEFAULT_FILE_LIST_USE_APP_FONT
        )
        assert (
            loaded.file_list_font_family == SettingsManager.DEFAULT_FILE_LIST_FONT_FAMILY
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
        assert loaded.default_copy_move_backend == SettingsManager.DEFAULT_COPY_MOVE_BACKEND
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
            loaded.file_open_overrides_json
            == SettingsManager.DEFAULT_FILE_OPEN_OVERRIDES_JSON
        )
        assert loaded.use_extended_paths_robocopy is False
        assert loaded.use_extended_paths_teracopy is False
        assert loaded.use_extended_paths_unstoppable is False
        assert loaded.use_extended_paths_external_copymove is False
        assert loaded.use_extended_paths_cmd_delete is False
        assert loaded.use_extended_paths_powershell_delete is False
        assert loaded.use_extended_paths_rimraf is False
        assert loaded.use_extended_paths_external_delete is False
        assert (
            loaded.script_editor_executable
            == SettingsManager.DEFAULT_SCRIPT_EDITOR_EXECUTABLE
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
