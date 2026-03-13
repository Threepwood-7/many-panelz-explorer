"""Byte-format settings for the UI domain."""

from __future__ import annotations

from threep_commons.settings import SettingsDomainBase

from . import normalize
from .registry import SettingsRegistry


class UiByteFormatSettingsMixin(SettingsDomainBase, SettingsRegistry):
    """Persist byte separators and per-surface byte-format preferences."""

    def _normalized_byte_separators(self) -> tuple[str, str]:
        return normalize.normalize_byte_separators(
            self._storage.value(
                self.BYTES_THOUSANDS_SEPARATOR_KEY,
                self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            ),
            self._storage.value(
                self.BYTES_DECIMAL_SEPARATOR_KEY,
                self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
            ),
            fallback_thousands=self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            fallback_decimal=self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
        )

    def set_byte_separators(self, thousands_raw: str, decimal_raw: str) -> None:
        thousands, decimal = normalize.normalize_byte_separators(
            thousands_raw,
            decimal_raw,
            fallback_thousands=self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            fallback_decimal=self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
        )
        self._storage.set_value(self.BYTES_THOUSANDS_SEPARATOR_KEY, thousands)
        self._storage.set_value(self.BYTES_DECIMAL_SEPARATOR_KEY, decimal)

    @property
    def byte_thousands_separator(self) -> str:
        thousands, _ = self._normalized_byte_separators()
        return thousands

    @byte_thousands_separator.setter
    def byte_thousands_separator(self, value: str) -> None:
        normalized = normalize.normalize_byte_separator(
            value,
            fallback=self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            allow_empty=True,
        )
        self._storage.set_value(self.BYTES_THOUSANDS_SEPARATOR_KEY, normalized)

    @property
    def byte_decimal_separator(self) -> str:
        _, decimal = self._normalized_byte_separators()
        return decimal

    @byte_decimal_separator.setter
    def byte_decimal_separator(self, value: str) -> None:
        normalized = normalize.normalize_byte_separator(
            value,
            fallback=self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
            allow_empty=False,
        )
        self._storage.set_value(self.BYTES_DECIMAL_SEPARATOR_KEY, normalized)

    @property
    def file_list_byte_format_mode(self) -> str:
        return normalize.normalize_byte_format_mode(
            self._storage.value(
                self.FILE_LIST_BYTE_FORMAT_MODE_KEY,
                self.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
            ),
            fallback=self.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
            allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
        )

    @file_list_byte_format_mode.setter
    def file_list_byte_format_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.FILE_LIST_BYTE_FORMAT_MODE_KEY,
            normalize.normalize_byte_format_mode(
                mode,
                fallback=self.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
                allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
            ),
        )

    @property
    def file_list_byte_custom_template(self) -> str:
        return normalize.normalize_byte_custom_template(
            self._storage.value(
                self.FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY,
                self.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE,
            ),
            fallback=self.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE,
        )

    @file_list_byte_custom_template.setter
    def file_list_byte_custom_template(self, value: str) -> None:
        self._storage.set_value(
            self.FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY,
            normalize.normalize_byte_custom_template(
                value,
                fallback=self.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE,
            ),
        )

    @property
    def status_bar_byte_format_mode(self) -> str:
        return normalize.normalize_byte_format_mode(
            self._storage.value(
                self.STATUS_BAR_BYTE_FORMAT_MODE_KEY,
                self.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
            ),
            fallback=self.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
            allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
        )

    @status_bar_byte_format_mode.setter
    def status_bar_byte_format_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.STATUS_BAR_BYTE_FORMAT_MODE_KEY,
            normalize.normalize_byte_format_mode(
                mode,
                fallback=self.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
                allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
            ),
        )

    @property
    def status_bar_byte_custom_template(self) -> str:
        return normalize.normalize_byte_custom_template(
            self._storage.value(
                self.STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY,
                self.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE,
            ),
            fallback=self.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE,
        )

    @status_bar_byte_custom_template.setter
    def status_bar_byte_custom_template(self, value: str) -> None:
        self._storage.set_value(
            self.STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY,
            normalize.normalize_byte_custom_template(
                value,
                fallback=self.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE,
            ),
        )

    @property
    def status_bar_storage_label_template(self) -> str:
        return normalize.normalize_status_storage_label_template(
            self._storage.value(
                self.STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY,
                self.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE,
            ),
            fallback=self.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE,
        )

    @status_bar_storage_label_template.setter
    def status_bar_storage_label_template(self, value: str) -> None:
        self._storage.set_value(
            self.STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY,
            normalize.normalize_status_storage_label_template(
                value,
                fallback=self.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE,
            ),
        )

    @property
    def properties_byte_format_mode(self) -> str:
        return normalize.normalize_byte_format_mode(
            self._storage.value(
                self.PROPERTIES_BYTE_FORMAT_MODE_KEY,
                self.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
            ),
            fallback=self.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
            allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
        )

    @properties_byte_format_mode.setter
    def properties_byte_format_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.PROPERTIES_BYTE_FORMAT_MODE_KEY,
            normalize.normalize_byte_format_mode(
                mode,
                fallback=self.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
                allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
            ),
        )

    @property
    def properties_byte_custom_template(self) -> str:
        return normalize.normalize_byte_custom_template(
            self._storage.value(
                self.PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY,
                self.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE,
            ),
            fallback=self.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE,
        )

    @properties_byte_custom_template.setter
    def properties_byte_custom_template(self, value: str) -> None:
        self._storage.set_value(
            self.PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY,
            normalize.normalize_byte_custom_template(
                value,
                fallback=self.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE,
            ),
        )
