import os
from os import linesep
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox, QTabWidget

from many_panelz_explorer._operations.backend_options import (
    resolve_copy_move_backend_args,
)
from many_panelz_explorer._operations.discovery import resolve_companion_tool_paths
from many_panelz_explorer._operations.queue_manager import OperationQueueManager
from many_panelz_explorer._operations.types import (
    OperationExecutionPreferences,
    OperationResult,
)
from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer._settings.models import UiPreferences
from many_panelz_explorer.dialogs.settings_dialog import SettingsDialog
from many_panelz_explorer.explorer_tab import ExplorerTab
from many_panelz_explorer.operation_queue_widgets import OperationQueueTableModel
from many_panelz_explorer.terminal_launchers import (
    TerminalLauncherSettings,
    configure_terminal_launchers,
    current_terminal_launcher_settings,
)
from many_panelz_explorer.window import ExplorerWindow


class _ControllerSettingsStub:
    def __init__(self, settings: SettingsManager) -> None:
        self.settings = settings
        app = QApplication.instance()
        assert app is not None
        self._app = app
        self._default_app_font = QFont(app.font())
        self.windows: list[ExplorerWindow] = []
        self.preview_calls: list[UiPreferences] = []
        self.operation_queue_manager = OperationQueueManager(
            preferences=OperationExecutionPreferences()
        )
        self.operation_queue_model = OperationQueueTableModel(
            self.operation_queue_manager
        )

    def close_window(self, _window: ExplorerWindow) -> None:
        return

    def current_ui_preferences(self) -> UiPreferences:
        return self.settings.ui_preferences()

    def preview_ui_preferences(self, preferences: UiPreferences) -> None:
        self.preview_calls.append(preferences)
        configure_terminal_launchers(
            TerminalLauncherSettings(
                default_terminal_launcher=preferences.default_terminal_launcher,
                comspec_terminal_executable=preferences.comspec_terminal_executable,
                comspec_terminal_open_args_template=(
                    preferences.comspec_terminal_open_args_template
                ),
                comspec_terminal_command_args_template=(
                    preferences.comspec_terminal_command_args_template
                ),
                comspec_terminal_startup_position=(
                    preferences.comspec_terminal_startup_position
                ),
                pwsh_terminal_executable=preferences.pwsh_terminal_executable,
                pwsh_terminal_open_args_template=(
                    preferences.pwsh_terminal_open_args_template
                ),
                pwsh_terminal_command_args_template=(
                    preferences.pwsh_terminal_command_args_template
                ),
                pwsh_terminal_startup_position=(
                    preferences.pwsh_terminal_startup_position
                ),
                powershell5_terminal_executable=(
                    preferences.powershell5_terminal_executable
                ),
                powershell5_terminal_open_args_template=(
                    preferences.powershell5_terminal_open_args_template
                ),
                powershell5_terminal_command_args_template=(
                    preferences.powershell5_terminal_command_args_template
                ),
                powershell5_terminal_startup_position=(
                    preferences.powershell5_terminal_startup_position
                ),
            )
        )
        resolved_copy_move = resolve_copy_move_backend_args(
            robocopy_options=preferences.robocopy_structured_options,
            teracopy_options=preferences.teracopy_structured_options,
            unstoppable_options=preferences.unstoppable_structured_options,
            external_copymove_options=preferences.external_copymove_structured_options,
        )
        self.operation_queue_manager.set_preferences(
            resolve_companion_tool_paths(
                OperationExecutionPreferences(
                    default_copy_move_backend=preferences.default_copy_move_backend,
                    default_delete_backend=preferences.default_delete_backend,
                    default_dispatch_mode=preferences.default_operation_dispatch_mode,
                    default_conflict_policy=preferences.default_operation_conflict_policy,
                    shortcut_behavior=preferences.operation_shortcut_behavior,
                    queue_view_mode=preferences.operation_queue_view_mode,
                    default_editor_executable=preferences.default_editor_executable,
                    default_viewer_executable=preferences.default_viewer_executable,
                    file_open_overrides_json=preferences.file_open_overrides_json,
                    use_extended_paths_robocopy=preferences.use_extended_paths_robocopy,
                    use_extended_paths_teracopy=preferences.use_extended_paths_teracopy,
                    use_extended_paths_unstoppable=preferences.use_extended_paths_unstoppable,
                    use_extended_paths_external_copymove=preferences.use_extended_paths_external_copymove,
                    use_extended_paths_cmd_delete=preferences.use_extended_paths_cmd_delete,
                    use_extended_paths_powershell_delete=preferences.use_extended_paths_powershell_delete,
                    use_extended_paths_rimraf=preferences.use_extended_paths_rimraf,
                    use_extended_paths_external_delete=preferences.use_extended_paths_external_delete,
                    teracopy_executable=preferences.teracopy_executable,
                    teracopy_args_template=resolved_copy_move.teracopy_args_template,
                    unstoppable_executable=preferences.unstoppable_executable,
                    unstoppable_args_template=resolved_copy_move.unstoppable_args_template,
                    generic_copymove_executable=preferences.generic_copymove_executable,
                    generic_copymove_args_template=resolved_copy_move.external_copymove_args_template,
                    generic_delete_executable=preferences.generic_delete_executable,
                    generic_delete_args_template=preferences.generic_delete_args_template,
                    robocopy_copy_args=resolved_copy_move.robocopy_copy_args,
                    robocopy_move_args=resolved_copy_move.robocopy_move_args,
                    cmd_delete_args=preferences.cmd_delete_args,
                    powershell_delete_args=preferences.powershell_delete_args,
                    rimraf_executable=preferences.rimraf_executable,
                    rimraf_args_template=preferences.rimraf_args_template,
                )
            )
        )
        self._apply_application_font(preferences)
        for window in list(self.windows):
            window.preferences_coordinator.apply_ui_preferences(preferences)

    def apply_ui_preferences(self, preferences: UiPreferences) -> None:
        self.settings.set_ui_preferences(preferences)
        self.settings.sync()
        self.preview_ui_preferences(preferences)

    def broadcast_column_widths(
        self,
        widths: list[object],
        *,
        source_window: ExplorerWindow | None = None,
        source_panel_id: int | None = None,
        source_tab: ExplorerTab | None = None,
    ) -> None:
        for window in list(self.windows):
            window.panels_coordinator.column_sync_coordinator.apply_column_widths_all_panels(
                widths,
                source_panel_id=source_panel_id if window is source_window else None,
                source_tab=source_tab if window is source_window else None,
            )

    def _apply_application_font(self, preferences: UiPreferences) -> None:
        font = QFont(self._default_app_font)
        family = str(preferences.app_font_family or "").strip()
        if family:
            font.setFamily(family)
        if int(preferences.app_font_size_pt) > 0:
            font.setPointSize(int(preferences.app_font_size_pt))
        self._app.setFont(font)

    def show_queue_floating_window(self):
        return None


def _test_roots_provider(tmp_path: Path):
    root = tmp_path / "roots"
    root.mkdir(parents=True, exist_ok=True)
    return lambda _current: [root]


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
        SettingsManager.SHOW_TAB_CLOSE_BUTTONS_KEY,
        SettingsManager.DEFAULT_TAB_POSITION_KEY,
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
        SettingsManager.SETTINGS_DIALOG_LAST_SECTION_KEY,
        SettingsManager.SETTINGS_DIALOG_LAST_SUBSECTION_KEY,
        f"ui/windows/{SettingsDialog.WINDOW_ID}/geometry",
    ]


@pytest.fixture
def isolated_settings() -> SettingsManager:
    settings = SettingsManager()
    keys = _tracked_keys()
    geometry_key = f"ui/windows/{SettingsDialog.WINDOW_ID}/geometry"
    snapshot = {key: settings.value(key, None) for key in keys if key != geometry_key}
    geometry_snapshot = settings.get_json(geometry_key, None)
    app = QApplication.instance()
    assert app is not None
    app_font_snapshot = QFont(app.font())
    terminal_snapshot = current_terminal_launcher_settings()
    try:
        yield settings
    finally:
        for key, value in snapshot.items():
            if value is None:
                settings.remove(key)
            else:
                settings.set_value(key, value)
        if geometry_snapshot is None:
            settings.remove(geometry_key)
        else:
            settings.set_json(geometry_key, geometry_snapshot)
        settings.sync()
        app.setFont(app_font_snapshot)
        configure_terminal_launchers(terminal_snapshot)


def _new_window(
    qtbot,
    *,
    controller: _ControllerSettingsStub,
    settings: SettingsManager,
    window_id: str,
    roots_provider,
) -> ExplorerWindow:
    window = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id=window_id,
        roots_provider=roots_provider,
    )
    controller.windows.append(window)
    qtbot.addWidget(window)
    window.show()
    return window


def test_settings_action_in_view_menu_and_shortcut_trigger(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-shortcut",
        roots_provider=roots_provider,
    )

    triggered: list[str] = []
    window.settings_action.triggered.disconnect()
    window.settings_action.triggered.connect(lambda: triggered.append("fired"))

    window.settings_action.trigger()
    assert triggered == ["fired"]
    assert window.settings_action.shortcut().toString() == "Ctrl+,"


def test_settings_search_filters_rows_in_place(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-search",
        roots_provider=roots_provider,
    )

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.search_edit.setText("root dropdown")
    qtbot.waitUntil(lambda: dialog._rows_by_key["show_root_dropdown"].isVisible())
    assert dialog._rows_by_key["show_hidden_default"].isVisible() is False
    assert dialog._rows_by_key["active_color"].isVisible() is False

    dialog.search_edit.setText("navigation font")
    qtbot.waitUntil(lambda: dialog._rows_by_key["navigation_font"].isVisible())
    assert dialog._rows_by_key["app_font"].isVisible() is False

    dialog.search_edit.setText("column width align")
    qtbot.waitUntil(
        lambda: dialog._rows_by_key["column_width_auto_align_mode"].isVisible()
    )
    assert dialog._rows_by_key["show_hidden_default"].isVisible() is False

    dialog.search_edit.setText("autofit columns")
    qtbot.waitUntil(lambda: dialog._rows_by_key["autofit_columns"].isVisible())
    assert dialog._rows_by_key["column_width_auto_align_mode"].isVisible() is False


def test_settings_dialog_restores_saved_window_geometry(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-geometry",
        roots_provider=roots_provider,
    )

    first = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(first)
    first.show()
    qtbot.waitUntil(first.isVisible)
    first.resize(1320, 900)
    first.move(54, 63)
    qtbot.waitUntil(
        lambda: (
            first.width() == 1320
            and first.height() == 900
            and first.x() == 54
            and first.y() == 63
        )
    )
    first.close()

    second = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(second)
    second.show()
    qtbot.waitUntil(
        lambda: (
            second.width() == 1320
            and second.height() == 900
            and second.x() == 54
            and second.y() == 63
        )
    )

    assert second.width() == 1320
    assert second.height() == 900
    assert second.x() == 54
    assert second.y() == 63


def test_settings_column_width_align_combo_exposes_all_scopes(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-column-align-scopes",
        roots_provider=roots_provider,
    )

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    options = [
        (
            dialog.column_width_auto_align_mode_combo.itemText(index),
            str(dialog.column_width_auto_align_mode_combo.itemData(index)),
        )
        for index in range(dialog.column_width_auto_align_mode_combo.count())
    ]
    assert options == [
        ("Current panel tabs", "current_panel_tabs"),
        (
            "All panels and tabs in current window",
            "current_window_panels_tabs",
        ),
        (
            "All panels and tabs in all windows",
            "all_windows_panels_tabs",
        ),
        ("No alignment", "none"),
    ]


def test_settings_live_preview_is_debounced(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-debounce",
        roots_provider=roots_provider,
    )

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    start_calls = len(controller.preview_calls)
    dialog.active_intensity_slider.setValue(31)
    dialog.active_intensity_slider.setValue(32)
    dialog.active_intensity_slider.setValue(33)
    qtbot.wait(80)
    assert len(controller.preview_calls) == start_calls

    qtbot.waitUntil(lambda: len(controller.preview_calls) == start_calls + 1)
    last = controller.preview_calls[-1]
    assert last.active_panel_tint_intensity_percent == 33


def test_app_font_size_spin_skips_values_below_minimum(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-app-font-step",
        roots_provider=roots_provider,
    )

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.app_font_size_spin.setValue(0)
    dialog.app_font_size_spin.stepUp()
    assert dialog.app_font_size_spin.value() == 6

    dialog.app_font_size_spin.stepDown()
    assert dialog.app_font_size_spin.value() == 0


def test_settings_app_font_preview_and_cancel_revert(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-app-font-preview",
        roots_provider=roots_provider,
    )
    _ = window
    baseline_size = QApplication.instance().font().pointSize()

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.app_font_size_spin.setValue(16)
    qtbot.waitUntil(lambda: QApplication.instance().font().pointSize() == 16)

    dialog.reject()
    qtbot.waitUntil(lambda: QApplication.instance().font().pointSize() == baseline_size)


def test_settings_live_preview_all_windows_and_cancel_revert(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    isolated_settings.set_ui_preferences(
        UiPreferences(
            new_context_mode="clone_active_path",
            show_hidden_default=True,
            show_root_dropdown=False,
            column_width_auto_align_mode="current_panel_tabs",
            autofit_columns=False,
            show_refresh_button=True,
            show_root_buttons=True,
            show_address_bar=True,
            show_navigation_buttons=True,
            show_tab_close_buttons=True,
            app_font_family="",
            app_font_size_pt=0,
            file_list_use_app_font=True,
            file_list_font_family="",
            file_list_font_size_pt=10,
            navigation_use_app_font=True,
            navigation_font_family="",
            navigation_font_size_pt=10,
            active_panel_tint_color_hex="#A8B6C4",
            active_panel_tint_intensity_percent=24,
            target_panel_tint_color_hex="#D2CCAA",
            target_panel_tint_intensity_percent=28,
        )
    )
    isolated_settings.sync()

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    first = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-preview-first",
        roots_provider=roots_provider,
    )
    second = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-preview-second",
        roots_provider=roots_provider,
    )

    first_active = first.panels_coordinator.active_panel()
    second_active = second.panels_coordinator.active_panel()
    assert first_active is not None
    assert second_active is not None
    assert "rgba(168, 182, 196, 61)" in first_active.styleSheet()
    assert "rgba(168, 182, 196, 61)" in second_active.styleSheet()

    dialog = SettingsDialog(controller=controller, parent=first)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.active_intensity_slider.setValue(60)
    qtbot.waitUntil(lambda: "rgba(168, 182, 196, 153)" in first_active.styleSheet())
    assert "rgba(168, 182, 196, 153)" in second_active.styleSheet()
    dialog.show_root_dropdown_checkbox.setChecked(True)
    dialog.show_refresh_button_checkbox.setChecked(False)
    dialog.show_tab_close_buttons_checkbox.setChecked(False)
    qtbot.waitUntil(lambda: first_active.root_combo.isVisible() is True)
    assert second_active.root_combo.isVisible() is True
    assert first_active.refresh_btn.isVisible() is False
    assert second_active.refresh_btn.isVisible() is False
    assert first_active.tabs.tabsClosable() is False
    assert second_active.tabs.tabsClosable() is False

    dialog.reject()
    qtbot.waitUntil(lambda: "rgba(168, 182, 196, 61)" in first_active.styleSheet())
    assert "rgba(168, 182, 196, 61)" in second_active.styleSheet()
    assert first_active.root_combo.isVisible() is False
    assert second_active.root_combo.isVisible() is False
    assert first_active.refresh_btn.isVisible() is True
    assert second_active.refresh_btn.isVisible() is True
    assert first_active.tabs.tabsClosable() is True
    assert second_active.tabs.tabsClosable() is True


def test_settings_apply_persists_and_new_window_uses_values(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-apply-source",
        roots_provider=roots_provider,
    )

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.active_intensity_slider.setValue(50)
    dialog.target_intensity_slider.setValue(40)
    dialog.show_hidden_checkbox.setChecked(False)
    dialog.show_root_dropdown_checkbox.setChecked(True)
    dialog.autofit_columns_checkbox.setChecked(True)
    dialog.show_refresh_button_checkbox.setChecked(False)
    dialog.show_root_buttons_checkbox.setChecked(False)
    dialog.show_address_bar_checkbox.setChecked(False)
    dialog.show_navigation_buttons_checkbox.setChecked(False)
    dialog.show_tab_close_buttons_checkbox.setChecked(False)
    dialog.show_storage_overview_status_row_checkbox.setChecked(False)
    dialog.byte_thousands_separator_edit.setText(" ")
    dialog.byte_decimal_separator_edit.setText(",")
    dialog.set_combo_value(dialog.file_list_byte_format_mode_combo, "custom")
    dialog.file_list_byte_custom_template_edit.setText("{b} ({MiB:.2f})")
    dialog.set_combo_value(dialog.status_bar_byte_format_mode_combo, "always_mib")
    dialog.status_bar_storage_label_template_edit.setText(
        "{disk_root} {disk_label} {used_space}/{total_space} {usage_indicator}"
    )
    dialog.set_combo_value(dialog.properties_byte_format_mode_combo, "always_mb")
    dialog.app_font_size_spin.setValue(12)
    dialog.file_list_use_app_font_checkbox.setChecked(False)
    dialog.file_list_font_size_spin.setValue(14)
    dialog.navigation_use_app_font_checkbox.setChecked(False)
    dialog.navigation_font_size_spin.setValue(13)
    dialog._apply_and_commit()

    persisted = isolated_settings.ui_preferences()
    assert persisted.active_panel_tint_intensity_percent == 50
    assert persisted.target_panel_tint_intensity_percent == 40
    assert persisted.show_hidden_default is False
    assert persisted.show_root_dropdown is True
    assert persisted.autofit_columns is True
    assert persisted.show_refresh_button is False
    assert persisted.show_root_buttons is False
    assert persisted.show_address_bar is False
    assert persisted.show_navigation_buttons is False
    assert persisted.show_tab_close_buttons is False
    assert persisted.show_storage_overview_status_row is False
    assert persisted.byte_thousands_separator == " "
    assert persisted.byte_decimal_separator == ","
    assert persisted.file_list_byte_format_mode == "custom"
    assert persisted.file_list_byte_custom_template == "{b} ({MiB:.2f})"
    assert persisted.status_bar_byte_format_mode == "always_mib"
    assert (
        persisted.status_bar_storage_label_template
        == "{disk_root} {disk_label} {used_space}/{total_space} {usage_indicator}"
    )
    assert persisted.properties_byte_format_mode == "always_mb"
    assert persisted.app_font_size_pt == 12
    assert persisted.file_list_use_app_font is False
    assert persisted.file_list_font_size_pt == 14
    assert persisted.navigation_use_app_font is False
    assert persisted.navigation_font_size_pt == 13

    reopened = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-apply-reopened",
        roots_provider=roots_provider,
    )
    reopened_panel = reopened.panels_coordinator.active_panel()
    assert reopened_panel is not None
    assert reopened.show_hidden_action.isChecked() is False
    assert reopened_panel.root_combo.isVisible() is True
    assert reopened_panel.refresh_btn.isVisible() is False
    assert reopened_panel.root_buttons_host.isVisible() is False
    assert reopened_panel.address_edit.isVisible() is False
    assert reopened_panel.back_btn.isVisible() is False
    assert reopened_panel.forward_btn.isVisible() is False
    assert reopened_panel.up_btn.isVisible() is False
    assert reopened_panel.root_btn.isVisible() is False
    assert reopened_panel.tabs.tabsClosable() is False
    assert reopened.storage_overview_row.isVisible() is False
    assert reopened_panel.current_tab().view.font().pointSize() == 14
    assert reopened_panel.address_edit.font().pointSize() == 13
    assert "rgba(168, 182, 196, 127)" in reopened_panel.styleSheet()


def test_settings_checkbox_changes_sync_existing_windows(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    isolated_settings.show_hidden_default = True
    isolated_settings.show_root_dropdown = False
    isolated_settings.sync()

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    first = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-sync-first",
        roots_provider=roots_provider,
    )
    second = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-sync-second",
        roots_provider=roots_provider,
    )

    dialog = SettingsDialog(controller=controller, parent=first)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.show_hidden_checkbox.setChecked(False)
    dialog.show_root_dropdown_checkbox.setChecked(True)
    dialog.show_refresh_button_checkbox.setChecked(False)
    dialog.show_root_buttons_checkbox.setChecked(False)
    dialog.show_address_bar_checkbox.setChecked(False)
    dialog.show_navigation_buttons_checkbox.setChecked(False)
    dialog.show_tab_close_buttons_checkbox.setChecked(False)
    dialog.show_storage_overview_status_row_checkbox.setChecked(False)
    dialog.app_font_size_spin.setValue(11)
    dialog.file_list_use_app_font_checkbox.setChecked(False)
    dialog.file_list_font_size_spin.setValue(15)
    dialog.navigation_use_app_font_checkbox.setChecked(False)
    dialog.navigation_font_size_spin.setValue(12)
    qtbot.waitUntil(lambda: first.show_hidden_action.isChecked() is False)
    assert second.show_hidden_action.isChecked() is False

    first_panel = first.panels_coordinator.active_panel()
    second_panel = second.panels_coordinator.active_panel()
    assert first_panel is not None
    assert second_panel is not None
    assert first_panel.root_combo.isVisible() is True
    assert second_panel.root_combo.isVisible() is True
    assert first_panel.refresh_btn.isVisible() is False
    assert second_panel.refresh_btn.isVisible() is False
    assert first_panel.root_buttons_host.isVisible() is False
    assert second_panel.root_buttons_host.isVisible() is False
    assert first_panel.address_edit.isVisible() is False
    assert second_panel.address_edit.isVisible() is False
    assert first_panel.back_btn.isVisible() is False
    assert second_panel.back_btn.isVisible() is False
    assert first_panel.tabs.tabsClosable() is False
    assert second_panel.tabs.tabsClosable() is False
    assert first.storage_overview_row.isVisible() is False
    assert second.storage_overview_row.isVisible() is False
    assert first_panel.current_tab().view.font().pointSize() == 15
    assert second_panel.current_tab().view.font().pointSize() == 15


def test_settings_dialog_has_larger_minimum_size_and_operations_controls(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-size-ops",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.minimumWidth() >= 1080
    assert dialog.minimumHeight() >= 760
    dialog.search_edit.setText("teracopy executable")
    qtbot.waitUntil(lambda: dialog._rows_by_key["teracopy_command"].isVisible())
    assert dialog.teracopy_executable_edit.isVisible() is True
    assert dialog.teracopy_struct_conflict_combo.isVisible() is True
    assert hasattr(dialog, "teracopy_args_edit") is False


def test_settings_dialog_shows_resolved_terminal_diagnostics(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-terminal-diagnostics",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    terminal_item = dialog._subsection_tree_items["operations/terminal_tools"]
    dialog._section_tree.setCurrentItem(terminal_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is terminal_item)

    assert dialog.resolved_comspec_terminal_path_label.text().startswith("ComSpec:")
    assert dialog.resolved_pwsh_terminal_path_label.text().startswith("PowerShell 7:")
    assert dialog.resolved_powershell5_terminal_path_label.text().startswith(
        "Windows PowerShell 5.1:"
    )


def test_settings_dialog_populates_terminal_executables_with_resolved_paths(
    qtbot,
    tmp_path: Path,
    isolated_settings: SettingsManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmd_path = tmp_path / "Windows" / "System32" / "cmd.exe"
    pwsh_path = tmp_path / "PowerShell" / "7" / "pwsh.exe"
    powershell5_path = (
        tmp_path
        / "Windows"
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    cmd_path.parent.mkdir(parents=True, exist_ok=True)
    pwsh_path.parent.mkdir(parents=True, exist_ok=True)
    powershell5_path.parent.mkdir(parents=True, exist_ok=True)
    cmd_path.write_text("", encoding="utf-8")
    pwsh_path.write_text("", encoding="utf-8")
    powershell5_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("ComSpec", str(cmd_path))
    monkeypatch.setenv("PATH", str(pwsh_path.parent))
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "Windows"))

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-terminal-resolved-paths",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.comspec_terminal_executable_edit.text() == str(cmd_path)
    assert dialog.pwsh_terminal_executable_edit.text() == str(pwsh_path)
    assert dialog.powershell5_terminal_executable_edit.text() == str(powershell5_path)


def test_settings_dialog_embeds_terminal_startup_position_in_launcher_group(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-terminal-startup-layout",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    terminal_item = dialog._subsection_tree_items["operations/terminal_tools"]
    dialog._section_tree.setCurrentItem(terminal_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is terminal_item)

    assert "comspec_terminal_startup_position" not in dialog._rows_by_key
    assert "pwsh_terminal_startup_position" not in dialog._rows_by_key
    assert "powershell5_terminal_startup_position" not in dialog._rows_by_key
    assert dialog.comspec_terminal_startup_position_combo.isVisible() is True
    assert dialog.pwsh_terminal_startup_position_combo.isVisible() is True
    assert dialog.powershell5_terminal_startup_position_combo.isVisible() is True


def test_settings_dialog_has_left_section_tree_and_search_sync(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-tree",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog._section_tree.topLevelItemCount() >= 5
    operations_item = dialog._section_tree_items["operations"]
    assert operations_item.childCount() >= 6
    dialog._section_tree.setCurrentItem(operations_item)
    qtbot.waitUntil(
        lambda: (
            dialog._section_tree.currentItem()
            is dialog._subsection_tree_items["operations/defaults_queue"]
        )
    )
    backend_commands_item = dialog._subsection_tree_items["operations/backend_commands"]
    dialog._section_tree.setCurrentItem(backend_commands_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is backend_commands_item)
    assert dialog._rows_by_key["teracopy_command"].isVisible() is True
    assert dialog._rows_by_key["default_copy_move_backend"].isVisible() is False

    dialog.search_edit.setText("version")
    qtbot.waitUntil(lambda: dialog._rows_by_key["about_version"].isVisible())
    assert dialog._section_tree_items["operations"].isHidden() is True
    assert dialog._section_tree_items["about"].isHidden() is False
    assert (
        dialog._section_tree.currentItem()
        is dialog._subsection_tree_items["about/application_info"]
    )


def test_settings_dialog_remembers_last_selected_subsection(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-memory",
        roots_provider=roots_provider,
    )

    first = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(first)
    first.show()

    remembered_item = first._subsection_tree_items["operations/backend_args"]
    first._section_tree.setCurrentItem(remembered_item)
    qtbot.waitUntil(lambda: first._section_tree.currentItem() is remembered_item)
    assert controller.settings.settings_dialog_last_section == "operations"
    assert (
        controller.settings.settings_dialog_last_subsection == "operations/backend_args"
    )
    first.reject()

    second = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(second)
    second.show()

    qtbot.waitUntil(
        lambda: (
            second._section_tree.currentItem()
            is second._subsection_tree_items["operations/backend_args"]
        )
    )
    assert second._rows_by_key["robocopy_args"].isVisible() is True
    assert second._rows_by_key["teracopy_command"].isVisible() is False


def test_settings_dialog_has_contextual_reset_bar_and_search_updates_target(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-reset-search",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    assert "reset" not in dialog._section_tree_items
    assert (
        dialog._reset_actions_bar.property("widget_alias")
        == "settings.reset.context_bar"
    )

    operations_item = dialog._subsection_tree_items["operations/backend_args"]
    dialog._section_tree.setCurrentItem(operations_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is operations_item)
    assert dialog.reset_section_context_label.text() == "Current Section: Operations"
    assert dialog.reset_section_button.isEnabled() is True

    dialog.search_edit.setText("version")
    qtbot.waitUntil(lambda: dialog._rows_by_key["about_version"].isVisible())
    assert (
        dialog._section_tree.currentItem()
        is dialog._subsection_tree_items["about/application_info"]
    )
    assert dialog.reset_section_context_label.text() == "Current Section: About"
    assert dialog.reset_section_button.isEnabled() is False


def test_settings_dialog_reset_section_resets_selected_section_only(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-reset-subsection",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    panels_item = dialog._subsection_tree_items["panels/file_list_layout"]
    dialog._section_tree.setCurrentItem(panels_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is panels_item)
    dialog.show_hidden_checkbox.setChecked(False)
    dialog.show_root_dropdown_checkbox.setChecked(True)
    dialog.set_combo_value(dialog.column_width_auto_align_mode_combo, "none")
    dialog.autofit_columns_checkbox.setChecked(True)
    dialog.context_scan_cap_spin.setValue(77)

    dialog.reset_section_button.click()

    assert dialog.show_hidden_checkbox.isChecked() is True
    assert dialog.show_root_dropdown_checkbox.isChecked() is False
    assert (
        str(dialog.column_width_auto_align_mode_combo.currentData())
        == "current_panel_tabs"
    )
    assert dialog.autofit_columns_checkbox.isChecked() is False
    assert dialog.context_scan_cap_spin.value() == 77
    assert dialog._pending_full_store_reset is False


def test_settings_dialog_reset_everything_staged_until_apply(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager, monkeypatch
) -> None:
    isolated_settings.show_hidden_default = False
    isolated_settings.set_session_window_ids(["window-1"])
    isolated_settings.set_saved_view("View A", {"tabs": {}, "panel_tree": {}})
    isolated_settings.set_value("custom/gui_reset_unknown", "x")
    isolated_settings.sync()

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-reset-all-apply",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    monkeypatch.setattr(
        "many_panelz_explorer.dialogs.settings.preferences_flow.QMessageBox.warning",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    dialog.reset_all_button.click()

    assert dialog._pending_full_store_reset is True
    assert dialog.reset_pending_label.isVisible() is True
    assert dialog.show_hidden_checkbox.isChecked() is True
    assert isolated_settings.show_hidden_default is False
    assert isolated_settings.session_window_ids() == ["window-1"]
    assert isolated_settings.value("custom/gui_reset_unknown", None) == "x"

    dialog._apply_and_commit()

    assert isolated_settings.ui_preferences() == UiPreferences()
    assert isolated_settings.session_window_ids() == []
    assert isolated_settings.list_saved_views() == []
    assert isolated_settings.value("custom/gui_reset_unknown", None) is None


def test_settings_dialog_reset_everything_cancel_keeps_persisted_values(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager, monkeypatch
) -> None:
    isolated_settings.show_hidden_default = False
    isolated_settings.set_session_window_ids(["window-2"])
    isolated_settings.set_value("custom/gui_reset_unknown_cancel", "keep")
    isolated_settings.sync()

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-reset-all-cancel",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    monkeypatch.setattr(
        "many_panelz_explorer.dialogs.settings.preferences_flow.QMessageBox.warning",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    dialog.reset_all_button.click()
    assert dialog._pending_full_store_reset is True

    dialog.reject()

    assert isolated_settings.show_hidden_default is False
    assert isolated_settings.session_window_ids() == ["window-2"]
    assert isolated_settings.value("custom/gui_reset_unknown_cancel", None) == "keep"


def test_settings_dialog_command_textboxes_expand_with_resize(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-width",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.search_edit.setText("teracopy command")
    qtbot.waitUntil(lambda: dialog._rows_by_key["teracopy_command"].isVisible())
    initial_width = dialog.teracopy_executable_edit.width()
    dialog.resize(dialog.width() + 260, dialog.height())
    qtbot.waitUntil(lambda: dialog.teracopy_executable_edit.width() > initial_width)


def test_settings_byte_format_preview_and_persistence(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    isolated_settings.byte_thousands_separator = ","
    isolated_settings.byte_decimal_separator = "."
    isolated_settings.file_list_byte_format_mode = "bytes"
    isolated_settings.file_list_byte_custom_template = ""
    isolated_settings.sync()

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-byte-format",
        roots_provider=roots_provider,
    )

    root = tmp_path / "files"
    root.mkdir(parents=True, exist_ok=True)
    sample = root / "sample.bin"
    sample.write_bytes(b"x" * 3_500)
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    tab = panel.current_tab()
    assert tab is not None
    tab.navigation.set_path(root)
    qtbot.waitUntil(lambda: tab.model.index(str(sample)).isValid())
    sample_index = tab.model.index(str(sample)).siblingAtColumn(2)
    assert str(tab.model.data(sample_index, Qt.DisplayRole)) == "3,500"

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()
    byte_display_item = dialog._subsection_tree_items["panels/byte_display"]
    dialog._section_tree.setCurrentItem(byte_display_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is byte_display_item)

    dialog.set_combo_value(dialog.file_list_byte_format_mode_combo, "custom")
    assert dialog.file_list_byte_custom_template_edit.isEnabled() is True
    dialog.file_list_byte_custom_template_edit.setText("{KiB:.2f} KiB")
    dialog.byte_thousands_separator_edit.setText(".")
    dialog.byte_decimal_separator_edit.setText(",")
    qtbot.waitUntil(
        lambda: str(tab.model.data(sample_index, Qt.DisplayRole)) == "3,42 KiB"
    )
    assert str(tab.model.data(sample_index, Qt.DisplayRole)) == "3,42 KiB"

    dialog._apply_and_commit()
    persisted = isolated_settings.ui_preferences()
    assert persisted.file_list_byte_format_mode == "custom"
    assert persisted.file_list_byte_custom_template == "{KiB:.2f} KiB"
    assert persisted.byte_thousands_separator == "."
    assert persisted.byte_decimal_separator == ","


def test_settings_dialog_open_with_and_extended_path_settings_persist(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-open-with",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.default_editor_executable_edit.setText(r"C:\tools\editor.exe")
    dialog.default_viewer_executable_edit.setText(r"C:\tools\viewer.exe")
    dialog.set_combo_value(dialog.default_terminal_launcher_combo, "powershell5")
    dialog.comspec_terminal_executable_edit.setText("%ComSpec%")
    dialog.comspec_terminal_open_args_edit.setText("/K cd /d {folder}")
    dialog.comspec_terminal_command_args_edit.setText("/K {shell_command}")
    dialog.set_combo_value(
        dialog.comspec_terminal_startup_position_combo,
        "maximized",
    )
    dialog.pwsh_terminal_executable_edit.setText(
        r"C:\Program Files\PowerShell\7\pwsh.exe"
    )
    dialog.pwsh_terminal_open_args_edit.setText(
        "-NoExit -Command Set-Location -LiteralPath {folder}"
    )
    dialog.pwsh_terminal_command_args_edit.setText("-NoExit -Command {shell_command}")
    dialog.set_combo_value(
        dialog.pwsh_terminal_startup_position_combo,
        "right_of_screen",
    )
    dialog.powershell5_terminal_executable_edit.setText(
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    dialog.powershell5_terminal_open_args_edit.setText(
        "-NoExit -Command Set-Location -LiteralPath {folder}"
    )
    dialog.powershell5_terminal_command_args_edit.setText(
        "-NoExit -Command {shell_command}"
    )
    dialog.set_combo_value(
        dialog.powershell5_terminal_startup_position_combo,
        "left_of_screen",
    )
    dialog.context_scan_cap_spin.setValue(77)
    dialog.context_code_editor_executable_edit.setText(r"C:\tools\code.exe")
    dialog.context_code_editor_args_edit.setText("--folder {folder}")
    dialog.context_git_gui_executable_edit.setText(r"C:\tools\gitgui.exe")
    dialog.context_git_gui_args_edit.setText("--path {folder}")
    dialog.total_commander_executable_edit.setText(r"C:\tools\totalcmd64.exe")
    dialog.total_commander_source_args_edit.setText("/N /L={source}")
    dialog.total_commander_source_target_args_edit.setText("/N /L={source} /R={target}")
    dialog.double_commander_executable_edit.setText(r"C:\tools\doublecmd.exe")
    dialog.double_commander_source_args_edit.setText("--client -L {source}")
    dialog.double_commander_source_target_args_edit.setText(
        "--client -L {source} -R {target}"
    )
    dialog.show_storage_overview_status_row_checkbox.setChecked(False)
    dialog.add_override_row_btn.click()
    row = dialog.file_open_overrides_table.rowCount() - 1
    dialog.file_open_overrides_table.item(row, 0).setText(".log")
    dialog.file_open_overrides_table.item(row, 1).setText(r"C:\tools\logedit.exe")
    dialog.file_open_overrides_table.item(row, 2).setText(r"C:\tools\logview.exe")
    dialog.use_extended_paths_robocopy_checkbox.setChecked(True)
    dialog.use_extended_paths_external_delete_checkbox.setChecked(True)
    dialog._apply_and_commit()

    persisted = isolated_settings.ui_preferences()
    assert persisted.default_editor_executable == r"C:\tools\editor.exe"
    assert persisted.default_viewer_executable == r"C:\tools\viewer.exe"
    assert persisted.default_terminal_launcher == "powershell5"
    assert persisted.comspec_terminal_executable == "%ComSpec%"
    assert persisted.comspec_terminal_open_args_template == "/K cd /d {folder}"
    assert persisted.comspec_terminal_command_args_template == "/K {shell_command}"
    assert persisted.comspec_terminal_startup_position == "maximized"
    assert (
        persisted.pwsh_terminal_executable == r"C:\Program Files\PowerShell\7\pwsh.exe"
    )
    assert (
        persisted.pwsh_terminal_open_args_template
        == "-NoExit -Command Set-Location -LiteralPath {folder}"
    )
    assert (
        persisted.pwsh_terminal_command_args_template
        == "-NoExit -Command {shell_command}"
    )
    assert persisted.pwsh_terminal_startup_position == "right_of_screen"
    assert (
        persisted.powershell5_terminal_executable
        == r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    assert (
        persisted.powershell5_terminal_open_args_template
        == "-NoExit -Command Set-Location -LiteralPath {folder}"
    )
    assert (
        persisted.powershell5_terminal_command_args_template
        == "-NoExit -Command {shell_command}"
    )
    assert persisted.powershell5_terminal_startup_position == "left_of_screen"
    assert persisted.context_immediate_child_scan_cap == 77
    assert persisted.context_tool_code_editor_exe_path == r"C:\tools\code.exe"
    assert persisted.context_tool_code_editor_args_template == "--folder {folder}"
    assert persisted.context_tool_git_gui_exe_path == r"C:\tools\gitgui.exe"
    assert persisted.context_tool_git_gui_args_template == "--path {folder}"
    assert persisted.total_commander_executable == r"C:\tools\totalcmd64.exe"
    assert persisted.total_commander_source_args_template == "/N /L={source}"
    assert (
        persisted.total_commander_source_target_args_template
        == "/N /L={source} /R={target}"
    )
    assert persisted.double_commander_executable == r"C:\tools\doublecmd.exe"
    assert persisted.double_commander_source_args_template == "--client -L {source}"
    assert (
        persisted.double_commander_source_target_args_template
        == "--client -L {source} -R {target}"
    )
    assert persisted.show_storage_overview_status_row is False
    assert '".log"' in persisted.file_open_overrides_json
    assert persisted.use_extended_paths_robocopy is True
    assert persisted.use_extended_paths_external_delete is True


def test_settings_dialog_default_tab_position_updates_follow_default_panels(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    isolated_settings.default_tab_position = "top"
    isolated_settings.sync()

    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-tab-position",
        roots_provider=roots_provider,
    )

    ordered_ids = [panel_id for row in window.layout_rows for panel_id in row]
    first_panel = window.panel_widgets[ordered_ids[0]]
    second_panel = window.panel_widgets[ordered_ids[1]]
    window.panels_coordinator.set_active_panel(second_panel.panel_id)
    window.panels_coordinator.set_active_panel_tab_position_mode("top")
    window.panels_coordinator.set_active_panel(first_panel.panel_id)

    assert first_panel.tabs.tabPosition() == QTabWidget.TabPosition.North
    assert second_panel.tabs.tabPosition() == QTabWidget.TabPosition.North

    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    assert str(dialog.default_tab_position_combo.currentData()) == "top"
    dialog.set_combo_value(dialog.default_tab_position_combo, "right_horizontal")
    qtbot.waitUntil(
        lambda: first_panel.tabs.tabPosition() == QTabWidget.TabPosition.East
    )
    qtbot.waitUntil(
        lambda: bool(first_panel.tabs.tabBar().property("right_horizontal_mode"))
        is True
    )
    assert second_panel.tabs.tabPosition() == QTabWidget.TabPosition.North
    assert (
        bool(second_panel.tabs.tabBar().property("right_horizontal_mode")) is False
    )

    dialog._apply_and_commit()
    persisted = isolated_settings.ui_preferences()
    assert persisted.default_tab_position == "right_horizontal"


def test_settings_dialog_removes_central_extended_paths_row(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-extended-paths-layout",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    assert "backend_extended_paths" not in dialog._rows_by_key
    backend_commands_item = dialog._subsection_tree_items["operations/backend_commands"]
    dialog._section_tree.setCurrentItem(backend_commands_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is backend_commands_item)
    assert dialog.use_extended_paths_teracopy_checkbox.isVisible() is True
    assert dialog.use_extended_paths_robocopy_checkbox.isVisible() is False
    backend_args_item = dialog._subsection_tree_items["operations/backend_args"]
    dialog._section_tree.setCurrentItem(backend_args_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is backend_args_item)
    assert dialog.use_extended_paths_robocopy_checkbox.isVisible() is True


def test_settings_dialog_backend_test_uses_unsaved_values(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager, monkeypatch
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-backend-test-unsaved",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    captured: dict[str, object] = {}

    def _fake_execute(request, *, wait, preferences, artifacts):
        captured["request"] = request
        captured["wait"] = wait
        captured["preferences"] = preferences
        captured["artifacts"] = artifacts
        return OperationResult(status="succeeded", message="ok", processed_count=2)

    monkeypatch.setattr(
        "many_panelz_explorer.dialogs.settings.backend_actions.execute_operation_request",
        _fake_execute,
    )
    monkeypatch.setattr(
        "many_panelz_explorer.dialogs.settings.backend_actions.QMessageBox.information",
        lambda *_args: captured.setdefault("info", True),
    )

    unsaved_path = r"C:\tools\teracopy-custom.exe"
    dialog.teracopy_executable_edit.setText(unsaved_path)
    dialog.teracopy_test_btn.click()

    request = captured["request"]
    preferences = captured["preferences"]
    assert request.backend_id == "teracopy"
    assert request.kind == "copy"
    assert captured["wait"] is True
    assert preferences.teracopy_executable == unsaved_path
    assert captured["info"] is True


def test_settings_dialog_browse_normalizes_windows_executable_paths(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager, monkeypatch
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-backend-browse-normalize",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    monkeypatch.setattr(
        "many_panelz_explorer.dialogs.settings.backend_actions.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (
            "C:/bin/roadkil/UnstopCpy_5_2_Win2K_UP.exe",
            "Executable Files (*.exe *.cmd *.bat)",
        ),
    )

    from many_panelz_explorer.dialogs.settings import backend_actions

    backend_actions.browse_executable(dialog, dialog.unstoppable_executable_edit)

    assert (
        dialog.unstoppable_executable_edit.text()
        == r"C:\bin\roadkil\UnstopCpy_5_2_Win2K_UP.exe"
    )

    dialog._apply_and_commit()
    persisted = isolated_settings.ui_preferences()
    assert (
        persisted.unstoppable_executable == r"C:\bin\roadkil\UnstopCpy_5_2_Win2K_UP.exe"
    )


def test_backend_create_test_paths_writes_runtime_txt_with_crlf_and_no_bom(
    tmp_path: Path,
) -> None:
    from many_panelz_explorer.dialogs.settings import backend_actions

    sources, target_dir = backend_actions.create_test_paths(tmp_path, kind="copy")

    sample_file = next(path for path in sources if path.name == "sample-file.txt")
    nested_file = tmp_path / "source" / "sample-dir" / "nested.txt"
    assert target_dir == tmp_path / "target"

    for file_path, expected_text in (
        (sample_file, f"many-panelz test{linesep}"),
        (nested_file, f"nested{linesep}"),
    ):
        raw = file_path.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf") is False
        assert raw.decode("utf-8") == expected_text


def test_settings_dialog_rich_backend_controls_update_preview_and_persist(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-rich-backend-preview",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    backend_args_item = dialog._subsection_tree_items["operations/backend_args"]
    dialog._section_tree.setCurrentItem(backend_args_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is backend_args_item)
    dialog.robocopy_struct_retry_spin.setValue(5)
    dialog.robocopy_struct_wait_spin.setValue(7)
    dialog.robocopy_struct_quiet_checkbox.setChecked(True)
    dialog.unstoppable_struct_power_down_checkbox.setChecked(True)
    qtbot.waitUntil(lambda: "/R:5" in dialog.robocopy_preview_label.text())
    assert "/W:7" in dialog.robocopy_preview_label.text()
    assert "/NFL" in dialog.robocopy_preview_label.text()
    assert "{job_file}" in dialog.unstoppable_preview_label.text()
    assert "{sources}" not in dialog.unstoppable_preview_label.text()
    assert "{target}" not in dialog.unstoppable_preview_label.text()

    dialog._apply_and_commit()
    persisted = isolated_settings.ui_preferences()
    assert persisted.robocopy_structured_options.retry_count == 5
    assert persisted.robocopy_structured_options.wait_seconds == 7
    assert persisted.robocopy_structured_options.suppress_logs is True
    assert persisted.unstoppable_structured_options.power_down_when_done is True


def test_settings_dialog_removes_legacy_raw_backend_controls(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerSettingsStub(isolated_settings)
    window = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-no-legacy-raw-fields",
        roots_provider=roots_provider,
    )
    dialog = SettingsDialog(controller=controller, parent=window)
    qtbot.addWidget(dialog)
    dialog.show()

    backend_commands_item = dialog._subsection_tree_items["operations/backend_commands"]
    dialog._section_tree.setCurrentItem(backend_commands_item)
    qtbot.waitUntil(lambda: dialog._section_tree.currentItem() is backend_commands_item)
    assert hasattr(dialog, "teracopy_use_raw_override_checkbox") is False
    assert hasattr(dialog, "teracopy_args_edit") is False
    assert hasattr(dialog, "robocopy_copy_args_edit") is False
    assert hasattr(dialog, "robocopy_move_args_edit") is False
    assert hasattr(dialog, "unstoppable_args_edit") is False
    assert hasattr(dialog, "generic_copymove_args_edit") is False
