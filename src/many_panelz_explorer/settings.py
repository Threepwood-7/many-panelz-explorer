from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from threep_commons.qsettings_store import create_qsettings

from .constants import APP_IDENTITY


@dataclass(frozen=True)
class UiPreferences:
    new_context_mode: str
    show_hidden_default: bool
    show_root_dropdown: bool
    column_width_auto_align_mode: str
    show_refresh_button: bool
    show_root_buttons: bool
    show_address_bar: bool
    show_navigation_buttons: bool
    app_font_family: str
    app_font_size_pt: int
    file_list_use_app_font: bool
    file_list_font_family: str
    file_list_font_size_pt: int
    navigation_use_app_font: bool
    navigation_font_family: str
    navigation_font_size_pt: int
    active_panel_tint_color_hex: str
    active_panel_tint_intensity_percent: int
    target_panel_tint_color_hex: str
    target_panel_tint_intensity_percent: int


class SettingsManager:
    """Thin wrapper around QSettings using INI storage."""

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
    _ALLOWED_NEW_CONTEXT_MODES = {"clone_active_path", "home", "cwd"}
    _ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES = {
        "all_panels_tabs",
        "current_panel_tabs",
        "none",
    }
    _HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def __init__(self) -> None:
        self.qsettings = create_qsettings(APP_IDENTITY)
        self.qsettings.sync()
        self.settings_path = Path(str(self.qsettings.fileName() or ""))

    def sync(self) -> None:
        self.qsettings.sync()

    def value(self, key: str, default: Any = None) -> Any:
        return self.qsettings.value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self.qsettings.setValue(key, value)

    def remove(self, key: str) -> None:
        self.qsettings.remove(key)

    def set_json(self, key: str, value: Any) -> None:
        self.qsettings.setValue(key, json.dumps(value))

    def get_json(self, key: str, default: Any) -> Any:
        raw = self.qsettings.value(key)
        if raw is None:
            return default
        if isinstance(raw, dict):
            return dict(cast("dict[str, Any]", raw))
        if isinstance(raw, list):
            return list(cast("list[Any]", raw))
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError:
            return default

    @property
    def new_context_mode(self) -> str:
        value = str(self.value(self.NEW_CONTEXT_MODE_KEY, "clone_active_path"))
        mode = value.strip().lower()
        if mode not in self._ALLOWED_NEW_CONTEXT_MODES:
            return "clone_active_path"
        return mode

    @new_context_mode.setter
    def new_context_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        if normalized not in self._ALLOWED_NEW_CONTEXT_MODES:
            normalized = "clone_active_path"
        self.set_value(self.NEW_CONTEXT_MODE_KEY, normalized)

    @property
    def show_hidden_default(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_HIDDEN_DEFAULT_KEY, True))

    @show_hidden_default.setter
    def show_hidden_default(self, enabled: bool) -> None:
        self.set_value(self.SHOW_HIDDEN_DEFAULT_KEY, bool(enabled))

    @property
    def show_root_dropdown(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_ROOT_DROPDOWN_KEY, False))

    @show_root_dropdown.setter
    def show_root_dropdown(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ROOT_DROPDOWN_KEY, bool(enabled))

    @property
    def column_width_auto_align_mode(self) -> str:
        value = str(
            self.value(
                self.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY,
                self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE,
            )
        )
        mode = value.strip().lower()
        if mode not in self._ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES:
            return self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        return mode

    @column_width_auto_align_mode.setter
    def column_width_auto_align_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        if normalized not in self._ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES:
            normalized = self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        self.set_value(self.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY, normalized)

    @property
    def show_refresh_button(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_REFRESH_BUTTON_KEY, True))

    @show_refresh_button.setter
    def show_refresh_button(self, enabled: bool) -> None:
        self.set_value(self.SHOW_REFRESH_BUTTON_KEY, bool(enabled))

    @property
    def show_root_buttons(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_ROOT_BUTTONS_KEY, True))

    @show_root_buttons.setter
    def show_root_buttons(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ROOT_BUTTONS_KEY, bool(enabled))

    @property
    def show_address_bar(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_ADDRESS_BAR_KEY, True))

    @show_address_bar.setter
    def show_address_bar(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ADDRESS_BAR_KEY, bool(enabled))

    @property
    def show_navigation_buttons(self) -> bool:
        return self._normalize_bool(
            self.value(self.SHOW_NAVIGATION_BUTTONS_KEY, True)
        )

    @show_navigation_buttons.setter
    def show_navigation_buttons(self, enabled: bool) -> None:
        self.set_value(self.SHOW_NAVIGATION_BUTTONS_KEY, bool(enabled))

    @property
    def app_font_family(self) -> str:
        return self._normalize_font_family(
            self.value(self.APP_FONT_FAMILY_KEY, self.DEFAULT_APP_FONT_FAMILY)
        )

    @app_font_family.setter
    def app_font_family(self, family: str) -> None:
        self.set_value(self.APP_FONT_FAMILY_KEY, self._normalize_font_family(family))

    @property
    def app_font_size_pt(self) -> int:
        return self._normalize_font_size(
            self.value(self.APP_FONT_SIZE_PT_KEY, self.DEFAULT_APP_FONT_SIZE_PT),
            fallback=self.DEFAULT_APP_FONT_SIZE_PT,
            allow_zero=True,
        )

    @app_font_size_pt.setter
    def app_font_size_pt(self, size_pt: int) -> None:
        self.set_value(
            self.APP_FONT_SIZE_PT_KEY,
            self._normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_APP_FONT_SIZE_PT,
                allow_zero=True,
            ),
        )

    @property
    def file_list_use_app_font(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.FILE_LIST_USE_APP_FONT_KEY,
                self.DEFAULT_FILE_LIST_USE_APP_FONT,
            )
        )

    @file_list_use_app_font.setter
    def file_list_use_app_font(self, enabled: bool) -> None:
        self.set_value(self.FILE_LIST_USE_APP_FONT_KEY, bool(enabled))

    @property
    def file_list_font_family(self) -> str:
        return self._normalize_font_family(
            self.value(
                self.FILE_LIST_FONT_FAMILY_KEY,
                self.DEFAULT_FILE_LIST_FONT_FAMILY,
            )
        )

    @file_list_font_family.setter
    def file_list_font_family(self, family: str) -> None:
        self.set_value(
            self.FILE_LIST_FONT_FAMILY_KEY,
            self._normalize_font_family(family),
        )

    @property
    def file_list_font_size_pt(self) -> int:
        return self._normalize_font_size(
            self.value(
                self.FILE_LIST_FONT_SIZE_PT_KEY,
                self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
        )

    @file_list_font_size_pt.setter
    def file_list_font_size_pt(self, size_pt: int) -> None:
        self.set_value(
            self.FILE_LIST_FONT_SIZE_PT_KEY,
            self._normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
        )

    @property
    def navigation_use_app_font(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.NAVIGATION_USE_APP_FONT_KEY,
                self.DEFAULT_NAVIGATION_USE_APP_FONT,
            )
        )

    @navigation_use_app_font.setter
    def navigation_use_app_font(self, enabled: bool) -> None:
        self.set_value(self.NAVIGATION_USE_APP_FONT_KEY, bool(enabled))

    @property
    def navigation_font_family(self) -> str:
        return self._normalize_font_family(
            self.value(
                self.NAVIGATION_FONT_FAMILY_KEY,
                self.DEFAULT_NAVIGATION_FONT_FAMILY,
            )
        )

    @navigation_font_family.setter
    def navigation_font_family(self, family: str) -> None:
        self.set_value(
            self.NAVIGATION_FONT_FAMILY_KEY,
            self._normalize_font_family(family),
        )

    @property
    def navigation_font_size_pt(self) -> int:
        return self._normalize_font_size(
            self.value(
                self.NAVIGATION_FONT_SIZE_PT_KEY,
                self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
        )

    @navigation_font_size_pt.setter
    def navigation_font_size_pt(self, size_pt: int) -> None:
        self.set_value(
            self.NAVIGATION_FONT_SIZE_PT_KEY,
            self._normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
        )

    @property
    def active_panel_tint_color_hex(self) -> str:
        return self._normalize_color_hex(
            self.value(
                self.ACTIVE_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
        )

    @active_panel_tint_color_hex.setter
    def active_panel_tint_color_hex(self, color_hex: str) -> None:
        self.set_value(
            self.ACTIVE_PANEL_TINT_COLOR_KEY,
            self._normalize_color_hex(
                color_hex, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def active_panel_tint_intensity_percent(self) -> int:
        return self._normalize_percent(
            self.value(
                self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
        )

    @active_panel_tint_intensity_percent.setter
    def active_panel_tint_intensity_percent(self, percent: int) -> None:
        self.set_value(
            self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
            self._normalize_percent(
                percent, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT
            ),
        )

    @property
    def target_panel_tint_color_hex(self) -> str:
        return self._normalize_color_hex(
            self.value(
                self.TARGET_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
        )

    @target_panel_tint_color_hex.setter
    def target_panel_tint_color_hex(self, color_hex: str) -> None:
        self.set_value(
            self.TARGET_PANEL_TINT_COLOR_KEY,
            self._normalize_color_hex(
                color_hex, fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def target_panel_tint_intensity_percent(self) -> int:
        return self._normalize_percent(
            self.value(
                self.TARGET_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
        )

    @target_panel_tint_intensity_percent.setter
    def target_panel_tint_intensity_percent(self, percent: int) -> None:
        self.set_value(
            self.TARGET_PANEL_TINT_INTENSITY_KEY,
            self._normalize_percent(
                percent, fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT
            ),
        )

    def ui_preferences(self) -> UiPreferences:
        return UiPreferences(
            new_context_mode=self.new_context_mode,
            show_hidden_default=self.show_hidden_default,
            show_root_dropdown=self.show_root_dropdown,
            column_width_auto_align_mode=self.column_width_auto_align_mode,
            show_refresh_button=self.show_refresh_button,
            show_root_buttons=self.show_root_buttons,
            show_address_bar=self.show_address_bar,
            show_navigation_buttons=self.show_navigation_buttons,
            app_font_family=self.app_font_family,
            app_font_size_pt=self.app_font_size_pt,
            file_list_use_app_font=self.file_list_use_app_font,
            file_list_font_family=self.file_list_font_family,
            file_list_font_size_pt=self.file_list_font_size_pt,
            navigation_use_app_font=self.navigation_use_app_font,
            navigation_font_family=self.navigation_font_family,
            navigation_font_size_pt=self.navigation_font_size_pt,
            active_panel_tint_color_hex=self.active_panel_tint_color_hex,
            active_panel_tint_intensity_percent=self.active_panel_tint_intensity_percent,
            target_panel_tint_color_hex=self.target_panel_tint_color_hex,
            target_panel_tint_intensity_percent=self.target_panel_tint_intensity_percent,
        )

    def set_ui_preferences(self, preferences: UiPreferences) -> None:
        self.new_context_mode = preferences.new_context_mode
        self.show_hidden_default = preferences.show_hidden_default
        self.show_root_dropdown = preferences.show_root_dropdown
        self.column_width_auto_align_mode = preferences.column_width_auto_align_mode
        self.show_refresh_button = preferences.show_refresh_button
        self.show_root_buttons = preferences.show_root_buttons
        self.show_address_bar = preferences.show_address_bar
        self.show_navigation_buttons = preferences.show_navigation_buttons
        self.app_font_family = preferences.app_font_family
        self.app_font_size_pt = preferences.app_font_size_pt
        self.file_list_use_app_font = preferences.file_list_use_app_font
        self.file_list_font_family = preferences.file_list_font_family
        self.file_list_font_size_pt = preferences.file_list_font_size_pt
        self.navigation_use_app_font = preferences.navigation_use_app_font
        self.navigation_font_family = preferences.navigation_font_family
        self.navigation_font_size_pt = preferences.navigation_font_size_pt
        self.active_panel_tint_color_hex = preferences.active_panel_tint_color_hex
        self.active_panel_tint_intensity_percent = (
            preferences.active_panel_tint_intensity_percent
        )
        self.target_panel_tint_color_hex = preferences.target_panel_tint_color_hex
        self.target_panel_tint_intensity_percent = (
            preferences.target_panel_tint_intensity_percent
        )

    def window_key(self, window_id: str, suffix: str) -> str:
        return f"ui/windows/{window_id}/{suffix}"

    def session_window_ids(self) -> list[str]:
        data = self.get_json(self.SESSION_WINDOWS_KEY, [])
        if not isinstance(data, list):
            return []
        return [str(item) for item in cast("list[Any]", data)]

    def set_session_window_ids(self, window_ids: list[str]) -> None:
        self.set_json(self.SESSION_WINDOWS_KEY, window_ids)

    def _saved_views(self) -> dict[str, dict[str, Any]]:
        data = self.get_json(self.SAVED_VIEWS_KEY, {})
        if not isinstance(data, dict):
            return {}
        views: dict[str, dict[str, Any]] = {}
        for key, value in cast("dict[str, Any]", data).items():
            if isinstance(value, dict):
                views[str(key)] = dict(cast("dict[str, Any]", value))
        return views

    def list_saved_views(self) -> list[str]:
        return sorted(self._saved_views().keys(), key=str.casefold)

    def get_saved_view(self, name: str) -> dict[str, Any] | None:
        return self._saved_views().get(name)

    def set_saved_view(self, name: str, payload: dict[str, Any]) -> None:
        views = self._saved_views()
        views[name] = payload
        self.set_json(self.SAVED_VIEWS_KEY, views)

    def _normalize_percent(self, raw: Any, *, fallback: int) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return int(fallback)
        if value < 0:
            return 0
        if value > 100:
            return 100
        return value

    def _normalize_bool(self, raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return bool(raw)

    def _normalize_font_family(self, raw: Any) -> str:
        return str(raw or "").strip()

    def _normalize_font_size(
        self,
        raw: Any,
        *,
        fallback: int,
        allow_zero: bool = False,
    ) -> int:
        try:
            size = int(raw)
        except (TypeError, ValueError):
            return int(fallback)
        if allow_zero and size <= 0:
            return 0
        if size < 6:
            return 6
        if size > 32:
            return 32
        return size

    def _normalize_color_hex(self, raw: Any, *, fallback: str) -> str:
        text = str(raw).strip()
        if not text:
            return fallback
        if not text.startswith("#"):
            text = f"#{text}"
        if self._HEX_COLOR_RE.fullmatch(text) is None:
            return fallback
        return text.upper()
