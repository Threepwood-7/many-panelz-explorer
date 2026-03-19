"""State serialization and column-sync coordination for a panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ...explorer_tab import ExplorerTab
from ...panel_groups import DEFAULT_TAB_GROUP_ID, DEFAULT_TAB_GROUP_TITLE
from ...panel_tab_positions import normalize_panel_tab_position_mode

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ...panel_widget import PanelWidget
    from ..window.state_types import PanelState


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

    def serialize_state(self) -> PanelState:
        """Serialize panel tabs and column widths."""

        return {
            "panel_id": self.panel.panel_id,
            "active_group_id": self.panel.active_group_id,
            "groups": self.panel.serialize_tab_groups(),
            "tab_position_mode": normalize_panel_tab_position_mode(
                self.panel.tab_position_mode
            ),
        }

    def restore_state(self, state: PanelState) -> None:
        """Restore tabs, current index, and remembered column widths."""

        self.panel.tab_position_mode = normalize_panel_tab_position_mode(
            state.get("tab_position_mode", self.panel.TAB_POSITION_MODE_DEFAULT)
        )

        self.panel.restoring_state = True
        try:
            groups = state.get("groups", [])
            if groups:
                self.panel.restore_tab_groups(
                    groups,
                    active_group_id=str(
                        state.get("active_group_id", DEFAULT_TAB_GROUP_ID)
                    ),
                )
            else:
                self.panel.restore_tab_groups(
                    [
                        {
                            "group_id": DEFAULT_TAB_GROUP_ID,
                            "title": DEFAULT_TAB_GROUP_TITLE,
                            "current_index": self._coerce_index(
                                state.get("current_index", 0)
                            ),
                            "tabs": state.get("tabs", []),
                            "column_widths": self._coerce_column_widths(
                                state.get("column_widths", [])
                            ),
                        }
                    ],
                    active_group_id=DEFAULT_TAB_GROUP_ID,
                )
            self.panel.presentation_coordinator.sync_toolbar_for_current_tab()
        finally:
            self.panel.restoring_state = False

    def close_tab_at(self, index: int) -> None:
        """Close the tab at the given index."""

        widget = self.panel.tabs.widget(index)
        if isinstance(widget, ExplorerTab):
            self.panel.tab_closed.emit(str(widget.navigation.path))
        self.panel.tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        if self.panel.tabs.count() == 0:
            self.panel.sync_active_group_state()
            if self.panel.can_close_active_group():
                self.panel.close_group(self.panel.active_group_id)
            else:
                self.panel.became_empty.emit()
            return
        self.panel.sync_active_group_state()
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

    def _coerce_index(self, value: object) -> int:
        """Normalize persisted tab indexes into a usable integer."""

        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

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
