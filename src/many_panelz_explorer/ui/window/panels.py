"""Panel lifecycle coordination for explorer windows."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from ...panel_widget import PanelWidget
from .layout import WindowLayoutCoordinator
from .panel_columns import WindowPanelColumnSyncCoordinator

if TYPE_CHECKING:
    from ...window import ExplorerWindow


type PanelState = dict[str, Any]
type TabsState = dict[int, PanelState]
type PanelRows = list[list[int]]


def serialize_window_tabs_state(window: ExplorerWindow) -> TabsState:
    """Serialize all panel tabs into persistence state."""

    return {
        panel_id: panel.state_coordinator.serialize_state()
        for panel_id, panel in window.panel_widgets.items()
    }


def resolve_window_target_panel_id(
    window: ExplorerWindow,
    source_panel_id: int,
) -> int | None:
    """Resolve the preferred target panel for cross-panel actions."""

    ordered = WindowLayoutCoordinator.ordered_panel_ids(window.layout_rows)
    candidates = [pid for pid in ordered if pid != source_panel_id]
    if not candidates:
        return None
    if window.last_non_source_panel_id in candidates:
        return window.last_non_source_panel_id
    return candidates[0]


def window_default_close_warning(window: ExplorerWindow) -> bool:
    """Return whether closing the window should be treated as lossy."""

    if len(window.panel_widgets) > 1:
        return True
    if window.active_panel_id is None:
        return False
    panel = window.panel_widgets.get(window.active_panel_id)
    return panel is not None and panel.tab_count() > 1


def _clear_layout(window: ExplorerWindow) -> None:
    """Delete the current central layout widgets."""
    while window.central_layout.count() > 0:
        item = window.central_layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()


def _build_rows_widget(
    window: ExplorerWindow,
    panel_widgets: dict[int, PanelWidget],
    rows: PanelRows,
) -> QWidget | None:
    """Build the nested splitter widget for the current rows."""
    if not rows:
        return None
    if len(rows) == 1:
        return _build_row_widget(window, panel_widgets, rows[0])

    splitter = QSplitter(Qt.Orientation.Vertical, window)
    for row in rows:
        row_widget = _build_row_widget(window, panel_widgets, row)
        splitter.addWidget(row_widget if row_widget is not None else QWidget())
    splitter.setChildrenCollapsible(False)
    splitter.setSizes([1000] * len(rows))
    return splitter


def _build_row_widget(
    window: ExplorerWindow,
    panel_widgets: dict[int, PanelWidget],
    row: list[int],
) -> QWidget | None:
    """Build a single horizontal splitter row."""
    if not row:
        return None
    if len(row) == 1:
        panel = panel_widgets.get(row[0])
        return panel if panel is not None else QWidget()

    splitter = QSplitter(Qt.Orientation.Horizontal, window)
    for panel_id in row:
        panel = panel_widgets.get(panel_id)
        splitter.addWidget(panel if panel is not None else QWidget())
    splitter.setChildrenCollapsible(False)
    splitter.setSizes([1000] * len(row))
    return splitter


def _activate_panel_and_focus(
    coordinator: WindowPanelsCoordinator,
    panel_id: int,
) -> None:
    """Activate a panel and transfer focus to its current view."""
    coordinator.set_active_panel(panel_id)
    panel = coordinator.window.panel_widgets.get(panel_id)
    if panel is None:
        return
    tab = panel.current_tab()
    if tab is not None:
        tab.view.setFocus()


class WindowPanelsCoordinator:
    """Manage panel lifecycle, active state, and widget rebuilds."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Initialize the panel coordinator."""
        self.window = window
        self.column_sync_coordinator = WindowPanelColumnSyncCoordinator(window)

    def split_active_panel(self, orientation: Qt.Orientation) -> None:
        """Split the active panel and focus the new pane."""
        active_panel = self.active_panel()
        if self.window.active_panel_id is None or active_panel is None:
            return

        tabs_state = serialize_window_tabs_state(self.window)
        rows = deepcopy(self.window.layout_rows)
        row_index, column_index = self.window.layout_coordinator.find_panel_position(
            self.window.active_panel_id,
            rows,
        )
        if row_index is None or column_index is None:
            return

        seed_path = self.window.preferences_coordinator.resolve_new_context_path(
            active_panel.current_path()
        )
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
        seed_path = self.window.preferences_coordinator.resolve_new_context_path(
            panel.current_path()
        )
        panel.add_tab(seed_path)

    def clone_active_panel(self, orientation: Qt.Orientation) -> None:
        """Clone the active panel into a new split."""
        if self.window.active_panel_id is None:
            return

        tabs_state = serialize_window_tabs_state(self.window)
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
        file_list_font, navigation_font = (
            self.window.preferences_coordinator.effective_panel_fonts()
        )
        (
            active_color_hex,
            active_intensity_percent,
            target_color_hex,
            target_intensity_percent,
        ) = self.window.preferences_coordinator.panel_role_visual_preferences()
        (
            show_refresh_button,
            show_root_buttons,
            show_root_dropdown,
            show_address_bar,
            show_navigation_buttons,
        ) = self.window.preferences_coordinator.panel_toolbar_visibility_preferences()
        for panel_id in panel_ids:
            panel_state = tabs_state.get(panel_id)
            panel = PanelWidget(
                panel_id=panel_id,
                default_path=self.window.preferences_coordinator.resolve_new_context_path(
                    self.window.preferences_coordinator.initial_path
                ),
                show_hidden=self.window.preferences_coordinator.show_hidden_enabled,
                show_root_dropdown=(
                    self.window.preferences_coordinator.show_root_dropdown_enabled
                ),
                file_list_size_formatter=(
                    self.window.preferences_coordinator.format_file_list_bytes
                ),
                properties_size_formatter=(
                    self.window.preferences_coordinator.format_properties_bytes
                ),
                roots_provider=self.window.roots_provider,
                parent=self.window,
            )
            panel.activated.connect(lambda pid=panel_id: self.set_active_panel(pid))
            panel.current_context_changed.connect(self.window.update_pane_visuals)
            panel.column_widths_sync_requested.connect(
                self.column_sync_coordinator.panel_widths_sync_callback(panel_id)
            )
            panel.became_empty.connect(lambda pid=panel_id: self.close_panel_by_id(pid))
            panel.state_coordinator.set_column_width_auto_align_mode(
                self.window.preferences_coordinator.column_width_auto_align_mode
            )

            if isinstance(panel_state, dict):
                panel.state_coordinator.restore_state(panel_state)
            else:
                panel.add_tab(
                    self.window.preferences_coordinator.resolve_new_context_path(
                        self.window.preferences_coordinator.initial_path
                    )
                )

            panel.presentation_coordinator.set_role_visual_preferences(
                active_color_hex=active_color_hex,
                active_intensity_percent=active_intensity_percent,
                target_color_hex=target_color_hex,
                target_intensity_percent=target_intensity_percent,
            )
            panel.presentation_coordinator.apply_toolbar_visibility(
                show_refresh_button=show_refresh_button,
                show_root_buttons=show_root_buttons,
                show_root_dropdown=show_root_dropdown,
                show_address_bar=show_address_bar,
                show_navigation_buttons=show_navigation_buttons,
            )
            panel.presentation_coordinator.apply_font_preferences(
                file_list_font=file_list_font,
                navigation_font=navigation_font,
            )
            panel.widget_map_coordinator.set_enabled(
                self.window.preferences_coordinator.show_widget_map_enabled
            )
            new_panel_widgets[panel_id] = panel

        self.window.panel_widgets = new_panel_widgets

        root_widget = _build_rows_widget(
            self.window,
            self.window.panel_widgets,
            self.window.layout_rows,
        )
        if root_widget is None:
            root_widget = QWidget()

        _clear_layout(self.window)
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

        tabs_state = serialize_window_tabs_state(self.window)
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
        _activate_panel_and_focus(self, ordered[next_index])

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
        _activate_panel_and_focus(self, ordered[next_index])
