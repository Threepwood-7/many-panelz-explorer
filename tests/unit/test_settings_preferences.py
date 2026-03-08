from __future__ import annotations

from many_panelz_explorer.settings import SettingsManager, UiPreferences


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
        SettingsManager.ACTIVE_PANEL_TINT_COLOR_KEY,
        SettingsManager.ACTIVE_PANEL_TINT_INTENSITY_KEY,
        SettingsManager.TARGET_PANEL_TINT_COLOR_KEY,
        SettingsManager.TARGET_PANEL_TINT_INTENSITY_KEY,
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
            active_panel_tint_color_hex="#ABCDEF",
            active_panel_tint_intensity_percent=80,
            target_panel_tint_color_hex="#123456",
            target_panel_tint_intensity_percent=33,
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
        settings.set_value(SettingsManager.ACTIVE_PANEL_TINT_COLOR_KEY, "blue")
        settings.set_value(SettingsManager.TARGET_PANEL_TINT_COLOR_KEY, "#12")
        settings.set_value(SettingsManager.ACTIVE_PANEL_TINT_INTENSITY_KEY, "oops")
        settings.set_value(SettingsManager.TARGET_PANEL_TINT_INTENSITY_KEY, "nope")

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
