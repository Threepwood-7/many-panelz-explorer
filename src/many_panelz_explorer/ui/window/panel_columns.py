"""Column-width synchronization helpers for explorer window panels."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ...explorer_tab import ExplorerTab
    from ...panel_widget import PanelWidget
    from ...window import ExplorerWindow


class WindowPanelColumnSyncCoordinator:
    """Manage manual and debounced column-width synchronization scopes."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Store the owning window."""
        self.window = window

    def align_columns_current_panel_tabs(self) -> None:
        """Apply current tab widths across the active panel tabs."""
        panel, tab = self._active_panel_and_tab()
        if panel is None or tab is None:
            return
        widths = list(tab.columns.widths)
        panel.state_coordinator.apply_column_widths_to_panel_tabs(
            widths,
            source_tab=tab,
        )
        self.window.statusBar().showMessage(
            "Aligned columns in current panel tabs.",
            2000,
        )

    def align_columns_all_panels_tabs(self) -> None:
        """Apply current tab widths to all panels in the current window."""
        _panel, tab = self._active_panel_and_tab()
        if tab is None:
            return
        widths = list(tab.columns.widths)
        self.apply_column_widths_all_panels(widths)
        self.window.statusBar().showMessage(
            "Aligned columns in all panels and tabs in the current window.",
            2000,
        )

    def align_columns_all_windows(self) -> None:
        """Apply current tab widths to all panels in every open window."""
        panel, tab = self._active_panel_and_tab()
        if panel is None or tab is None:
            return
        widths: list[object] = list(tab.columns.widths)
        self.window.controller.broadcast_column_widths(
            widths,
            source_window=self.window,
            source_panel_id=panel.panel_id,
            source_tab=tab,
        )
        self.window.statusBar().showMessage(
            "Aligned columns in all panels and tabs in all windows.",
            2000,
        )

    def panel_widths_sync_callback(
        self,
        panel_id: int,
    ) -> Callable[[object, object], None]:
        """Build the per-panel column width sync callback."""

        def _callback(widths: object, source_tab: object) -> None:
            self.on_panel_column_widths_sync_requested(
                panel_id,
                cast("list[object]", widths),
                source_tab,
            )

        return _callback

    def on_panel_column_widths_sync_requested(
        self,
        panel_id: int,
        widths: list[object],
        source_tab: object,
    ) -> None:
        """Apply debounced column width changes using the configured scope."""
        panel = self.window.panel_widgets.get(panel_id)
        if panel is None:
            return
        mode = panel.column_width_auto_align_mode
        if mode == panel.COLUMN_ALIGN_MODE_CURRENT_WINDOW_PANELS_TABS:
            self.apply_column_widths_all_panels(
                widths,
                source_panel_id=panel_id,
                source_tab=source_tab,
            )
            return
        if mode == panel.COLUMN_ALIGN_MODE_ALL_WINDOWS_PANELS_TABS:
            self.window.controller.broadcast_column_widths(
                widths,
                source_window=self.window,
                source_panel_id=panel_id,
                source_tab=source_tab,
            )

    def apply_column_widths_all_panels(
        self,
        widths: Sequence[object],
        *,
        source_panel_id: int | None = None,
        source_tab: object | None = None,
    ) -> None:
        """Apply a width set to every panel in the current window."""
        for panel_id, panel in self.window.panel_widgets.items():
            panel.state_coordinator.apply_column_widths_to_panel_tabs(
                widths,
                source_tab=(
                    cast("ExplorerTab | None", source_tab)
                    if source_panel_id is not None and panel_id == source_panel_id
                    else None
                ),
            )

    def _active_panel_and_tab(self) -> tuple[PanelWidget | None, ExplorerTab | None]:
        """Return the active panel and its current tab when available."""
        panel = self.window.panels_coordinator.active_panel()
        if panel is None:
            return None, None
        return panel, panel.current_tab()
