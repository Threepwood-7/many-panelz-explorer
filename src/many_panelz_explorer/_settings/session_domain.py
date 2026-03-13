"""Session-scoped settings domain."""

from __future__ import annotations

from typing import Any, cast

from threep_commons.settings import SettingsDomainBase

from . import normalize
from .registry import SettingsRegistry


class SessionSettingsDomain(SettingsDomainBase, SettingsRegistry):
    """Read and persist transient session-scoped UI state."""

    def window_key(self, window_id: str, suffix: str) -> str:
        return f"ui/windows/{window_id}/{suffix}"

    def session_window_ids(self) -> list[str]:
        data = self._storage.get_json(self.SESSION_WINDOWS_KEY, [])
        if not isinstance(data, list):
            return []
        return [str(item) for item in cast("list[Any]", data)]

    def set_session_window_ids(self, window_ids: list[str]) -> None:
        self._storage.set_json(self.SESSION_WINDOWS_KEY, window_ids)

    @property
    def settings_dialog_last_section(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.SETTINGS_DIALOG_LAST_SECTION_KEY,
                self.DEFAULT_SETTINGS_DIALOG_LAST_SECTION,
            ),
            fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SECTION,
        )

    @settings_dialog_last_section.setter
    def settings_dialog_last_section(self, value: str) -> None:
        self._storage.set_value(
            self.SETTINGS_DIALOG_LAST_SECTION_KEY,
            normalize.normalize_text(
                value,
                fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SECTION,
            ),
        )

    @property
    def settings_dialog_last_subsection(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.SETTINGS_DIALOG_LAST_SUBSECTION_KEY,
                self.DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION,
            ),
            fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION,
        )

    @settings_dialog_last_subsection.setter
    def settings_dialog_last_subsection(self, value: str) -> None:
        self._storage.set_value(
            self.SETTINGS_DIALOG_LAST_SUBSECTION_KEY,
            normalize.normalize_text(
                value,
                fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION,
            ),
        )

    def saved_views(self) -> dict[str, dict[str, Any]]:
        data = self._storage.get_json(self.SAVED_VIEWS_KEY, {})
        if not isinstance(data, dict):
            return {}
        views: dict[str, dict[str, Any]] = {}
        for key, value in cast("dict[str, Any]", data).items():
            if isinstance(value, dict):
                views[str(key)] = dict(cast("dict[str, Any]", value))
        return views

    def list_saved_views(self) -> list[str]:
        return sorted(self.saved_views().keys(), key=str.casefold)

    def get_saved_view(self, name: str) -> dict[str, Any] | None:
        return self.saved_views().get(name)

    def set_saved_view(self, name: str, payload: dict[str, Any]) -> None:
        views = self.saved_views()
        views[name] = payload
        self._storage.set_json(self.SAVED_VIEWS_KEY, views)
