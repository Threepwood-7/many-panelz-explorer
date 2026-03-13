"""Panel lifecycle coordination for explorer windows."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from ...panel_widget import PanelWidget
from .layout import WindowLayoutCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...window import ExplorerWindow


type PanelState = dict[str, Any]
type TabsState = dict[int, PanelState]
type PanelRows = list[list[int]]


class WindowPanelsCoordinator:
    """Manage panel lifecycle, active state, and widget rebuilds."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Initialize the panel coordinator."""
        self.window = window

    def split_active_panel(self, orientation: Qt.Orientation) -> None:
        """Split the active panel and focus the new pane."""
        active_panel = self.active_panel()
        if self.window.active_panel_id is None or active_panel is None:
            return

        tabs_state = self.serialize_tabs_state()
        rows = deepcopy(self.window.layout_rows)
        row_index, column_index = self.window.layout_coordinator.find_panel_position(
            self.window.active_panel_id,
            rows,
        )
        if row_index is None or column_index is None:
            return

        seed_path = self.window.resolve_new_context_path(active_panel.current_path())
        preferred_active_panel: int | None = None
        is_horizontal_split = orientation == Qt.Orientation.Horizontal
        if is_horizontal_split:
            new_panel_id = self.window.layout_coordinator.allocate_panel_id(
                rows,
                tabs_state,
            )
            rows[row_index].insert(column_index + 1, new_panel_id)
            tabs_state[new_panel_id] = self.window.layout_coordinator.new_panel_state(
                new_panel_id,
                seed_path,
            )
            preferred_active_panel = new_panel_id
        else:
            source_row = rows[row_index]
            new_row: list[int] = []
            for _source_panel_id in source_row:
                new_panel_id = self.window.layout_coordinator.allocate_panel_id(
                    rows,
                    tabs_state,
                )
                new_row.append(new_panel_id)
                tabs_state[new_panel_id] = (
                    self.window.layout_coordinator.new_panel_state(
                        new_panel_id,
                        seed_path,
                    )
                )
            rows.insert(row_index + 1, new_row)
            preferred_active_panel = new_row[0] if new_row else None

        self.window.layout_rows = self.window.layout_coordinator.normalize_rows(rows)
        self.window.layout_coordinator.sync_panel_tree_from_rows()
        self.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
        )

    def new_tab_in_active_panel(self) -> None:
        """Open a new tab in the active panel."""
        panel = self.active_panel()
        if panel is None:
            return
        seed_path = self.window.resolve_new_context_path(panel.current_path())
        panel.add_tab(seed_path)

    def clone_active_panel(self, orientation: Qt.Orientation) -> None:
        """Clone the active panel into a new split."""
        if self.window.active_panel_id is None:
            return

        tabs_state = self.serialize_tabs_state()
        rows = deepcopy(self.window.layout_rows)
        row_index, column_index = self.window.layout_coordinator.find_panel_position(
            self.window.active_panel_id,
            rows,
        )
        if row_index is None or column_index is None:
            return

        source_state = tabs_state.get(
            self.window.active_panel_id
        ) or self.window.layout_coordinator.default_panel_state(
            self.window.active_panel_id
        )
        preferred_active_panel: int | None = None
        is_horizontal_split = orientation == Qt.Orientation.Horizontal
        if is_horizontal_split:
            new_panel_id = self.window.layout_coordinator.allocate_panel_id(
                rows,
                tabs_state,
            )
            rows[row_index].insert(column_index + 1, new_panel_id)
            cloned_state = deepcopy(source_state)
            cloned_state["panel_id"] = new_panel_id
            tabs_state[new_panel_id] = cloned_state
            preferred_active_panel = new_panel_id
        else:
            source_row = list(rows[row_index])
            new_row: list[int] = []
            for source_panel_id in source_row:
                source_panel_state = tabs_state.get(
                    source_panel_id
                ) or self.window.layout_coordinator.default_panel_state(source_panel_id)
                new_panel_id = self.window.layout_coordinator.allocate_panel_id(
                    rows,
                    tabs_state,
                )
                new_row.append(new_panel_id)
                cloned_state = deepcopy(source_panel_state)
                cloned_state["panel_id"] = new_panel_id
                tabs_state[new_panel_id] = cloned_state
            rows.insert(row_index + 1, new_row)
            preferred_active_panel = new_row[0] if new_row else None

        self.window.layout_rows = self.window.layout_coordinator.normalize_rows(rows)
        self.window.layout_coordinator.sync_panel_tree_from_rows()
        self.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
        )

    def close_active_tab(self) -> None:
        """Close the current tab in the active panel."""
        panel = self.active_panel()
        if panel is None:
            return
        panel.close_current_tab()
        if panel.tab_count() == 0:
            self.close_panel_by_id(panel.panel_id)

    def close_active_panel(self) -> None:
        """Close the active panel."""
        if self.window.active_panel_id is None:
            return
        self.close_panel_by_id(self.window.active_panel_id)

    def refresh_active_panel(self) -> None:
        """Refresh the active panel contents."""
        panel = self.active_panel()
        if panel is not None:
            panel.navigation_coordinator.refresh_current_path()

    def align_columns_current_panel_tabs(self) -> None:
        """Apply current tab widths across the active panel tabs."""
        panel = self.active_panel()
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is None:
            return
        widths = list(tab.columns.widths)
        panel.apply_column_widths_to_panel_tabs(widths, source_tab=tab)
        self.window.statusBar().showMessage(
            "Aligned columns in current panel tabs.",
            2000,
        )

    def align_columns_all_panels_tabs(self) -> None:
        """Broadcast current tab widths to all panels."""
        panel = self.active_panel()
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is None:
            return
        widths: list[object] = list(tab.columns.widths)
        self.window.controller.broadcast_column_widths(
            widths,
            source_window=self.window,
            source_panel_id=panel.panel_id,
            source_tab=tab,
        )
        self.window.statusBar().showMessage(
            "Aligned columns in all panels and tabs.",
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

    def rebuild_from_tree(
        self,
        tabs_state: TabsState,
        preferred_active_panel: int | None,
    ) -> None:
        """Rebuild panel widgets from the current row layout."""
        normalized_rows = self.window.layout_coordinator.normalize_rows(
            self.window.layout_rows
        )
        panel_ids = WindowLayoutCoordinator.ordered_panel_ids(normalized_rows)
        if not panel_ids:
            normalized_rows = [[1]]
            panel_ids = [1]

        self.window.layout_rows = normalized_rows
        self.window.layout_coordinator.sync_panel_tree_from_rows()

        new_panel_widgets: dict[int, PanelWidget] = {}
        file_list_font, navigation_font = self.window.effective_panel_fonts()
        (
            active_color_hex,
            active_intensity_percent,
            target_color_hex,
            target_intensity_percent,
        ) = self.window.panel_role_visual_preferences()
        (
            show_refresh_button,
            show_root_buttons,
            show_root_dropdown,
            show_address_bar,
            show_navigation_buttons,
        ) = self.window.panel_toolbar_visibility_preferences()
        for panel_id in panel_ids:
            panel_state = tabs_state.get(panel_id)
            panel = PanelWidget(
                panel_id=panel_id,
                default_path=self.window.resolve_new_context_path(
                    self.window.initial_path
                ),
                show_hidden=self.window.show_hidden_enabled,
                show_root_dropdown=self.window.show_root_dropdown_enabled,
                file_list_size_formatter=self.window.format_file_list_bytes,
                properties_size_formatter=self.window.format_properties_bytes,
                roots_provider=self.window.roots_provider,
                parent=self.window,
            )
            panel.activated.connect(lambda pid=panel_id: self.set_active_panel(pid))
            panel.current_context_changed.connect(self.window.update_pane_visuals)
            panel.column_widths_sync_requested.connect(
                self.panel_widths_sync_callback(panel_id)
            )
            panel.became_empty.connect(lambda pid=panel_id: self.close_panel_by_id(pid))
            panel.set_column_width_auto_align_mode(
                self.window.column_width_auto_align_mode
            )

            if isinstance(panel_state, dict):
                panel.restore_state(panel_state)
            else:
                panel.add_tab(
                    self.window.resolve_new_context_path(self.window.initial_path)
                )

            panel.set_role_visual_preferences(
                active_color_hex=active_color_hex,
                active_intensity_percent=active_intensity_percent,
                target_color_hex=target_color_hex,
                target_intensity_percent=target_intensity_percent,
            )
            panel.apply_toolbar_visibility(
                show_refresh_button=show_refresh_button,
                show_root_buttons=show_root_buttons,
                show_root_dropdown=show_root_dropdown,
                show_address_bar=show_address_bar,
                show_navigation_buttons=show_navigation_buttons,
            )
            panel.apply_font_preferences(
                file_list_font=file_list_font,
                navigation_font=navigation_font,
            )
            panel.set_widget_map_enabled(self.window.show_widget_map_enabled)
            new_panel_widgets[panel_id] = panel

        self.window.panel_widgets = new_panel_widgets

        root_widget = self._build_rows_widget(self.window.layout_rows)
        if root_widget is None:
            root_widget = QWidget()

        self._clear_layout()
        self.window.central_layout.addWidget(root_widget)

        target_active = preferred_active_panel
        if target_active is None or target_active not in self.window.panel_widgets:
            target_active = next(iter(self.window.panel_widgets), None)
        if target_active is not None:
            self.set_active_panel(target_active)
        else:
            self.window.update_pane_visuals()

    def set_active_panel(self, panel_id: int) -> None:
        """Mark the given panel as active."""
        if panel_id not in self.window.panel_widgets:
            return
        previous = self.window.active_panel_id
        if (
            previous is not None
            and previous != panel_id
            and previous in self.window.panel_widgets
        ):
            self.window.last_non_source_panel_id = previous
        self.window.active_panel_id = panel_id
        self.window.update_pane_visuals()

    def active_panel(self) -> PanelWidget | None:
        """Return the active panel widget."""
        if self.window.active_panel_id is None:
            return None
        return self.window.panel_widgets.get(self.window.active_panel_id)

    def close_panel_by_id(self, panel_id: int) -> None:
        """Close a panel by identifier and rebuild the layout."""
        if panel_id not in self.window.panel_widgets:
            return

        tabs_state = self.serialize_tabs_state()
        rows = deepcopy(self.window.layout_rows)
        removed = False
        new_rows: PanelRows = []
        for row in rows:
            filtered = [pid for pid in row if pid != panel_id]
            if len(filtered) != len(row):
                removed = True
            if filtered:
                new_rows.append(filtered)

        if not removed:
            return

        tabs_state.pop(panel_id, None)
        if panel_id == self.window.last_non_source_panel_id:
            self.window.last_non_source_panel_id = None
        if panel_id == self.window.active_panel_id:
            self.window.active_panel_id = None

        if not new_rows:
            self.window.close()
            return

        self.window.layout_rows = self.window.layout_coordinator.normalize_rows(
            new_rows
        )
        self.window.layout_coordinator.sync_panel_tree_from_rows()
        ordered = WindowLayoutCoordinator.ordered_panel_ids(self.window.layout_rows)
        preferred = ordered[0] if ordered else None
        self.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred,
        )

    def serialize_tabs_state(self) -> TabsState:
        """Serialize all panel tabs into persistence state."""
        return {
            panel_id: panel.serialize_state()
            for panel_id, panel in self.window.panel_widgets.items()
        }

    def focus_next_panel(self) -> None:
        """Move focus to the next panel."""
        ordered = WindowLayoutCoordinator.ordered_panel_ids(self.window.layout_rows)
        if not ordered:
            return
        if self.window.active_panel_id in ordered:
            current = ordered.index(self.window.active_panel_id)
            next_index = (current + 1) % len(ordered)
        else:
            next_index = 0
        self._activate_panel_and_focus(ordered[next_index])

    def focus_previous_panel(self) -> None:
        """Move focus to the previous panel."""
        ordered = WindowLayoutCoordinator.ordered_panel_ids(self.window.layout_rows)
        if not ordered:
            return
        if self.window.active_panel_id in ordered:
            current = ordered.index(self.window.active_panel_id)
            next_index = (current - 1) % len(ordered)
        else:
            next_index = 0
        self._activate_panel_and_focus(ordered[next_index])

    def resolve_target_panel_id(self, source_panel_id: int) -> int | None:
        """Resolve the preferred target panel for cross-panel actions."""
        ordered = WindowLayoutCoordinator.ordered_panel_ids(self.window.layout_rows)
        candidates = [pid for pid in ordered if pid != source_panel_id]
        if not candidates:
            return None
        if self.window.last_non_source_panel_id in candidates:
            return self.window.last_non_source_panel_id
        return candidates[0]

    def on_panel_column_widths_sync_requested(
        self,
        panel_id: int,
        widths: list[object],
        source_tab: object,
    ) -> None:
        """Forward panel column width changes to the app controller."""
        self.window.controller.broadcast_column_widths(
            widths,
            source_window=self.window,
            source_panel_id=panel_id,
            source_tab=source_tab,
        )

    def apply_column_widths_all_panels(
        self,
        widths: list[object],
        *,
        source_panel_id: int | None = None,
        source_tab: object | None = None,
    ) -> None:
        """Apply a width set to every panel in the window."""
        _ = source_panel_id, source_tab
        for panel_id, panel in self.window.panel_widgets.items():
            _ = panel_id
            panel.apply_column_widths_to_panel_tabs(widths)

    def default_close_warning(self) -> bool:
        """Return whether closing the window should be treated as lossy."""
        if len(self.window.panel_widgets) > 1:
            return True
        panel = self.active_panel()
        return panel is not None and panel.tab_count() > 1

    def _clear_layout(self) -> None:
        """Delete the current central layout widgets."""
        while self.window.central_layout.count() > 0:
            item = self.window.central_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _build_rows_widget(self, rows: PanelRows) -> QWidget | None:
        """Build the nested splitter widget for the current rows."""
        if not rows:
            return None
        if len(rows) == 1:
            return self._build_row_widget(rows[0])

        splitter = QSplitter(Qt.Orientation.Vertical, self.window)
        for row in rows:
            row_widget = self._build_row_widget(row)
            splitter.addWidget(row_widget if row_widget is not None else QWidget())
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([1000] * len(rows))
        return splitter

    def _build_row_widget(self, row: list[int]) -> QWidget | None:
        """Build a single horizontal splitter row."""
        if not row:
            return None
        if len(row) == 1:
            panel = self.window.panel_widgets.get(row[0])
            return panel if panel is not None else QWidget()

        splitter = QSplitter(Qt.Orientation.Horizontal, self.window)
        for panel_id in row:
            panel = self.window.panel_widgets.get(panel_id)
            splitter.addWidget(panel if panel is not None else QWidget())
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([1000] * len(row))
        return splitter

    def _activate_panel_and_focus(self, panel_id: int) -> None:
        """Activate a panel and transfer focus to its current view."""
        self.set_active_panel(panel_id)
        panel = self.window.panel_widgets.get(panel_id)
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is not None:
            tab.view.setFocus()
