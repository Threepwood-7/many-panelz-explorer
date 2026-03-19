"""Panel lifecycle coordination for explorer windows."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog

from .layout import WindowLayoutCoordinator
from .panel_columns import WindowPanelColumnSyncCoordinator
from .panel_rebuild import WindowPanelRebuildCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...panel_widget import PanelWidget
    from ...window import ExplorerWindow
    from .state_types import ClosedTabState, PanelRows, PanelState, TabsState


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
    return panel is not None and (
        panel.total_tab_count() > 1 or panel.group_count() > 1
    )


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
    """Manage panel lifecycle, active state, and layout mutations."""

    CLOSED_TAB_HISTORY_LIMIT = 30

    def __init__(self, window: ExplorerWindow) -> None:
        """Initialize the panel coordinator."""

        self.window = window
        self.column_sync_coordinator = WindowPanelColumnSyncCoordinator(window)
        self.rebuild_coordinator = WindowPanelRebuildCoordinator(
            window,
            self.column_sync_coordinator,
        )

    def split_active_panel(self, orientation: Qt.Orientation) -> None:
        """Split the active panel and focus the new pane."""

        active_panel = self.active_panel()
        if self.window.active_panel_id is None or active_panel is None:
            return

        rows, tabs_state = self._snapshot_layout_state()
        position = self._active_panel_position(rows)
        if position is None:
            return
        row_index, column_index = position

        preferred_active_panel = self._add_split_panel_states(
            rows=rows,
            tabs_state=tabs_state,
            orientation=orientation,
            row_index=row_index,
            column_index=column_index,
            seed_path=self._resolved_seed_path(active_panel.current_path()),
        )
        self._apply_layout_change(
            rows=rows,
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
        )

    def new_tab_in_active_panel(self) -> None:
        """Open a new tab in the active panel."""

        panel = self.active_panel()
        if panel is None:
            return
        panel.add_tab(self._resolved_seed_path(panel.current_path()))

    def new_group_in_active_panel(self) -> None:
        """Create a new tab group in the active panel."""

        panel = self.active_panel()
        if panel is None:
            return
        panel.create_group(
            seed_paths=[self._resolved_seed_path(panel.current_path())],
            activate=True,
        )

    def new_group_from_current_tab(self) -> None:
        """Create a new tab group seeded from the current tab."""

        panel = self.active_panel()
        if panel is None:
            return
        panel.clone_current_tab_to_new_group()

    def rename_active_group(self) -> None:
        """Prompt for a new title for the active tab group."""

        panel = self.active_panel()
        if panel is None:
            return
        title, accepted = QInputDialog.getText(
            self.window,
            "Rename Tab Group",
            "Group name:",
            text=panel.active_group_title,
        )
        if not accepted:
            return
        panel.rename_group(panel.active_group_id, title)

    def close_active_group(self) -> None:
        """Close the active tab group when another group remains."""

        panel = self.active_panel()
        if panel is None:
            return
        panel.close_group(panel.active_group_id)

    def focus_next_group(self) -> None:
        """Move focus to the next tab group in the active panel."""

        panel = self.active_panel()
        if panel is not None:
            panel.focus_relative_group(1)

    def focus_previous_group(self) -> None:
        """Move focus to the previous tab group in the active panel."""

        panel = self.active_panel()
        if panel is not None:
            panel.focus_relative_group(-1)

    def move_current_tab_to_group(self) -> None:
        """Prompt for a target tab group and move the current tab there."""

        panel = self.active_panel()
        if panel is None:
            return

        choices = panel.ordered_group_choices(include_active=False)
        if not choices:
            return
        labels = self._group_choice_labels(choices)
        label_to_group_id = {
            label: group_id
            for label, (group_id, _title) in zip(labels, choices, strict=True)
        }
        selected_label, accepted = QInputDialog.getItem(
            self.window,
            "Move Tab To Group",
            "Target group:",
            labels,
            0,
            False,
        )
        if not accepted:
            return
        target_group_id = label_to_group_id.get(selected_label)
        if target_group_id is None:
            return
        panel.move_current_tab_to_group(target_group_id)

    def move_current_tab_to_new_group(self) -> None:
        """Move the current tab into a newly created tab group."""

        panel = self.active_panel()
        if panel is None:
            return
        panel.move_current_tab_to_new_group()

    def clone_active_panel(self, orientation: Qt.Orientation) -> None:
        """Clone the active panel into a new split."""

        active_panel_id = self.window.active_panel_id
        if active_panel_id is None:
            return

        rows, tabs_state = self._snapshot_layout_state()
        position = self._active_panel_position(rows)
        if position is None:
            return
        row_index, column_index = position

        source_state = tabs_state.get(
            active_panel_id
        ) or self.window.layout_coordinator.default_panel_state(active_panel_id)
        preferred_active_panel = self._add_cloned_panel_states(
            rows=rows,
            tabs_state=tabs_state,
            orientation=orientation,
            row_index=row_index,
            column_index=column_index,
            source_state=source_state,
        )
        self._apply_layout_change(
            rows=rows,
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

    def reopen_last_closed_tab(self) -> None:
        """Reopen the most recently closed tab into the best available panel."""

        if not self.window.recently_closed_tabs:
            return

        closed_tab = self.window.recently_closed_tabs.pop(0)
        target_panel = self.active_panel()
        if target_panel is None:
            target_panel = self.window.panel_widgets.get(closed_tab["panel_id"])
        if target_panel is None:
            target_panel = self.first_ordered_panel()
        if target_panel is None:
            return

        self.set_active_panel(target_panel.panel_id)
        reopened_tab = target_panel.add_tab(Path(closed_tab["path"]))
        reopened_tab.view.setFocus()

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

    def refresh_all_panels(self) -> None:
        """Refresh every visible panel in the current window."""

        for panel in self.window.panel_widgets.values():
            panel.navigation_coordinator.refresh_current_path()

    def set_active_panel_tab_position_mode(self, mode: str) -> None:
        """Persist and apply a tab-position mode for the active panel."""

        panel = self.active_panel()
        if panel is None:
            return
        panel.presentation_coordinator.apply_tab_position(
            tab_position_mode=mode,
            default_tab_position=self.window.preferences_coordinator.default_tab_position,
        )
        self.window.ui_composer.sync_active_panel_tab_position_actions()

    def first_ordered_panel(self) -> PanelWidget | None:
        """Return the first ordered panel in the current layout."""

        ordered = WindowLayoutCoordinator.ordered_panel_ids(self.window.layout_rows)
        if not ordered:
            return None
        return self.window.panel_widgets.get(ordered[0])

    def target_panel(self) -> PanelWidget | None:
        """Return the resolved target panel for the active panel."""

        source_id = self.window.active_panel_id
        if source_id is None:
            return None
        target_id = resolve_window_target_panel_id(self.window, source_id)
        if target_id is None:
            return None
        return self.window.panel_widgets.get(target_id)

    def rebuild_from_tree(
        self,
        tabs_state: TabsState,
        preferred_active_panel: int | None,
    ) -> None:
        """Rebuild panel widgets from the current row layout."""

        self.rebuild_coordinator.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
            panel_activated_callback=self._panel_activated_callback,
            panel_empty_callback=self._panel_empty_callback,
            set_active_panel=self.set_active_panel,
        )

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

        active_panel_id = self.window.active_panel_id
        if active_panel_id is None:
            return None
        return self.window.panel_widgets.get(active_panel_id)

    def close_panel_by_id(self, panel_id: int) -> None:
        """Close a panel by identifier and rebuild the layout."""

        if panel_id not in self.window.panel_widgets:
            return

        rows, tabs_state = self._snapshot_layout_state()
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

        normalized_rows = self.window.layout_coordinator.normalize_rows(new_rows)
        ordered = WindowLayoutCoordinator.ordered_panel_ids(normalized_rows)
        self._apply_layout_change(
            rows=normalized_rows,
            tabs_state=tabs_state,
            preferred_active_panel=ordered[0] if ordered else None,
        )

    def focus_next_panel(self) -> None:
        """Move focus to the next panel."""

        self._focus_relative_panel(1)

    def focus_previous_panel(self) -> None:
        """Move focus to the previous panel."""

        self._focus_relative_panel(-1)

    def _snapshot_layout_state(self) -> tuple[PanelRows, TabsState]:
        """Capture mutable layout rows and serialized tab state."""

        return deepcopy(self.window.layout_rows), serialize_window_tabs_state(
            self.window
        )

    def _active_panel_position(self, rows: PanelRows) -> tuple[int, int] | None:
        """Return the current active panel position within the provided rows."""

        active_panel_id = self.window.active_panel_id
        if active_panel_id is None:
            return None
        row_index, column_index = self.window.layout_coordinator.find_panel_position(
            active_panel_id,
            rows,
        )
        if row_index is None or column_index is None:
            return None
        return row_index, column_index

    def _resolved_seed_path(self, source_path: Path) -> Path:
        """Resolve the preferred seed path for newly created panel tabs."""

        return self.window.preferences_coordinator.resolve_new_context_path(source_path)

    def _allocate_panel_state(
        self,
        rows: PanelRows,
        tabs_state: TabsState,
        seed_path: Path,
    ) -> tuple[int, PanelState]:
        """Allocate a new panel identifier and its seeded default state."""

        new_panel_id = self.window.layout_coordinator.allocate_panel_id(
            rows,
            tabs_state,
        )
        return (
            new_panel_id,
            self.window.layout_coordinator.new_panel_state(new_panel_id, seed_path),
        )

    def _clone_panel_state(self, source_state: PanelState, panel_id: int) -> PanelState:
        """Clone persisted panel state while assigning a new panel identifier."""

        cloned_state = deepcopy(source_state)
        cloned_state["panel_id"] = panel_id
        return cloned_state

    def _add_split_panel_states(
        self,
        *,
        rows: PanelRows,
        tabs_state: TabsState,
        orientation: Qt.Orientation,
        row_index: int,
        column_index: int,
        seed_path: Path,
    ) -> int | None:
        """Insert seeded panels for a split operation and return the new focus."""

        if orientation == Qt.Orientation.Horizontal:
            new_panel_id, panel_state = self._allocate_panel_state(
                rows,
                tabs_state,
                seed_path,
            )
            rows[row_index].insert(column_index + 1, new_panel_id)
            tabs_state[new_panel_id] = panel_state
            return new_panel_id

        new_row: list[int] = []
        for _source_panel_id in rows[row_index]:
            new_panel_id, panel_state = self._allocate_panel_state(
                rows,
                tabs_state,
                seed_path,
            )
            new_row.append(new_panel_id)
            tabs_state[new_panel_id] = panel_state
        rows.insert(row_index + 1, new_row)
        return new_row[0] if new_row else None

    def _add_cloned_panel_states(
        self,
        *,
        rows: PanelRows,
        tabs_state: TabsState,
        orientation: Qt.Orientation,
        row_index: int,
        column_index: int,
        source_state: PanelState,
    ) -> int | None:
        """Insert cloned panels for a split operation and return the new focus."""

        if orientation == Qt.Orientation.Horizontal:
            new_panel_id = self.window.layout_coordinator.allocate_panel_id(
                rows,
                tabs_state,
            )
            rows[row_index].insert(column_index + 1, new_panel_id)
            tabs_state[new_panel_id] = self._clone_panel_state(
                source_state,
                new_panel_id,
            )
            return new_panel_id

        new_row: list[int] = []
        for source_panel_id in list(rows[row_index]):
            source_panel_state = tabs_state.get(
                source_panel_id
            ) or self.window.layout_coordinator.default_panel_state(source_panel_id)
            new_panel_id = self.window.layout_coordinator.allocate_panel_id(
                rows,
                tabs_state,
            )
            new_row.append(new_panel_id)
            tabs_state[new_panel_id] = self._clone_panel_state(
                source_panel_state,
                new_panel_id,
            )
        rows.insert(row_index + 1, new_row)
        return new_row[0] if new_row else None

    def _apply_layout_change(
        self,
        *,
        rows: PanelRows,
        tabs_state: TabsState,
        preferred_active_panel: int | None,
    ) -> None:
        """Persist new rows and rebuild panel widgets from the updated layout."""

        self.window.layout_rows = self.window.layout_coordinator.normalize_rows(rows)
        self.window.layout_coordinator.sync_panel_tree_from_rows()
        self.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
        )

    def _focus_relative_panel(self, step: int) -> None:
        """Move focus forward or backward through ordered panels."""

        ordered = WindowLayoutCoordinator.ordered_panel_ids(self.window.layout_rows)
        if not ordered:
            return
        if self.window.active_panel_id in ordered:
            current = ordered.index(self.window.active_panel_id)
            next_index = (current + step) % len(ordered)
        else:
            next_index = 0
        _activate_panel_and_focus(self, ordered[next_index])

    def _panel_activated_callback(self, panel_id: int) -> Callable[[], None]:
        """Build the callback used when a panel becomes active."""

        def _handle_activated() -> None:
            self.set_active_panel(panel_id)

        return _handle_activated

    def _panel_empty_callback(self, panel_id: int) -> Callable[[], None]:
        """Build the callback used when a panel loses its last tab."""

        def _handle_empty() -> None:
            self.close_panel_by_id(panel_id)

        return _handle_empty

    def panel_closed_tab_callback(self, panel_id: int) -> Callable[[str], None]:
        """Build the callback used when a panel closes a tab."""

        def _handle_tab_closed(path: str) -> None:
            self._remember_closed_tab({"path": str(path), "panel_id": panel_id})

        return _handle_tab_closed

    def _remember_closed_tab(self, entry: ClosedTabState) -> None:
        """Push one closed tab onto the bounded recently closed history."""

        deduplicated = [
            item
            for item in self.window.recently_closed_tabs
            if not (
                item["path"] == entry["path"] and item["panel_id"] == entry["panel_id"]
            )
        ]
        self.window.recently_closed_tabs = [entry, *deduplicated][
            : self.CLOSED_TAB_HISTORY_LIMIT
        ]

    def _group_choice_labels(
        self,
        choices: list[tuple[str, str]],
    ) -> list[str]:
        """Build stable prompt labels for a set of tab-group choices."""

        title_counts: dict[str, int] = {}
        for _group_id, title in choices:
            title_counts[title] = title_counts.get(title, 0) + 1

        labels: list[str] = []
        for group_id, title in choices:
            if title_counts[title] > 1:
                labels.append(f"{title} [{group_id[:6]}]")
            else:
                labels.append(title)
        return labels
