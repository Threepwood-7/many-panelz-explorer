"""Appearance settings for the UI domain."""

from __future__ import annotations

from threep_commons.settings import SettingsDomainBase

from . import normalize
from .registry import SettingsRegistry


class UiAppearanceSettingsMixin(SettingsDomainBase, SettingsRegistry):
    """Persist fonts and panel tint appearance preferences."""

    @property
    def app_font_family(self) -> str:
        return normalize.normalize_font_family(
            self._storage.value(self.APP_FONT_FAMILY_KEY, self.DEFAULT_APP_FONT_FAMILY)
        )

    @app_font_family.setter
    def app_font_family(self, family: str) -> None:
        self._storage.set_value(
            self.APP_FONT_FAMILY_KEY, normalize.normalize_font_family(family)
        )

    @property
    def app_font_size_pt(self) -> int:
        return normalize.normalize_font_size(
            self._storage.value(
                self.APP_FONT_SIZE_PT_KEY, self.DEFAULT_APP_FONT_SIZE_PT
            ),
            fallback=self.DEFAULT_APP_FONT_SIZE_PT,
            allow_zero=True,
        )

    @app_font_size_pt.setter
    def app_font_size_pt(self, size_pt: int) -> None:
        self._storage.set_value(
            self.APP_FONT_SIZE_PT_KEY,
            normalize.normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_APP_FONT_SIZE_PT,
                allow_zero=True,
            ),
        )

    @property
    def file_list_use_app_font(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.FILE_LIST_USE_APP_FONT_KEY,
                self.DEFAULT_FILE_LIST_USE_APP_FONT,
            )
        )

    @file_list_use_app_font.setter
    def file_list_use_app_font(self, enabled: bool) -> None:
        self._storage.set_value(self.FILE_LIST_USE_APP_FONT_KEY, bool(enabled))

    @property
    def file_list_font_family(self) -> str:
        return normalize.normalize_font_family(
            self._storage.value(
                self.FILE_LIST_FONT_FAMILY_KEY,
                self.DEFAULT_FILE_LIST_FONT_FAMILY,
            )
        )

    @file_list_font_family.setter
    def file_list_font_family(self, family: str) -> None:
        self._storage.set_value(
            self.FILE_LIST_FONT_FAMILY_KEY,
            normalize.normalize_font_family(family),
        )

    @property
    def file_list_font_size_pt(self) -> int:
        return normalize.normalize_font_size(
            self._storage.value(
                self.FILE_LIST_FONT_SIZE_PT_KEY,
                self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
        )

    @file_list_font_size_pt.setter
    def file_list_font_size_pt(self, size_pt: int) -> None:
        self._storage.set_value(
            self.FILE_LIST_FONT_SIZE_PT_KEY,
            normalize.normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
        )

    @property
    def navigation_use_app_font(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.NAVIGATION_USE_APP_FONT_KEY,
                self.DEFAULT_NAVIGATION_USE_APP_FONT,
            )
        )

    @navigation_use_app_font.setter
    def navigation_use_app_font(self, enabled: bool) -> None:
        self._storage.set_value(self.NAVIGATION_USE_APP_FONT_KEY, bool(enabled))

    @property
    def navigation_font_family(self) -> str:
        return normalize.normalize_font_family(
            self._storage.value(
                self.NAVIGATION_FONT_FAMILY_KEY,
                self.DEFAULT_NAVIGATION_FONT_FAMILY,
            )
        )

    @navigation_font_family.setter
    def navigation_font_family(self, family: str) -> None:
        self._storage.set_value(
            self.NAVIGATION_FONT_FAMILY_KEY,
            normalize.normalize_font_family(family),
        )

    @property
    def navigation_font_size_pt(self) -> int:
        return normalize.normalize_font_size(
            self._storage.value(
                self.NAVIGATION_FONT_SIZE_PT_KEY,
                self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
        )

    @navigation_font_size_pt.setter
    def navigation_font_size_pt(self, size_pt: int) -> None:
        self._storage.set_value(
            self.NAVIGATION_FONT_SIZE_PT_KEY,
            normalize.normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
        )

    @property
    def active_panel_tint_color_hex(self) -> str:
        return normalize.normalize_color_hex(
            self._storage.value(
                self.ACTIVE_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
        )

    @active_panel_tint_color_hex.setter
    def active_panel_tint_color_hex(self, color_hex: str) -> None:
        self._storage.set_value(
            self.ACTIVE_PANEL_TINT_COLOR_KEY,
            normalize.normalize_color_hex(
                color_hex, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def active_panel_tint_intensity_percent(self) -> int:
        return normalize.normalize_percent(
            self._storage.value(
                self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
        )

    @active_panel_tint_intensity_percent.setter
    def active_panel_tint_intensity_percent(self, percent: int) -> None:
        self._storage.set_value(
            self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
            normalize.normalize_percent(
                percent, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT
            ),
        )

    @property
    def target_panel_tint_color_hex(self) -> str:
        return normalize.normalize_color_hex(
            self._storage.value(
                self.TARGET_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
        )

    @target_panel_tint_color_hex.setter
    def target_panel_tint_color_hex(self, color_hex: str) -> None:
        self._storage.set_value(
            self.TARGET_PANEL_TINT_COLOR_KEY,
            normalize.normalize_color_hex(
                color_hex, fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def target_panel_tint_intensity_percent(self) -> int:
        return normalize.normalize_percent(
            self._storage.value(
                self.TARGET_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
        )

    @target_panel_tint_intensity_percent.setter
    def target_panel_tint_intensity_percent(self, percent: int) -> None:
        self._storage.set_value(
            self.TARGET_PANEL_TINT_INTENSITY_KEY,
            normalize.normalize_percent(
                percent, fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT
            ),
        )
