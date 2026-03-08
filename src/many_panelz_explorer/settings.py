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
    show_refresh_button: bool
    show_root_buttons: bool
    show_address_bar: bool
    show_navigation_buttons: bool
    active_panel_tint_color_hex: str
    active_panel_tint_intensity_percent: int
    target_panel_tint_color_hex: str
    target_panel_tint_intensity_percent: int


class SettingsManager:
    """Thin wrapper around QSettings using INI storage."""

    NEW_CONTEXT_MODE_KEY = "config/new_context_mode"
    SHOW_HIDDEN_DEFAULT_KEY = "ui/show_hidden_default"
    SHOW_ROOT_DROPDOWN_KEY = "ui/show_root_dropdown"
    SHOW_REFRESH_BUTTON_KEY = "ui/show_refresh_button"
    SHOW_ROOT_BUTTONS_KEY = "ui/show_root_buttons"
    SHOW_ADDRESS_BAR_KEY = "ui/show_address_bar"
    SHOW_NAVIGATION_BUTTONS_KEY = "ui/show_navigation_buttons"
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
    _ALLOWED_NEW_CONTEXT_MODES = {"clone_active_path", "home", "cwd"}
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
            show_refresh_button=self.show_refresh_button,
            show_root_buttons=self.show_root_buttons,
            show_address_bar=self.show_address_bar,
            show_navigation_buttons=self.show_navigation_buttons,
            active_panel_tint_color_hex=self.active_panel_tint_color_hex,
            active_panel_tint_intensity_percent=self.active_panel_tint_intensity_percent,
            target_panel_tint_color_hex=self.target_panel_tint_color_hex,
            target_panel_tint_intensity_percent=self.target_panel_tint_intensity_percent,
        )

    def set_ui_preferences(self, preferences: UiPreferences) -> None:
        self.new_context_mode = preferences.new_context_mode
        self.show_hidden_default = preferences.show_hidden_default
        self.show_root_dropdown = preferences.show_root_dropdown
        self.show_refresh_button = preferences.show_refresh_button
        self.show_root_buttons = preferences.show_root_buttons
        self.show_address_bar = preferences.show_address_bar
        self.show_navigation_buttons = preferences.show_navigation_buttons
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

    def _normalize_color_hex(self, raw: Any, *, fallback: str) -> str:
        text = str(raw).strip()
        if not text:
            return fallback
        if not text.startswith("#"):
            text = f"#{text}"
        if self._HEX_COLOR_RE.fullmatch(text) is None:
            return fallback
        return text.upper()
