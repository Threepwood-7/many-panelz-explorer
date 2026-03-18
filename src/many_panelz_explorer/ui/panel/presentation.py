"""Presentation and role-visual coordination for a panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QFont
from threep_commons.fs_paths import display_path_text

from ...explorer_tab import ExplorerTab

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QWidget

    from ...panel_widget import PanelWidget


class PanelPresentationCoordinator:
    """Own toolbar visibility, fonts, and panel role styling."""

    def __init__(self, panel: PanelWidget) -> None:
        self.panel = panel

    def apply_toolbar_visibility(
        self,
        *,
        show_refresh_button: bool,
        show_root_buttons: bool,
        show_root_dropdown: bool,
        show_address_bar: bool,
        show_navigation_buttons: bool,
    ) -> None:
        dropdown_changed = self.panel.show_root_dropdown != bool(show_root_dropdown)
        self.panel.show_refresh_button = bool(show_refresh_button)
        self.panel.show_root_buttons = bool(show_root_buttons)
        self.panel.show_root_dropdown = bool(show_root_dropdown)
        self.panel.show_address_bar = bool(show_address_bar)
        self.panel.show_navigation_buttons = bool(show_navigation_buttons)
        if dropdown_changed:
            self.panel.navigation_coordinator.rebuild_root_controls(
                self.panel.current_path()
            )
        self._sync_toolbar_visibility()
        self.panel.widget_map_coordinator.sync_overlay()

    def apply_tab_close_button_visibility(
        self, *, show_tab_close_buttons: bool
    ) -> None:
        """Show or hide tab close buttons for this panel."""

        self.panel.show_tab_close_buttons = bool(show_tab_close_buttons)
        self.panel.tabs.setTabsClosable(self.panel.show_tab_close_buttons)
        self.panel.widget_map_coordinator.sync_overlay()

    def apply_font_preferences(
        self, *, file_list_font: QFont, navigation_font: QFont
    ) -> None:
        self.panel.file_list_font_value = QFont(file_list_font)
        self.panel.navigation_font_value = QFont(navigation_font)
        self._apply_toolbar_font()
        self._apply_file_list_font()
        self.panel.widget_map_coordinator.sync_overlay()

    def apply_size_formatters(
        self,
        *,
        file_list_size_formatter: Callable[[int], str] | None,
        properties_size_formatter: Callable[[int], str] | None,
    ) -> None:
        self.panel.file_list_size_formatter = (
            file_list_size_formatter or self.panel.default_file_list_size_formatter
        )
        self.panel.properties_size_formatter = (
            properties_size_formatter or self.panel.default_properties_size_formatter
        )
        self._apply_size_formatters_to_tabs()

    def set_role_visual_preferences(
        self,
        *,
        active_color_hex: str,
        active_intensity_percent: int,
        target_color_hex: str,
        target_intensity_percent: int,
    ) -> None:
        active_color = QColor(str(active_color_hex))
        target_color = QColor(str(target_color_hex))
        if active_color.isValid():
            self.panel.active_role_color = active_color
        if target_color.isValid():
            self.panel.target_role_color = target_color
        self.panel.active_role_intensity_percent = self._normalize_percent(
            active_intensity_percent
        )
        self.panel.target_role_intensity_percent = self._normalize_percent(
            target_intensity_percent
        )
        self._apply_visual_role()
        self.panel.widget_map_coordinator.sync_overlay()

    def set_role_visual_state(self, *, is_active: bool, is_target: bool) -> None:
        if is_active:
            self.panel.pane_role = "active"
        elif is_target:
            self.panel.pane_role = "target"
        else:
            self.panel.pane_role = "normal"
        self._apply_visual_role()
        self.panel.widget_map_coordinator.sync_overlay()

    def sync_toolbar_for_current_tab(self) -> None:
        tab = self.panel.current_tab()
        if tab is None:
            self.panel.back_btn.setEnabled(False)
            self.panel.forward_btn.setEnabled(False)
            self.panel.up_btn.setEnabled(False)
            self.panel.root_btn.setEnabled(False)
            self.panel.refresh_btn.setEnabled(False)
            self.panel.navigation_coordinator.set_address_text_programmatically("")
            self.panel.navigation_coordinator.rebuild_root_controls(None)
            self.panel.widget_map_coordinator.sync_overlay()
            return

        self.panel.back_btn.setEnabled(tab.navigation.can_go_back)
        self.panel.forward_btn.setEnabled(tab.navigation.can_go_forward)
        self.panel.up_btn.setEnabled(True)
        self.panel.root_btn.setEnabled(True)
        self.panel.refresh_btn.setEnabled(True)
        self.panel.navigation_coordinator.set_address_text_programmatically(
            display_path_text(tab.navigation.path)
        )
        self.panel.navigation_coordinator.rebuild_root_controls(tab.navigation.path)
        if self.panel.filter_edit.isVisible():
            tab.navigation.set_inline_filter(self.panel.filter_edit.text())
        self.panel.widget_map_coordinator.sync_overlay()

    def _sync_toolbar_visibility(self) -> None:
        self.panel.refresh_btn.setVisible(self.panel.show_refresh_button)
        self.panel.root_buttons_host.setVisible(self.panel.show_root_buttons)
        self.panel.root_combo.setVisible(self.panel.show_root_dropdown)
        self.panel.address_edit.setVisible(self.panel.show_address_bar)
        for nav_button in self.panel.navigation_buttons:
            nav_button.setVisible(self.panel.show_navigation_buttons)

    def _apply_toolbar_font(self) -> None:
        toolbar_widgets: list[QWidget] = [
            self.panel.refresh_btn,
            self.panel.root_combo,
            self.panel.address_edit,
            *self.panel.navigation_buttons,
        ]
        for widget in toolbar_widgets:
            widget.setFont(self.panel.navigation_font_value)
        for button in self.panel.root_buttons:
            button.setFont(self.panel.navigation_font_value)

    def _apply_file_list_font(self) -> None:
        for index in range(self.panel.tabs.count()):
            widget = self.panel.tabs.widget(index)
            if isinstance(widget, ExplorerTab):
                widget.view.setFont(self.panel.file_list_font_value)

    def _apply_size_formatters_to_tabs(self) -> None:
        for index in range(self.panel.tabs.count()):
            widget = self.panel.tabs.widget(index)
            if isinstance(widget, ExplorerTab):
                widget.set_file_size_formatter(self.panel.file_list_size_formatter)
                widget.set_properties_size_formatter(
                    self.panel.properties_size_formatter
                )

    def _apply_visual_role(self) -> None:
        if self.panel.pane_role == "active":
            color = self.panel.active_role_color
            alpha = self._alpha_from_percent(self.panel.active_role_intensity_percent)
            background_color = (
                f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
            )
        elif self.panel.pane_role == "target":
            color = self.panel.target_role_color
            alpha = self._alpha_from_percent(self.panel.target_role_intensity_percent)
            background_color = (
                f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
            )
        else:
            background_color = "rgba(0, 0, 0, 0)"
        panel_object_name = self.panel.objectName()
        self.panel.setStyleSheet(
            f"QWidget#{panel_object_name} {{ "
            f"border: none; "
            f"background-color: {background_color}; "
            f"}}"
        )

    def _normalize_percent(self, value: int) -> int:
        if value < 0:
            return 0
        if value > 100:
            return 100
        return int(value)

    def _alpha_from_percent(self, percent: int) -> int:
        normalized = self._normalize_percent(percent)
        return int((normalized / 100.0) * 255)
