"""State serialization and column-sync coordination for a panel."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ...explorer_tab import ExplorerTab

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ...panel_widget import PanelWidget


class PanelStateCoordinator:
    """Own panel state restore/serialize and column width synchronization."""

    def __init__(self, panel: PanelWidget) -> None:
        self.panel = panel

    def set_column_width_auto_align_mode(self, mode: str) -> None:
        """Store the requested column auto-alignment mode."""

        self.panel.column_width_auto_align_mode = self._normalize_column_width_mode(
            mode
        )

    def apply_column_widths_to_panel_tabs(
        self,
        widths: Sequence[object],
        *,
        source_tab: ExplorerTab | None = None,
    ) -> None:
        """Apply normalized widths to tabs in this panel."""

        normalized = self._coerce_column_widths(widths)
        if not normalized:
            return
        self.panel.column_widths = list(normalized)
        self._apply_column_widths_to_all_tabs(normalized, source_tab=source_tab)

    def initialize_new_tab_column_widths(
        self,
        *,
        tab: ExplorerTab,
        source_widths: Sequence[object],
    ) -> None:
        """Seed a newly added tab with the panel's synchronized widths."""

        if (
            self.panel.column_width_auto_align_mode != self.panel.COLUMN_ALIGN_MODE_NONE
            and source_widths
            and not self.panel.restoring_state
        ):
            self.panel.column_widths = self._coerce_column_widths(source_widths)
        if (
            self.panel.column_width_auto_align_mode != self.panel.COLUMN_ALIGN_MODE_NONE
            and self.panel.column_widths
        ):
            tab.columns.set_widths(self.panel.column_widths)
            return
        self.panel.column_widths = list(tab.columns.widths)

    def serialize_state(self) -> dict[str, object]:
        """Serialize panel tabs and column widths."""

        tabs: list[dict[str, str]] = []
        for index in range(self.panel.tabs.count()):
            widget = self.panel.tabs.widget(index)
            if isinstance(widget, ExplorerTab):
                tabs.append(widget.serialize_state())

        return {
            "panel_id": self.panel.panel_id,
            "current_index": self.panel.tabs.currentIndex(),
            "tabs": tabs,
            "column_widths": list(self.panel.column_widths),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore tabs, current index, and remembered column widths."""

        raw_widths = state.get("column_widths", [])
        if isinstance(raw_widths, list):
            self.panel.column_widths = self._coerce_column_widths(
                cast("list[object]", raw_widths)
            )

        self.panel.restoring_state = True
        try:
            tabs = state.get("tabs", [])
            if not isinstance(tabs, list) or not tabs:
                self.panel.add_tab(self.panel.default_path)
                if self.panel.column_widths:
                    self._apply_column_widths_to_all_tabs(self.panel.column_widths)
                return

            for tab_state_raw in cast("list[object]", tabs):
                if not isinstance(tab_state_raw, dict):
                    continue
                tab_state = cast("dict[str, Any]", tab_state_raw)
                path_value = tab_state.get("path", str(self.panel.default_path))
                self.panel.add_tab(Path(str(path_value)))

            current_index_raw = state.get("current_index", 0)
            try:
                current_index = int(current_index_raw)
            except (TypeError, ValueError):
                current_index = 0
            current_index = max(0, min(current_index, self.panel.tabs.count() - 1))
            self.panel.tabs.setCurrentIndex(current_index)
            if self.panel.column_widths:
                self._apply_column_widths_to_all_tabs(self.panel.column_widths)
            self.panel.presentation_coordinator.sync_toolbar_for_current_tab()
        finally:
            self.panel.restoring_state = False

    def close_tab_at(self, index: int) -> None:
        """Close the tab at the given index."""

        widget = self.panel.tabs.widget(index)
        self.panel.tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        if self.panel.tabs.count() == 0:
            self.panel.became_empty.emit()
            return
        self.panel.presentation_coordinator.sync_toolbar_for_current_tab()
        self.panel.widget_map_coordinator.sync_overlay()

    def on_current_changed(self, index: int) -> None:
        """Handle a newly selected current tab."""

        if index >= 0:
            self.panel.activated.emit()
            tab = self.panel.current_tab()
            if (
                tab is not None
                and self.panel.column_widths
                and self.panel.column_width_auto_align_mode
                != self.panel.COLUMN_ALIGN_MODE_NONE
            ):
                tab.columns.set_widths(self.panel.column_widths)
            if tab is not None and self.panel.filter_edit.isVisible():
                tab.navigation.set_inline_filter(self.panel.filter_edit.text())
            self.panel.current_context_changed.emit()
        self.panel.presentation_coordinator.sync_toolbar_for_current_tab()
        self.panel.widget_map_coordinator.sync_overlay()

    def on_tab_navigation_changed(self, tab: ExplorerTab) -> None:
        """Retitle and resync toolbar state after tab navigation changes."""

        self.panel.retitle_tab(tab)
        if tab is self.panel.current_tab():
            self.panel.presentation_coordinator.sync_toolbar_for_current_tab()
            self.panel.current_context_changed.emit()

    def on_tab_column_widths_changed(self, tab: ExplorerTab, widths: object) -> None:
        """Queue a panel or cross-panel width synchronization update."""

        if self.panel.syncing_column_widths or self.panel.restoring_state:
            return
        if not isinstance(widths, tuple) or not widths:
            return

        normalized = self._coerce_column_widths(
            list(cast("tuple[object, ...]", widths))
        )
        if not normalized or normalized == self.panel.column_widths:
            return
        self.panel.column_widths = normalized
        self.panel.pending_column_widths_sync = list(normalized)
        self.panel.pending_column_widths_source_tab = tab
        self.panel.column_sync_timer.start(self.panel.COLUMN_SYNC_DEBOUNCE_MS)

    def flush_pending_column_width_sync(self) -> None:
        """Apply or broadcast pending synchronized column widths."""

        if not self.panel.pending_column_widths_sync:
            return
        source_tab = self.panel.pending_column_widths_source_tab
        widths = list(self.panel.pending_column_widths_sync)
        self.panel.pending_column_widths_sync = []
        self.panel.pending_column_widths_source_tab = None
        if self.panel.column_width_auto_align_mode == self.panel.COLUMN_ALIGN_MODE_NONE:
            return
        if (
            self.panel.column_width_auto_align_mode
            == self.panel.COLUMN_ALIGN_MODE_CURRENT_PANEL_TABS
        ):
            self._apply_column_widths_to_all_tabs(widths, source_tab=source_tab)
            return
        self.panel.column_widths_sync_requested.emit(widths, source_tab)

    def _apply_column_widths_to_all_tabs(
        self,
        widths: list[int],
        *,
        source_tab: ExplorerTab | None = None,
    ) -> None:
        self.panel.syncing_column_widths = True
        try:
            for index in range(self.panel.tabs.count()):
                widget = self.panel.tabs.widget(index)
                if not isinstance(widget, ExplorerTab):
                    continue
                if source_tab is not None and widget is source_tab:
                    continue
                widget.columns.set_widths(widths)
        finally:
            self.panel.syncing_column_widths = False

    def _coerce_column_widths(self, widths: Sequence[object]) -> list[int]:
        normalized: list[int] = []
        for width in widths:
            if isinstance(width, bool):
                value = int(width)
            elif isinstance(width, int):
                value = width
            elif isinstance(width, float):
                value = int(width)
            elif isinstance(width, str):
                try:
                    value = int(width)
                except ValueError:
                    continue
            else:
                continue
            if value > 0:
                normalized.append(value)
        return normalized

    def _normalize_column_width_mode(self, mode: str) -> str:
        normalized = str(mode).strip().lower()
        if normalized in {
            self.panel.COLUMN_ALIGN_MODE_CURRENT_PANEL_TABS,
            self.panel.COLUMN_ALIGN_MODE_CURRENT_WINDOW_PANELS_TABS,
            self.panel.COLUMN_ALIGN_MODE_ALL_WINDOWS_PANELS_TABS,
            self.panel.COLUMN_ALIGN_MODE_NONE,
        }:
            return normalized
        return self.panel.COLUMN_ALIGN_MODE_CURRENT_PANEL_TABS
