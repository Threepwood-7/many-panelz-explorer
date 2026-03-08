import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer.dialogs.settings_dialog import SettingsDialog
from many_panelz_explorer.settings import SettingsManager, UiPreferences
from many_panelz_explorer.window import ExplorerWindow


class _ControllerSettingsStub:
    def __init__(self, settings: SettingsManager) -> None:
        self.settings = settings
        self.windows: list[ExplorerWindow] = []
        self.preview_calls: list[UiPreferences] = []

    def close_window(self, _window: ExplorerWindow) -> None:
        return

    def current_ui_preferences(self) -> UiPreferences:
        return self.settings.ui_preferences()

    def preview_ui_preferences(self, preferences: UiPreferences) -> None:
        self.preview_calls.append(preferences)
        for window in list(self.windows):
            window.apply_ui_preferences(preferences)

    def apply_ui_preferences(self, preferences: UiPreferences) -> None:
        self.settings.set_ui_preferences(preferences)
        self.settings.sync()
        self.preview_ui_preferences(preferences)


def _test_roots_provider(tmp_path: Path):
    root = tmp_path / "roots"
    root.mkdir(parents=True, exist_ok=True)
    return lambda _current: [root]


def _tracked_keys() -> list[str]:
    return [
        SettingsManager.NEW_CONTEXT_MODE_KEY,
        SettingsManager.SHOW_HIDDEN_DEFAULT_KEY,
        SettingsManager.SHOW_ROOT_DROPDOWN_KEY,
        SettingsManager.SHOW_REFRESH_BUTTON_KEY,
        SettingsManager.SHOW_ROOT_BUTTONS_KEY,
        SettingsManager.SHOW_ADDRESS_BAR_KEY,
        SettingsManager.SHOW_NAVIGATION_BUTTONS_KEY,
        SettingsManager.ACTIVE_PANEL_TINT_COLOR_KEY,
        SettingsManager.ACTIVE_PANEL_TINT_INTENSITY_KEY,
        SettingsManager.TARGET_PANEL_TINT_COLOR_KEY,
        SettingsManager.TARGET_PANEL_TINT_INTENSITY_KEY,
    ]


@pytest.fixture
def isolated_settings() -> SettingsManager:
    settings = SettingsManager()
    keys = _tracked_keys()
    snapshot = {key: settings.value(key, None) for key in keys}
    try:
        yield settings
    finally:
        for key, value in snapshot.items():
            if value is None:
                settings.remove(key)
            else:
                settings.set_value(key, value)
        settings.sync()


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


def test_settings_action_in_view_menu_and_shortcut_trigger(qtbot, tmp_path: Path, isolated_settings: SettingsManager) -> None:
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
    window._settings_action.triggered.disconnect()
    window._settings_action.triggered.connect(lambda: triggered.append("fired"))

    window._settings_action.trigger()
    assert triggered == ["fired"]
    assert window._settings_action.shortcut().toString() == "Ctrl+,"


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


def test_settings_live_preview_all_windows_and_cancel_revert(
    qtbot, tmp_path: Path, isolated_settings: SettingsManager
) -> None:
    isolated_settings.set_ui_preferences(
        UiPreferences(
            new_context_mode="clone_active_path",
            show_hidden_default=True,
            show_root_dropdown=False,
            show_refresh_button=True,
            show_root_buttons=True,
            show_address_bar=True,
            show_navigation_buttons=True,
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

    first_active = first.active_panel()
    second_active = second.active_panel()
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
    qtbot.waitUntil(lambda: first_active.root_combo.isVisible() is True)
    assert second_active.root_combo.isVisible() is True
    assert first_active.refresh_btn.isVisible() is False
    assert second_active.refresh_btn.isVisible() is False

    dialog.reject()
    qtbot.waitUntil(lambda: "rgba(168, 182, 196, 61)" in first_active.styleSheet())
    assert "rgba(168, 182, 196, 61)" in second_active.styleSheet()
    assert first_active.root_combo.isVisible() is False
    assert second_active.root_combo.isVisible() is False
    assert first_active.refresh_btn.isVisible() is True
    assert second_active.refresh_btn.isVisible() is True


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
    dialog.show_refresh_button_checkbox.setChecked(False)
    dialog.show_root_buttons_checkbox.setChecked(False)
    dialog.show_address_bar_checkbox.setChecked(False)
    dialog.show_navigation_buttons_checkbox.setChecked(False)
    dialog._apply_and_commit()

    persisted = isolated_settings.ui_preferences()
    assert persisted.active_panel_tint_intensity_percent == 50
    assert persisted.target_panel_tint_intensity_percent == 40
    assert persisted.show_hidden_default is False
    assert persisted.show_root_dropdown is True
    assert persisted.show_refresh_button is False
    assert persisted.show_root_buttons is False
    assert persisted.show_address_bar is False
    assert persisted.show_navigation_buttons is False

    reopened = _new_window(
        qtbot,
        controller=controller,
        settings=isolated_settings,
        window_id="settings-apply-reopened",
        roots_provider=roots_provider,
    )
    reopened_panel = reopened.active_panel()
    assert reopened_panel is not None
    assert reopened._show_hidden_action.isChecked() is False
    assert reopened_panel.root_combo.isVisible() is True
    assert reopened_panel.refresh_btn.isVisible() is False
    assert reopened_panel.root_buttons_host.isVisible() is False
    assert reopened_panel.address_edit.isVisible() is False
    assert reopened_panel.back_btn.isVisible() is False
    assert reopened_panel.forward_btn.isVisible() is False
    assert reopened_panel.up_btn.isVisible() is False
    assert reopened_panel.root_btn.isVisible() is False
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
    qtbot.waitUntil(lambda: first._show_hidden_action.isChecked() is False)
    assert second._show_hidden_action.isChecked() is False

    first_panel = first.active_panel()
    second_panel = second.active_panel()
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
