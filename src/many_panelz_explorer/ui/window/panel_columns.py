"""Column-width synchronization helpers for explorer window panels."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer

from ...explorer_tab import ExplorerTab

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ...panel_widget import PanelWidget
    from ...window import ExplorerWindow


class WindowPanelColumnSyncCoordinator:
    """Manage column alignment, fitting, and debounced autofit scopes."""

    AUTOFIT_COLUMNS_DEBOUNCE_MS = 120

    def __init__(self, window: ExplorerWindow) -> None:
        """Store the owning window."""
        self.window = window
        self._autofit_timer = QTimer(window)
        self._autofit_timer.setSingleShot(True)
        self._autofit_timer.timeout.connect(self.autofit_columns)

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

    def fit_columns_current_window(self) -> None:
        """Fit all tab columns in the current window immediately."""
        if not self._fit_columns_all_panels():
            return
        self.window.statusBar().showMessage(
            "Fitted columns in all tabs in the current window.",
            2000,
        )

    def schedule_autofit_columns(self) -> None:
        """Debounce a window-wide fit pass when autofit is enabled."""
        if not self.window.preferences_coordinator.autofit_columns_enabled:
            self._autofit_timer.stop()
            return
        self._autofit_timer.start(self.AUTOFIT_COLUMNS_DEBOUNCE_MS)

    def autofit_columns(self) -> None:
        """Fit all tab columns in the current window when enabled."""
        if not self.window.preferences_coordinator.autofit_columns_enabled:
            return
        self._fit_columns_all_panels()

    def panel_widths_sync_callback(
        self,
        panel_id: int,
    ) -> Callable[[list[object], ExplorerTab | None], None]:
        """Build the per-panel column width sync callback."""

        def _callback(widths: list[object], source_tab: ExplorerTab | None) -> None:
            self.on_panel_column_widths_sync_requested(
                panel_id,
                widths,
                source_tab,
            )

        return _callback

    def on_panel_column_widths_sync_requested(
        self,
        panel_id: int,
        widths: list[object],
        source_tab: ExplorerTab | None,
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
        source_tab: ExplorerTab | None = None,
    ) -> None:
        """Apply a width set to every panel in the current window."""
        for panel_id, panel in self.window.panel_widgets.items():
            panel.state_coordinator.apply_column_widths_to_panel_tabs(
                widths,
                source_tab=(
                    source_tab
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

    def _fit_columns_all_panels(self) -> bool:
        """Fit all explorer tabs in the current window."""
        fitted_any = False
        for panel in self.window.panel_widgets.values():
            for index in range(panel.tabs.count()):
                widget = panel.tabs.widget(index)
                if not isinstance(widget, ExplorerTab):
                    continue
                widget.columns.fit_to_contents()
                fitted_any = True
            current_tab = panel.current_tab()
            if current_tab is not None:
                panel.column_widths = list(current_tab.columns.widths)
        return fitted_any
