"""Window preference state and derived formatter coordination."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ...byte_formatting import (
    ByteFormatPreferences,
    ByteFormatScopeConfig,
    format_bytes,
)

if TYPE_CHECKING:
    from ..._settings.models import UiPreferences
    from ...window import ExplorerWindow


class WindowPreferencesCoordinator:
    """Manage per-window UI preferences and derived presentation helpers."""

    def __init__(
        self,
        window: ExplorerWindow,
        *,
        initial_path: Path | None,
        preferences: UiPreferences,
    ) -> None:
        """Initialize coordinator state for a newly created window."""
        self.window = window
        self._initial_path = initial_path or Path.home()
        self._show_widget_map = False
        self._load_preferences(preferences)

    @property
    def show_hidden_enabled(self) -> bool:
        """Return whether hidden files should be visible."""
        return self._show_hidden

    @property
    def show_widget_map_enabled(self) -> bool:
        """Return whether widget-map overlays should be visible."""
        return self._show_widget_map

    @property
    def show_storage_overview_enabled(self) -> bool:
        """Return whether storage overview rows should be visible."""
        return self._show_storage_overview_status_row

    @property
    def initial_path(self) -> Path:
        """Return the seed path for new panels and tabs."""
        return Path(self._initial_path)

    @property
    def show_root_dropdown_enabled(self) -> bool:
        """Return whether root selectors should be visible."""
        return self._show_root_dropdown

    @property
    def show_refresh_button_enabled(self) -> bool:
        """Return whether panel refresh buttons should be visible."""
        return self._show_refresh_button

    @property
    def show_root_buttons_enabled(self) -> bool:
        """Return whether root navigation buttons should be visible."""
        return self._show_root_buttons

    @property
    def show_address_bar_enabled(self) -> bool:
        """Return whether address bars should be visible."""
        return self._show_address_bar

    @property
    def show_navigation_buttons_enabled(self) -> bool:
        """Return whether back/forward/up buttons should be visible."""
        return self._show_navigation_buttons

    @property
    def column_width_auto_align_mode(self) -> str:
        """Return the selected auto-alignment mode for file list widths."""
        return self._column_width_auto_align_mode

    @property
    def operation_queue_view_mode(self) -> str:
        """Return the configured queue presentation mode."""
        return self._operation_queue_view_mode

    @property
    def operation_shortcut_behavior(self) -> str:
        """Return the configured operation-shortcut behavior."""
        return self._operation_shortcut_behavior

    @property
    def default_copy_move_backend(self) -> str:
        """Return the configured copy and move backend."""
        return self._default_copy_move_backend

    @property
    def default_delete_backend(self) -> str:
        """Return the configured delete backend."""
        return self._default_delete_backend

    @property
    def default_operation_dispatch_mode(self) -> str:
        """Return the configured operation dispatch mode."""
        return self._default_operation_dispatch_mode

    @property
    def default_operation_conflict_policy(self) -> str:
        """Return the configured default conflict policy."""
        return self._default_operation_conflict_policy

    @property
    def status_bar_storage_label_template(self) -> str:
        """Return the active storage status label template."""
        return self._status_bar_storage_label_template

    def panel_role_visual_preferences(self) -> tuple[str, int, str, int]:
        """Return active/target panel tint preferences."""
        return (
            self._active_panel_tint_color_hex,
            self._active_panel_tint_intensity_percent,
            self._target_panel_tint_color_hex,
            self._target_panel_tint_intensity_percent,
        )

    def panel_toolbar_visibility_preferences(
        self,
    ) -> tuple[bool, bool, bool, bool, bool]:
        """Return panel toolbar visibility flags."""
        return (
            self._show_refresh_button,
            self._show_root_buttons,
            self._show_root_dropdown,
            self._show_address_bar,
            self._show_navigation_buttons,
        )

    def apply_ui_preferences(self, preferences: UiPreferences) -> None:
        """Apply updated UI preferences to the live window and its panels."""
        self._load_preferences(preferences)

        with QSignalBlocker(self.window.show_hidden_action):
            self.window.show_hidden_action.setChecked(self._show_hidden)

        file_list_font, navigation_font = self.effective_panel_fonts()
        for panel in self.window.panel_widgets.values():
            panel.set_show_hidden(self._show_hidden)
            panel.presentation_coordinator.apply_toolbar_visibility(
                show_refresh_button=self._show_refresh_button,
                show_root_buttons=self._show_root_buttons,
                show_root_dropdown=self._show_root_dropdown,
                show_address_bar=self._show_address_bar,
                show_navigation_buttons=self._show_navigation_buttons,
            )
            panel.state_coordinator.set_column_width_auto_align_mode(
                self._column_width_auto_align_mode
            )
            panel.presentation_coordinator.apply_font_preferences(
                file_list_font=file_list_font,
                navigation_font=navigation_font,
            )
            panel.presentation_coordinator.apply_size_formatters(
                file_list_size_formatter=self.format_file_list_bytes,
                properties_size_formatter=self.format_properties_bytes,
            )
            panel.presentation_coordinator.set_role_visual_preferences(
                active_color_hex=self._active_panel_tint_color_hex,
                active_intensity_percent=self._active_panel_tint_intensity_percent,
                target_color_hex=self._target_panel_tint_color_hex,
                target_intensity_percent=self._target_panel_tint_intensity_percent,
            )

        self.window.ui_composer.apply_operation_queue_visibility()
        self.window.status_coordinator.set_storage_bytes_formatter(
            self.format_status_bar_bytes
        )
        self.window.status_coordinator.set_storage_label_template(
            self._status_bar_storage_label_template
        )
        self.window.status_coordinator.set_storage_overview_enabled(
            self._show_storage_overview_status_row
        )
        self.window.update_pane_visuals()

    def effective_panel_fonts(self) -> tuple[QFont, QFont]:
        """Build the effective file-list and navigation fonts for panels."""
        app_font = QApplication.font()
        file_list_font = QFont(app_font)
        navigation_font = QFont(app_font)

        if not self._file_list_use_app_font:
            family = str(self._file_list_font_family or "").strip()
            if family:
                file_list_font.setFamily(family)
            if self._file_list_font_size_pt > 0:
                file_list_font.setPointSize(self._file_list_font_size_pt)

        if not self._navigation_use_app_font:
            family = str(self._navigation_font_family or "").strip()
            if family:
                navigation_font.setFamily(family)
            if self._navigation_font_size_pt > 0:
                navigation_font.setPointSize(self._navigation_font_size_pt)

        return file_list_font, navigation_font

    def format_file_list_bytes(self, value: int) -> str:
        """Format bytes for file-list presentation."""
        return self._format_bytes_for_scope(
            value,
            self._byte_format_preferences.file_list,
        )

    def format_status_bar_bytes(self, value: int) -> str:
        """Format bytes for status-bar presentation."""
        return self._format_bytes_for_scope(
            value,
            self._byte_format_preferences.status_bar,
        )

    def format_properties_bytes(self, value: int) -> str:
        """Format bytes for properties presentation."""
        return self._format_bytes_for_scope(
            value,
            self._byte_format_preferences.properties,
        )

    def resolve_new_context_path(self, active_path: Path | None) -> Path:
        """Resolve the seed path for a newly created panel context."""
        mode = self._new_context_mode.strip().lower()
        if mode == "home":
            return Path.home()
        if mode == "cwd":
            return Path.cwd()
        if active_path is not None:
            return Path(active_path)
        return Path.home()

    def set_show_hidden(self, enabled: bool) -> None:
        """Toggle hidden-file visibility and refresh all panels."""
        self._show_hidden = bool(enabled)
        self.window.settings.show_hidden_default = self._show_hidden
        for panel in self.window.panel_widgets.values():
            panel.set_show_hidden(self._show_hidden)

    def set_show_widget_map(self, enabled: bool) -> None:
        """Toggle widget-map overlays across all panels."""
        self._show_widget_map = bool(enabled)
        for panel in self.window.panel_widgets.values():
            panel.widget_map_coordinator.set_enabled(self._show_widget_map)

    def _load_preferences(self, preferences: UiPreferences) -> None:
        """Copy preference values into coordinator state."""
        self._new_context_mode = preferences.new_context_mode
        self._show_hidden = bool(preferences.show_hidden_default)
        self._show_root_dropdown = bool(preferences.show_root_dropdown)
        self._show_storage_overview_status_row = bool(
            preferences.show_storage_overview_status_row
        )
        self._column_width_auto_align_mode = preferences.column_width_auto_align_mode
        self._show_refresh_button = bool(preferences.show_refresh_button)
        self._show_root_buttons = bool(preferences.show_root_buttons)
        self._show_address_bar = bool(preferences.show_address_bar)
        self._show_navigation_buttons = bool(preferences.show_navigation_buttons)
        self._byte_format_preferences = self._build_byte_format_preferences(preferences)
        self._status_bar_storage_label_template = (
            preferences.status_bar_storage_label_template
        )
        self._app_font_family = preferences.app_font_family
        self._app_font_size_pt = int(preferences.app_font_size_pt)
        self._file_list_use_app_font = bool(preferences.file_list_use_app_font)
        self._file_list_font_family = preferences.file_list_font_family
        self._file_list_font_size_pt = int(preferences.file_list_font_size_pt)
        self._navigation_use_app_font = bool(preferences.navigation_use_app_font)
        self._navigation_font_family = preferences.navigation_font_family
        self._navigation_font_size_pt = int(preferences.navigation_font_size_pt)
        self._active_panel_tint_color_hex = preferences.active_panel_tint_color_hex
        self._active_panel_tint_intensity_percent = (
            preferences.active_panel_tint_intensity_percent
        )
        self._target_panel_tint_color_hex = preferences.target_panel_tint_color_hex
        self._target_panel_tint_intensity_percent = (
            preferences.target_panel_tint_intensity_percent
        )
        self._default_copy_move_backend = preferences.default_copy_move_backend
        self._default_delete_backend = preferences.default_delete_backend
        self._default_operation_dispatch_mode = (
            preferences.default_operation_dispatch_mode
        )
        self._default_operation_conflict_policy = (
            preferences.default_operation_conflict_policy
        )
        self._operation_shortcut_behavior = preferences.operation_shortcut_behavior
        self._operation_queue_view_mode = preferences.operation_queue_view_mode

    def _build_byte_format_preferences(
        self,
        preferences: UiPreferences,
    ) -> ByteFormatPreferences:
        """Build the byte-formatting configuration snapshot."""
        return ByteFormatPreferences(
            thousands_sep=preferences.byte_thousands_separator,
            decimal_sep=preferences.byte_decimal_separator,
            file_list=ByteFormatScopeConfig(
                mode=preferences.file_list_byte_format_mode,
                custom_template=preferences.file_list_byte_custom_template,
            ),
            status_bar=ByteFormatScopeConfig(
                mode=preferences.status_bar_byte_format_mode,
                custom_template=preferences.status_bar_byte_custom_template,
            ),
            properties=ByteFormatScopeConfig(
                mode=preferences.properties_byte_format_mode,
                custom_template=preferences.properties_byte_custom_template,
            ),
        )

    def _format_bytes_for_scope(
        self,
        value: int,
        scope_config: ByteFormatScopeConfig,
    ) -> str:
        """Render a byte value using the configured separators and template."""
        preferences = self._byte_format_preferences
        return format_bytes(
            value,
            scope_config,
            (preferences.thousands_sep, preferences.decimal_sep),
        )
