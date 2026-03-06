from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QSettings, QStandardPaths


class SettingsManager:
    """Thin wrapper around QSettings using INI storage."""

    NEW_CONTEXT_MODE_KEY = "defaults/new_context_mode"
    SHOW_HIDDEN_DEFAULT_KEY = "view/show_hidden_default"
    SHOW_ROOT_DROPDOWN_KEY = "view/show_root_dropdown"
    SESSION_WINDOWS_KEY = "session/windows"
    SAVED_VIEWS_KEY = "views/saved"

    def __init__(self, settings_path: Path | None = None) -> None:
        if settings_path is None:
            config_dir = Path(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.AppConfigLocation
                )
            )
            if not config_dir.exists():
                config_dir.mkdir(parents=True, exist_ok=True)
            settings_path = config_dir / "settings.ini"

        self.settings_path = Path(settings_path)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.qsettings = QSettings(str(self.settings_path), QSettings.Format.IniFormat)

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
        return str(self.value(self.NEW_CONTEXT_MODE_KEY, "clone_active_path"))

    @new_context_mode.setter
    def new_context_mode(self, mode: str) -> None:
        self.set_value(self.NEW_CONTEXT_MODE_KEY, mode)

    @property
    def show_hidden_default(self) -> bool:
        value = self.value(self.SHOW_HIDDEN_DEFAULT_KEY, True)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @show_hidden_default.setter
    def show_hidden_default(self, enabled: bool) -> None:
        self.set_value(self.SHOW_HIDDEN_DEFAULT_KEY, bool(enabled))

    @property
    def show_root_dropdown(self) -> bool:
        value = self.value(self.SHOW_ROOT_DROPDOWN_KEY, False)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @show_root_dropdown.setter
    def show_root_dropdown(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ROOT_DROPDOWN_KEY, bool(enabled))

    def window_key(self, window_id: str, suffix: str) -> str:
        return f"window/{window_id}/{suffix}"

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
