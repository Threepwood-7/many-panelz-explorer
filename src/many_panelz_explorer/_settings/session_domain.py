"""Session-scoped settings domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from threep_commons.settings import SettingsDomainBase

from many_panelz_explorer.window_state_payloads import (
    saved_view_state,
    saved_views_payload,
    string_list_payload,
)

from . import normalize
from .registry import SettingsRegistry

if TYPE_CHECKING:
    from many_panelz_explorer.ui.window.state_types import SavedViewState


class SessionSettingsDomain(SettingsDomainBase, SettingsRegistry):
    """Read and persist transient session-scoped UI state."""

    def window_key(self, window_id: str, suffix: str) -> str:
        return f"ui/windows/{window_id}/{suffix}"

    def session_window_ids(self) -> list[str]:
        return string_list_payload(self._storage.get_json(self.SESSION_WINDOWS_KEY, []))

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

    def saved_views(self) -> dict[str, SavedViewState]:
        return saved_views_payload(self._storage.get_json(self.SAVED_VIEWS_KEY, {}))

    def list_saved_views(self) -> list[str]:
        return sorted(self.saved_views().keys(), key=str.casefold)

    def get_saved_view(self, name: str) -> SavedViewState | None:
        return self.saved_views().get(name)

    def set_saved_view(self, name: str, payload: object) -> None:
        views = self.saved_views()
        views[name] = saved_view_state(payload)
        self._storage.set_json(self.SAVED_VIEWS_KEY, views)
