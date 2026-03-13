"""Inline filter overlay coordination for a panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt

if TYPE_CHECKING:
    from PySide6.QtGui import QKeyEvent

    from ...panel_widget import PanelWidget


class PanelInlineFilterCoordinator:
    """Own inline filter overlay placement, visibility, and input flow."""

    def __init__(self, panel: PanelWidget) -> None:
        self.panel = panel

    def clear(self) -> None:
        """Clear the overlay text and the active tab filter."""

        self.panel.filter_edit.blockSignals(True)
        self.panel.filter_edit.setText("")
        self.panel.filter_edit.blockSignals(False)
        tab = self.panel.current_tab()
        if tab is not None:
            tab.navigation.clear_inline_filter()

    def position_overlay(self) -> None:
        """Place the overlay near the active file list."""

        margin = 8
        height = 30
        tab = self.panel.current_tab()
        if tab is not None:
            view = tab.view
            view_top_left = view.mapTo(self.panel, QPoint(0, 0))
            view_width = max(1, view.width())
            view_height = max(1, view.height())
            desired_width = max(220, int(view_width * 0.35))
            max_width = max(1, view_width - (margin * 2))
            width = min(desired_width, max_width)
            x = max(
                view_top_left.x() + margin,
                view_top_left.x() + view_width - margin - width,
            )
            y = max(
                view_top_left.y() + margin,
                view_top_left.y() + view_height - margin - height,
            )
            self.panel.filter_edit.setGeometry(x, y, width, height)
            self.panel.filter_edit.raise_()
            self.panel.widget_map_coordinator.sync_overlay()
            return

        width = max(220, int(self.panel.width() * 0.35))
        x = max(margin, self.panel.width() - width - margin)
        self.panel.filter_edit.setGeometry(x, margin, width, height)
        self.panel.filter_edit.raise_()
        self.panel.widget_map_coordinator.sync_overlay()

    def show_overlay(self, *, seed_text: str) -> None:
        """Show the inline filter overlay and optionally append seed text."""

        self.position_overlay()
        self.panel.filter_edit.setVisible(True)
        self.panel.filter_edit.raise_()
        self.panel.widget_map_coordinator.sync_overlay()
        self.panel.filter_edit.setFocus()
        if seed_text:
            self.panel.filter_edit.setText(self.panel.filter_edit.text() + seed_text)
            self.panel.filter_edit.setCursorPosition(len(self.panel.filter_edit.text()))

    def hide_overlay(self) -> None:
        """Hide the inline filter overlay."""

        self.panel.filter_edit.setVisible(False)
        self.panel.widget_map_coordinator.sync_overlay()

    def on_text_changed(self, text: str) -> None:
        """Push the current filter text into the active tab navigation state."""

        tab = self.panel.current_tab()
        if tab is not None:
            tab.navigation.set_inline_filter(text)

    def should_start_from_key(self, key_event: QKeyEvent) -> bool:
        """Return whether a key press should open the inline filter overlay."""

        if key_event.modifiers() not in {
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        }:
            return False
        text = key_event.text()
        if not text:
            return False
        if len(text) != 1 or text.isspace():
            return False
        return text.isprintable()
