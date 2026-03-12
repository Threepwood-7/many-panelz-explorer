from __future__ import annotations

import uuid
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from threep_commons.qt.widget_identity import assign_widget_identity

from . import widget_naming
from ._context import ContextMenuController
from .byte_formatting import ByteFormatPreferences, ByteFormatScopeConfig, format_bytes
from .panel_tree import (
    ORIENTATION_HORIZONTAL,
    LeafNode,
    PanelTreeModel,
    SplitNode,
)
from .panel_widget import PanelWidget
from .ui.window import (
    WindowLayoutCoordinator,
    WindowOperationsCoordinator,
    WindowPersistenceCoordinator,
    WindowStatusCoordinator,
    WindowUiComposer,
)

if TYPE_CHECKING:
    from ._operations.types import OperationRequest
    from ._settings.manager import SettingsManager
    from ._settings.models import UiPreferences
    from .app_controller import AppController


type PanelState = dict[str, Any]
type TabsState = dict[int, PanelState]
type PanelRows = list[list[int]]
type RootsProvider = Callable[[Path | None], list[Path]]
type ConflictChoice = Literal["overwrite", "skip", "rename", "cancel"]


class ExplorerWindow(QMainWindow):
    window_activated = Signal()
    request_new_window = Signal()

    def __init__(
        self,
        controller: AppController,
        settings: SettingsManager,
        window_id: str | None = None,
        initial_path: Path | None = None,
        roots_provider: RootsProvider | None = None,
    ) -> None:
        super().__init__(None)
        self.controller = controller
        self.settings = settings
        self.window_id = window_id or uuid.uuid4().hex
        self._initial_path = initial_path or Path.home()
        self._roots_provider = roots_provider
        self._active_panel_id: int | None = None
        self._last_non_source_panel_id: int | None = None
        self._show_widget_map = False

        self.panel_tree = PanelTreeModel()
        self._layout_coordinator = WindowLayoutCoordinator(self)
        self._status_coordinator = WindowStatusCoordinator(self)
        self._operations_coordinator = WindowOperationsCoordinator(self)
        self._persistence_coordinator = WindowPersistenceCoordinator(self)
        self._ui_composer = WindowUiComposer(self)
        self._context_menu_controller: ContextMenuController | None = None

        self._layout_rows: PanelRows = self._rows_from_tree(self.panel_tree.root)
        self.panel_widgets: dict[int, PanelWidget] = {}

        self._central = QWidget(self)
        self._central_layout = QVBoxLayout(self._central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self._central)

        ui_preferences = self.settings.ui_preferences()
        self._new_context_mode = ui_preferences.new_context_mode
        self._show_hidden = ui_preferences.show_hidden_default
        self._show_root_dropdown = ui_preferences.show_root_dropdown
        self._show_storage_overview_status_row = (
            ui_preferences.show_storage_overview_status_row
        )
        self._column_width_auto_align_mode = ui_preferences.column_width_auto_align_mode
        self._show_refresh_button = ui_preferences.show_refresh_button
        self._show_root_buttons = ui_preferences.show_root_buttons
        self._show_address_bar = ui_preferences.show_address_bar
        self._show_navigation_buttons = ui_preferences.show_navigation_buttons
        self._byte_format_preferences = self._build_byte_format_preferences(
            ui_preferences
        )
        self._status_bar_storage_label_template = (
            ui_preferences.status_bar_storage_label_template
        )
        self._app_font_family = ui_preferences.app_font_family
        self._app_font_size_pt = ui_preferences.app_font_size_pt
        self._file_list_use_app_font = ui_preferences.file_list_use_app_font
        self._file_list_font_family = ui_preferences.file_list_font_family
        self._file_list_font_size_pt = ui_preferences.file_list_font_size_pt
        self._navigation_use_app_font = ui_preferences.navigation_use_app_font
        self._navigation_font_family = ui_preferences.navigation_font_family
        self._navigation_font_size_pt = ui_preferences.navigation_font_size_pt
        self._context_immediate_child_scan_cap = (
            ui_preferences.context_immediate_child_scan_cap
        )
        self._context_tool_code_editor_exe_path = (
            ui_preferences.context_tool_code_editor_exe_path
        )
        self._context_tool_code_editor_args_template = (
            ui_preferences.context_tool_code_editor_args_template
        )
        self._context_tool_git_gui_exe_path = (
            ui_preferences.context_tool_git_gui_exe_path
        )
        self._context_tool_git_gui_args_template = (
            ui_preferences.context_tool_git_gui_args_template
        )
        self._active_panel_tint_color_hex = ui_preferences.active_panel_tint_color_hex
        self._active_panel_tint_intensity_percent = (
            ui_preferences.active_panel_tint_intensity_percent
        )
        self._target_panel_tint_color_hex = ui_preferences.target_panel_tint_color_hex
        self._target_panel_tint_intensity_percent = (
            ui_preferences.target_panel_tint_intensity_percent
        )
        self._default_copy_move_backend = ui_preferences.default_copy_move_backend
        self._default_delete_backend = ui_preferences.default_delete_backend
        self._default_operation_dispatch_mode = (
            ui_preferences.default_operation_dispatch_mode
        )
        self._default_operation_conflict_policy = (
            ui_preferences.default_operation_conflict_policy
        )
        self._operation_shortcut_behavior = ui_preferences.operation_shortcut_behavior
        self._operation_queue_view_mode = ui_preferences.operation_queue_view_mode

        self._build_actions()
        self._build_menus()
        self._context_menu_controller = ContextMenuController(self, self._context_menu)
        self._build_shortcuts()
        self._build_operation_queue_widgets()
        self._status_coordinator.set_storage_bytes_formatter(
            self._format_status_bar_bytes
        )
        self._status_coordinator.set_storage_label_template(
            self._status_bar_storage_label_template
        )
        self._status_coordinator.set_storage_overview_enabled(
            self._show_storage_overview_status_row
        )
        self.controller.operation_queue_manager.job_updated.connect(
            self._on_operation_job_updated
        )

        self.setWindowTitle("Many Panelz Explorer")
        window_widget_id = widget_naming.window_widget_id(self.window_id)
        assign_widget_identity(
            self,
            widget_id=window_widget_id,
            widget_alias="window",
        )
        self.setWindowFlag(Qt.WindowType.Window, True)

        empty_state: TabsState = {}
        self._sync_panel_tree_from_rows()
        self._rebuild_from_tree(tabs_state=empty_state, preferred_active_panel=None)
        self._apply_operation_queue_visibility()
        self._refresh_context_menu()

    # ----- public API -----
    def split_active_panel(self, orientation: Qt.Orientation) -> None:
        active_panel = self.active_panel()
        if self._active_panel_id is None or active_panel is None:
            return

        tabs_state = self._serialize_tabs_state()
        rows = deepcopy(self._layout_rows)
        row_index, column_index = self._find_panel_position(self._active_panel_id, rows)
        if row_index is None or column_index is None:
            return

        seed_path = self._resolve_new_context_path(active_panel.current_path())
        preferred_active_panel: int | None = None
        is_horizontal_split = (
            orientation == Qt.Orientation.Horizontal
            or orientation == ORIENTATION_HORIZONTAL
        )
        if is_horizontal_split:
            # New vertical pane: mutate only active row.
            new_panel_id = self._allocate_panel_id(rows, tabs_state)
            rows[row_index].insert(column_index + 1, new_panel_id)
            tabs_state[new_panel_id] = self._new_panel_state(new_panel_id, seed_path)
            preferred_active_panel = new_panel_id
        else:
            # New horizontal pane: create full-width row mirroring active row shape.
            source_row = rows[row_index]
            new_row: list[int] = []
            for _source_panel_id in source_row:
                new_panel_id = self._allocate_panel_id(rows, tabs_state)
                new_row.append(new_panel_id)
                tabs_state[new_panel_id] = self._new_panel_state(
                    new_panel_id, seed_path
                )
            rows.insert(row_index + 1, new_row)
            preferred_active_panel = new_row[0] if new_row else None

        self._layout_rows = self._normalize_rows(rows)
        self._sync_panel_tree_from_rows()
        self._rebuild_from_tree(
            tabs_state=tabs_state, preferred_active_panel=preferred_active_panel
        )

    def new_tab_in_active_panel(self) -> None:
        panel = self.active_panel()
        if panel is None:
            return
        seed_path = self._resolve_new_context_path(panel.current_path())
        panel.add_tab(seed_path)

    def clone_active_panel(self, orientation: Qt.Orientation) -> None:
        if self._active_panel_id is None:
            return

        tabs_state = self._serialize_tabs_state()
        rows = deepcopy(self._layout_rows)
        row_index, column_index = self._find_panel_position(self._active_panel_id, rows)
        if row_index is None or column_index is None:
            return

        source_state = tabs_state.get(
            self._active_panel_id
        ) or self._default_panel_state(self._active_panel_id)
        preferred_active_panel: int | None = None

        is_horizontal_split = (
            orientation == Qt.Orientation.Horizontal
            or orientation == ORIENTATION_HORIZONTAL
        )
        if is_horizontal_split:
            # Clone vertically: duplicate active pane state in current row.
            new_panel_id = self._allocate_panel_id(rows, tabs_state)
            rows[row_index].insert(column_index + 1, new_panel_id)
            cloned_state = cast("PanelState", deepcopy(source_state))
            cloned_state["panel_id"] = new_panel_id
            tabs_state[new_panel_id] = cloned_state
            preferred_active_panel = new_panel_id
        else:
            # Clone horizontally: duplicate full active row with per-column state.
            source_row = list(rows[row_index])
            new_row: list[int] = []
            for source_panel_id in source_row:
                source_panel_state = tabs_state.get(
                    source_panel_id
                ) or self._default_panel_state(source_panel_id)
                new_panel_id = self._allocate_panel_id(rows, tabs_state)
                new_row.append(new_panel_id)
                cloned_state = cast("PanelState", deepcopy(source_panel_state))
                cloned_state["panel_id"] = new_panel_id
                tabs_state[new_panel_id] = cloned_state
            rows.insert(row_index + 1, new_row)
            preferred_active_panel = new_row[0] if new_row else None

        self._layout_rows = self._normalize_rows(rows)
        self._sync_panel_tree_from_rows()
        self._rebuild_from_tree(
            tabs_state=tabs_state, preferred_active_panel=preferred_active_panel
        )

    def close_active_tab(self) -> None:
        panel = self.active_panel()
        if panel is None:
            return
        panel.close_current_tab()
        if panel.tab_count() == 0:
            self._close_panel_by_id(panel.panel_id)

    def close_active_panel(self) -> None:
        if self._active_panel_id is None:
            return
        self._close_panel_by_id(self._active_panel_id)

    def clone_current_window(self) -> None:
        new_window = self.controller.new_window(from_window=self, show=False)
        new_window.apply_cloned_state(self.serialize_state())
        new_window.show()

    def save_view(self) -> None:
        name, ok = QInputDialog.getText(self, "Save View", "View name:")
        if not ok:
            return
        view_name = name.strip()
        if not view_name:
            return

        if self.settings.get_saved_view(view_name) is not None:
            overwrite = QMessageBox.question(
                self,
                "Save View",
                f'View "{view_name}" already exists. Overwrite?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if overwrite != QMessageBox.StandardButton.Yes:
                return

        self.settings.set_saved_view(
            view_name, self.serialize_state(include_geometry=True)
        )
        self.settings.sync()

    def restore_view(self) -> None:
        view_state = self._prompt_saved_view("Restore View")
        if view_state is None:
            return
        self._restore_view_state(view_state)

    def restore_view_named(self, view_name: str) -> None:
        payload = self.settings.get_saved_view(view_name)
        if payload is None:
            QMessageBox.warning(
                self, "Restore View", f'View "{view_name}" was not found.'
            )
            return
        self._restore_view_state(payload)

    def _restore_view_state(self, view_state: dict[str, Any]) -> None:
        new_window = self.controller.new_window(from_window=self, show=False)
        new_window.apply_cloned_state(view_state, restore_geometry=True)
        new_window.show()

    def replace_view(self) -> None:
        view_state = self._prompt_saved_view("Replace View")
        if view_state is None:
            return
        self.apply_cloned_state(view_state, restore_geometry=True)

    def set_on_top(self, enabled: bool) -> None:
        on_top = bool(enabled)
        with QSignalBlocker(self._on_top_action):
            self._on_top_action.setChecked(on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.show()

    @property
    def roots_provider(self) -> RootsProvider | None:
        return self._roots_provider

    # ----- QWidget/QWindow events -----
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowActivate:
            self.window_activated.emit()
            self._refresh_context_menu()
        return super().event(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.controller.close_window(self)
        super().closeEvent(event)

    # ----- UI composition -----
    def _build_actions(self) -> None:
        self._ui_composer.build_actions()

    def _build_shortcuts(self) -> None:
        self._ui_composer.build_shortcuts()

    def _build_menus(self) -> None:
        self._ui_composer.build_menus()

    def _build_operation_queue_widgets(self) -> None:
        self._ui_composer.build_operation_queue_widgets()

    def _toggle_queue_dock(self, enabled: bool) -> None:
        self._queue_dock.setVisible(bool(enabled))

    def _on_queue_dock_visibility_changed(self, visible: bool) -> None:
        with QSignalBlocker(self._show_queue_dock_action):
            self._show_queue_dock_action.setChecked(bool(visible))

    def _apply_operation_queue_visibility(self) -> None:
        self._ui_composer.apply_operation_queue_visibility()

    def _on_operation_job_updated(self, job_obj: object) -> None:
        job = cast("object", job_obj)
        if not hasattr(job, "request") or not hasattr(job, "status"):
            return
        request = cast("Any", job).request
        created_by = str(getattr(request, "created_by", ""))
        if not created_by.startswith(f"window:{self.window_id}"):
            return
        status = str(getattr(job, "status", ""))
        if status not in {"succeeded", "failed", "cancelled"}:
            return
        panel = self.active_panel()
        if panel is not None:
            panel.refresh_current_path()
        target_id = (
            self._resolve_target_panel_id(self._active_panel_id)
            if self._active_panel_id is not None
            else None
        )
        if target_id is not None:
            target_panel = self.panel_widgets.get(target_id)
            if target_panel is not None:
                target_panel.refresh_current_path()

    def _focus_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        menu_bar.setActiveAction(self._menu_file_action)

    def _refresh_active_panel(self) -> None:
        panel = self.active_panel()
        if panel is not None:
            panel.refresh_current_path()

    def _align_columns_current_panel_tabs(self) -> None:
        panel = self.active_panel()
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is None:
            return
        widths = list(tab.columns.widths)
        panel.apply_column_widths_to_panel_tabs(widths, source_tab=tab)
        self.statusBar().showMessage("Aligned columns in current panel tabs.", 2000)

    def _align_columns_all_panels_tabs(self) -> None:
        panel = self.active_panel()
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is None:
            return
        widths = list(tab.columns.widths)
        self.controller.broadcast_column_widths(
            widths,
            source_window=self,
            source_panel_id=panel.panel_id,
            source_tab=tab,
        )
        self.statusBar().showMessage("Aligned columns in all panels and tabs.", 2000)

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "Help",
            "Keyboard shortcuts:\n"
            "F5: Copy to target pane\n"
            "F6: Move to target pane\n"
            "F8: Delete selection\n"
            "Tab / Shift+Tab: Switch active pane\n"
            "Ctrl+, : Open settings\n"
            "Alt or F10: Focus main menu\n"
            "Ctrl+Q / Alt+X: Exit application",
        )

    def _open_settings_dialog(self) -> None:
        from .dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(controller=self.controller, parent=self)
        dialog.exec()

    def _populate_restore_view_menu(self) -> None:
        self._restore_view_menu.clear()
        names = self.settings.list_saved_views()
        if not names:
            empty_action = self._restore_view_menu.addAction("(N&o saved views)")
            empty_action.setEnabled(False)
            return

        for view_name in names:
            action = self._restore_view_menu.addAction(view_name.replace("&", "&&"))
            action.triggered.connect(
                lambda _checked=False, name=view_name: self.restore_view_named(name)
            )

    def _quit_application(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _clear_layout(self) -> None:
        while self._central_layout.count() > 0:
            item = self._central_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _rebuild_from_tree(
        self,
        tabs_state: TabsState,
        preferred_active_panel: int | None,
    ) -> None:
        normalized_rows = self._normalize_rows(self._layout_rows)
        panel_ids = self._ordered_panel_ids(normalized_rows)
        if not panel_ids:
            normalized_rows = [[1]]
            panel_ids = [1]

        self._layout_rows = normalized_rows
        self._sync_panel_tree_from_rows()

        new_panel_widgets: dict[int, PanelWidget] = {}
        file_list_font, navigation_font = self._effective_panel_fonts()
        for panel_id in panel_ids:
            panel_state = tabs_state.get(panel_id)
            panel = PanelWidget(
                panel_id=panel_id,
                default_path=self._resolve_new_context_path(self._initial_path),
                show_hidden=self._show_hidden,
                show_root_dropdown=self._show_root_dropdown,
                file_list_size_formatter=self._format_file_list_bytes,
                properties_size_formatter=self._format_properties_bytes,
                roots_provider=self._roots_provider,
                parent=self,
            )
            panel.activated.connect(lambda pid=panel_id: self._set_active_panel(pid))
            panel.current_context_changed.connect(self._update_pane_visuals)
            panel.column_widths_sync_requested.connect(
                lambda widths, source_tab, pid=panel_id: (
                    self._on_panel_column_widths_sync_requested(pid, widths, source_tab)
                )
            )
            panel.became_empty.connect(
                lambda pid=panel_id: self._close_panel_by_id(pid)
            )
            panel.set_column_width_auto_align_mode(self._column_width_auto_align_mode)

            if isinstance(panel_state, dict):
                panel.restore_state(panel_state)
            else:
                panel.add_tab(self._resolve_new_context_path(self._initial_path))

            panel.set_role_visual_preferences(
                active_color_hex=self._active_panel_tint_color_hex,
                active_intensity_percent=self._active_panel_tint_intensity_percent,
                target_color_hex=self._target_panel_tint_color_hex,
                target_intensity_percent=self._target_panel_tint_intensity_percent,
            )
            panel.apply_toolbar_visibility(
                show_refresh_button=self._show_refresh_button,
                show_root_buttons=self._show_root_buttons,
                show_root_dropdown=self._show_root_dropdown,
                show_address_bar=self._show_address_bar,
                show_navigation_buttons=self._show_navigation_buttons,
            )
            panel.apply_font_preferences(
                file_list_font=file_list_font,
                navigation_font=navigation_font,
            )
            panel.set_widget_map_enabled(self._show_widget_map)
            new_panel_widgets[panel_id] = panel

        self.panel_widgets = new_panel_widgets

        root_widget = self._build_rows_widget(self._layout_rows)
        if root_widget is None:
            root_widget = QWidget()

        self._clear_layout()
        self._central_layout.addWidget(root_widget)

        target_active = preferred_active_panel
        if target_active is None or target_active not in self.panel_widgets:
            target_active = next(iter(self.panel_widgets), None)
        if target_active is not None:
            self._set_active_panel(target_active)
        else:
            self._update_pane_visuals()

    def _build_rows_widget(self, rows: PanelRows) -> QWidget | None:
        if not rows:
            return None
        if len(rows) == 1:
            return self._build_row_widget(rows[0])

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        for row in rows:
            row_widget = self._build_row_widget(row)
            splitter.addWidget(row_widget if row_widget is not None else QWidget())
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([1000] * len(rows))
        return splitter

    def _build_row_widget(self, row: list[int]) -> QWidget | None:
        if not row:
            return None
        if len(row) == 1:
            panel = self.panel_widgets.get(row[0])
            return panel if panel is not None else QWidget()

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        for panel_id in row:
            panel = self.panel_widgets.get(panel_id)
            splitter.addWidget(panel if panel is not None else QWidget())
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([1000] * len(row))
        return splitter

    def _set_active_panel(self, panel_id: int) -> None:
        if panel_id not in self.panel_widgets:
            return
        previous = self._active_panel_id
        if (
            previous is not None
            and previous != panel_id
            and previous in self.panel_widgets
        ):
            self._last_non_source_panel_id = previous
        self._active_panel_id = panel_id
        self._update_pane_visuals()

    def active_panel(self) -> PanelWidget | None:
        if self._active_panel_id is None:
            return None
        return self.panel_widgets.get(self._active_panel_id)

    def _close_panel_by_id(self, panel_id: int) -> None:
        if panel_id not in self.panel_widgets:
            return

        tabs_state = self._serialize_tabs_state()
        rows = deepcopy(self._layout_rows)
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
        if panel_id == self._last_non_source_panel_id:
            self._last_non_source_panel_id = None
        if panel_id == self._active_panel_id:
            self._active_panel_id = None

        if not new_rows:
            self.close()
            return

        self._layout_rows = self._normalize_rows(new_rows)
        self._sync_panel_tree_from_rows()
        ordered = self._ordered_panel_ids(self._layout_rows)
        preferred = ordered[0] if ordered else None
        self._rebuild_from_tree(tabs_state=tabs_state, preferred_active_panel=preferred)

    def _serialize_tabs_state(self) -> TabsState:
        return {
            panel_id: panel.serialize_state()
            for panel_id, panel in self.panel_widgets.items()
        }

    def apply_ui_preferences(self, preferences: UiPreferences) -> None:
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
        self._context_immediate_child_scan_cap = int(
            preferences.context_immediate_child_scan_cap
        )
        self._context_tool_code_editor_exe_path = (
            preferences.context_tool_code_editor_exe_path
        )
        self._context_tool_code_editor_args_template = (
            preferences.context_tool_code_editor_args_template
        )
        self._context_tool_git_gui_exe_path = preferences.context_tool_git_gui_exe_path
        self._context_tool_git_gui_args_template = (
            preferences.context_tool_git_gui_args_template
        )
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

        with QSignalBlocker(self._show_hidden_action):
            self._show_hidden_action.setChecked(self._show_hidden)

        file_list_font, navigation_font = self._effective_panel_fonts()
        for panel in self.panel_widgets.values():
            panel.set_show_hidden(self._show_hidden)
            panel.apply_toolbar_visibility(
                show_refresh_button=self._show_refresh_button,
                show_root_buttons=self._show_root_buttons,
                show_root_dropdown=self._show_root_dropdown,
                show_address_bar=self._show_address_bar,
                show_navigation_buttons=self._show_navigation_buttons,
            )
            panel.set_column_width_auto_align_mode(self._column_width_auto_align_mode)
            panel.apply_font_preferences(
                file_list_font=file_list_font,
                navigation_font=navigation_font,
            )
            panel.apply_size_formatters(
                file_list_size_formatter=self._format_file_list_bytes,
                properties_size_formatter=self._format_properties_bytes,
            )
            panel.set_role_visual_preferences(
                active_color_hex=self._active_panel_tint_color_hex,
                active_intensity_percent=self._active_panel_tint_intensity_percent,
                target_color_hex=self._target_panel_tint_color_hex,
                target_intensity_percent=self._target_panel_tint_intensity_percent,
            )
        self._apply_operation_queue_visibility()
        self._status_coordinator.set_storage_bytes_formatter(
            self._format_status_bar_bytes
        )
        self._status_coordinator.set_storage_label_template(
            self._status_bar_storage_label_template
        )
        self._status_coordinator.set_storage_overview_enabled(
            self._show_storage_overview_status_row
        )
        self._update_pane_visuals()

    def _effective_panel_fonts(self) -> tuple[QFont, QFont]:
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

    def _build_byte_format_preferences(
        self,
        preferences: UiPreferences,
    ) -> ByteFormatPreferences:
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
        preferences = self._byte_format_preferences
        return format_bytes(
            value,
            scope_config,
            (preferences.thousands_sep, preferences.decimal_sep),
        )

    def _format_file_list_bytes(self, value: int) -> str:
        return self._format_bytes_for_scope(
            value, self._byte_format_preferences.file_list
        )

    def _format_status_bar_bytes(self, value: int) -> str:
        return self._format_bytes_for_scope(
            value, self._byte_format_preferences.status_bar
        )

    def _format_properties_bytes(self, value: int) -> str:
        return self._format_bytes_for_scope(
            value, self._byte_format_preferences.properties
        )

    def _resolve_new_context_path(self, active_path: Path | None) -> Path:
        mode = self._new_context_mode.strip().lower()
        if mode == "home":
            return Path.home()
        if mode == "cwd":
            return Path.cwd()
        if active_path is not None:
            return Path(active_path)
        return Path.home()

    def _toggle_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        self.settings.show_hidden_default = self._show_hidden
        for panel in self.panel_widgets.values():
            panel.set_show_hidden(self._show_hidden)

    def _toggle_show_widget_map(self, enabled: bool) -> None:
        self._show_widget_map = bool(enabled)
        for panel in self.panel_widgets.values():
            panel.set_widget_map_enabled(self._show_widget_map)

    def _prompt_saved_view(self, title: str) -> dict[str, Any] | None:
        names = self.settings.list_saved_views()
        if not names:
            QMessageBox.information(self, title, "No saved views.")
            return None

        selected_raw, ok = QInputDialog.getItem(
            self, title, "Select a saved view:", names, 0, False
        )
        selected = str(selected_raw).strip()
        if not ok or not selected:
            return None

        payload = self.settings.get_saved_view(selected)
        if payload is None:
            QMessageBox.warning(self, title, f'View "{selected}" was not found.')
            return None
        return payload

    def _focus_next_panel(self) -> None:
        ordered = self._ordered_panel_ids(self._layout_rows)
        if not ordered:
            return
        if self._active_panel_id in ordered:
            current = ordered.index(cast("int", self._active_panel_id))
            next_index = (current + 1) % len(ordered)
        else:
            next_index = 0
        self._activate_panel_and_focus(ordered[next_index])

    def _focus_previous_panel(self) -> None:
        ordered = self._ordered_panel_ids(self._layout_rows)
        if not ordered:
            return
        if self._active_panel_id in ordered:
            current = ordered.index(cast("int", self._active_panel_id))
            next_index = (current - 1) % len(ordered)
        else:
            next_index = 0
        self._activate_panel_and_focus(ordered[next_index])

    def _activate_panel_and_focus(self, panel_id: int) -> None:
        self._set_active_panel(panel_id)
        panel = self.panel_widgets.get(panel_id)
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is not None:
            tab.view.setFocus()

    def _copy_selected_to_target(self, configure: bool = False) -> None:
        self._operations_coordinator.copy_selected_to_target(configure=configure)

    def _move_selected_to_target(self, configure: bool = False) -> None:
        self._operations_coordinator.move_selected_to_target(configure=configure)

    def _delete_selected_items(self, configure: bool = False) -> None:
        self._operations_coordinator.delete_selected_items(configure=configure)

    def _transfer_selected_to_target(
        self, *, move: bool, configure: bool = False
    ) -> None:
        self._operations_coordinator.transfer_selected_to_target(
            move=move,
            configure=configure,
        )

    def _build_operation_request(
        self,
        *,
        kind: str,
        sources: list[Path],
        target_dir: Path | None,
        configure: bool,
    ) -> OperationRequest | None:
        return self._operations_coordinator.build_operation_request(
            kind=kind,
            sources=sources,
            target_dir=target_dir,
            configure=configure,
        )

    def _copy_or_move_one(
        self, *, source: Path, destination_dir: Path, move: bool
    ) -> Literal["done", "skip", "cancel"]:
        return self._operations_coordinator.copy_or_move_one(
            source=source,
            destination_dir=destination_dir,
            move=move,
        )

    def _prompt_conflict_resolution(
        self, source: Path, destination: Path
    ) -> ConflictChoice:
        return self._operations_coordinator.prompt_conflict_resolution(
            source,
            destination,
        )

    def _next_available_path(self, destination_dir: Path, base_name: str) -> Path:
        return self._operations_coordinator.next_available_path(
            destination_dir=destination_dir,
            base_name=base_name,
        )

    def _remove_existing_path(self, path: Path) -> None:
        self._operations_coordinator.remove_existing_path(path)

    def _resolve_target_panel_id(self, source_panel_id: int) -> int | None:
        ordered = self._ordered_panel_ids(self._layout_rows)
        candidates = [pid for pid in ordered if pid != source_panel_id]
        if not candidates:
            return None
        if self._last_non_source_panel_id in candidates:
            return self._last_non_source_panel_id
        return candidates[0]

    def _on_panel_column_widths_sync_requested(
        self,
        panel_id: int,
        widths: list[object],
        source_tab: object,
    ) -> None:
        self.controller.broadcast_column_widths(
            widths,
            source_window=self,
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
        _ = source_panel_id, source_tab
        for panel_id, panel in self.panel_widgets.items():
            _ = panel_id
            panel.apply_column_widths_to_panel_tabs(widths)

    def _update_pane_visuals(self) -> None:
        self._status_coordinator.update_pane_visuals()
        self._refresh_context_menu()

    def _refresh_context_menu(self) -> None:
        if self._context_menu_controller is None:
            return
        self._context_menu_controller.rebuild()

    def _set_persistent_path_status(
        self, *, source_id: int | None, target_id: int | None
    ) -> None:
        self._status_coordinator.set_persistent_path_status(
            source_id=source_id,
            target_id=target_id,
        )

    def _panel_path_text(self, panel_id: int | None) -> str:
        return self._status_coordinator.panel_path_text(panel_id)

    # ----- persistence -----
    def _encode_geometry(self) -> str:
        return self._persistence_coordinator.encode_geometry()

    def _restore_geometry_from_b64(self, encoded: str) -> None:
        self._persistence_coordinator.restore_geometry_from_b64(encoded)

    def serialize_state(self, *, include_geometry: bool = False) -> dict[str, Any]:
        return self._persistence_coordinator.serialize_state(
            include_geometry=include_geometry
        )

    def save_to_settings(self) -> None:
        self._persistence_coordinator.save_to_settings()

    def restore_from_settings(self) -> None:
        self._persistence_coordinator.restore_from_settings()

    def apply_cloned_state(
        self, state: dict[str, Any], *, restore_geometry: bool = False
    ) -> None:
        self._persistence_coordinator.apply_cloned_state(
            state,
            restore_geometry=restore_geometry,
        )

    def _new_panel_state(self, panel_id: int, seed_path: Path) -> PanelState:
        return self._layout_coordinator.new_panel_state(panel_id, seed_path)

    def _default_panel_state(self, panel_id: int) -> PanelState:
        return self._layout_coordinator.default_panel_state(panel_id)

    def _find_panel_position(
        self, panel_id: int, rows: PanelRows
    ) -> tuple[int | None, int | None]:
        return self._layout_coordinator.find_panel_position(panel_id, rows)

    def _allocate_panel_id(self, rows: PanelRows, tabs_state: TabsState) -> int:
        return self._layout_coordinator.allocate_panel_id(rows, tabs_state)

    @staticmethod
    def _ordered_panel_ids(rows: PanelRows) -> list[int]:
        return WindowLayoutCoordinator.ordered_panel_ids(rows)

    def _normalize_rows(self, rows: PanelRows) -> PanelRows:
        return self._layout_coordinator.normalize_rows(rows)

    def _append_missing_panel_ids(
        self, rows: PanelRows, panel_ids: list[int]
    ) -> PanelRows:
        return self._layout_coordinator.append_missing_panel_ids(rows, panel_ids)

    def _rows_from_tree(self, node: LeafNode | SplitNode | None) -> PanelRows:
        return self._layout_coordinator.rows_from_tree(node)

    def _sync_panel_tree_from_rows(self) -> None:
        self._layout_coordinator.sync_panel_tree_from_rows()

    def _build_tree_root_from_rows(
        self, rows: PanelRows
    ) -> LeafNode | SplitNode | None:
        return self._layout_coordinator.build_tree_root_from_rows(rows)

    def default_close_warning(self) -> bool:
        if len(self.panel_widgets) > 1:
            return True
        panel = self.active_panel()
        return panel is not None and panel.tab_count() > 1
