from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QFont, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from threep_commons.qt.widget_identity import assign_widget_identity

from . import widget_naming
from ._context import ContextMenuController
from .byte_formatting import ByteFormatPreferences, ByteFormatScopeConfig, format_bytes
from .panel_tree import (
    PanelTreeModel,
)
from .ui.window import (
    WindowLayoutCoordinator,
    WindowOperationsCoordinator,
    WindowPanelsCoordinator,
    WindowPersistenceCoordinator,
    WindowStatusCoordinator,
    WindowUiComposer,
)

if TYPE_CHECKING:
    from ._settings.manager import SettingsManager
    from ._settings.models import UiPreferences
    from .app_controller import AppController
    from .operation_queue_widgets import OperationQueuePanel
    from .panel_widget import PanelWidget


type PanelState = dict[str, Any]
type TabsState = dict[int, PanelState]
type PanelRows = list[list[int]]
type RootsProvider = Callable[[Path | None], list[Path]]


class ExplorerWindow(QMainWindow):
    window_activated = Signal()
    request_new_window = Signal()

    new_tab_action: QAction
    new_vertical_panel_action: QAction
    new_horizontal_panel_action: QAction
    clone_vertical_panel_action: QAction
    clone_horizontal_panel_action: QAction
    copy_to_target_action: QAction
    copy_to_target_configure_action: QAction
    move_to_target_action: QAction
    move_to_target_configure_action: QAction
    delete_selection_action: QAction
    delete_selection_configure_action: QAction
    new_window_action: QAction
    clone_window_action: QAction
    save_view_action: QAction
    restore_view_action: QAction
    replace_view_action: QAction
    close_tab_action: QAction
    close_panel_action: QAction
    close_window_action: QAction
    exit_action: QAction
    refresh_action: QAction
    on_top_action: QAction
    show_hidden_action: QAction
    show_widget_map_action: QAction
    align_columns_current_panel_tabs_action: QAction
    align_columns_all_panels_tabs_action: QAction
    show_queue_dock_action: QAction
    show_queue_window_action: QAction
    settings_action: QAction
    help_action: QAction
    restore_view_menu: QMenu
    context_menu: QMenu
    menu_file_action: QAction
    menu_view_action: QAction
    menu_context_action: QAction
    menu_help_action: QAction
    next_pane_shortcut: QShortcut
    previous_pane_shortcut: QShortcut
    menu_focus_shortcut: QShortcut
    queue_dock: QDockWidget
    queue_panel: OperationQueuePanel
    source_path_label: QLabel
    target_path_label: QLabel
    status_rows_host: QWidget
    status_paths_row: QWidget
    storage_overview_row: QWidget
    storage_entries_host: QWidget
    storage_entries_layout: QHBoxLayout
    storage_overview_labels: list[QLabel]

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
        self.layout_coordinator = WindowLayoutCoordinator(self)
        self.panels_coordinator = WindowPanelsCoordinator(self)
        self._status_coordinator = WindowStatusCoordinator(self)
        self.operations_coordinator = WindowOperationsCoordinator(self)
        self.persistence_coordinator = WindowPersistenceCoordinator(self)
        self._ui_composer = WindowUiComposer(self)
        self.context_menu_controller: ContextMenuController | None = None

        self._layout_rows: PanelRows = self.layout_coordinator.rows_from_tree(
            self.panel_tree.root
        )
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

        self._ui_composer.build_actions()
        self._ui_composer.build_menus()
        self.context_menu_controller = ContextMenuController(self, self.context_menu)
        self._ui_composer.build_shortcuts()
        self._ui_composer.build_operation_queue_widgets()
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
        self.layout_coordinator.sync_panel_tree_from_rows()
        self.panels_coordinator.rebuild_from_tree(
            tabs_state=empty_state,
            preferred_active_panel=None,
        )
        self._ui_composer.apply_operation_queue_visibility()
        self._refresh_context_menu()

    @property
    def show_hidden_enabled(self) -> bool:
        return self._show_hidden

    @property
    def show_widget_map_enabled(self) -> bool:
        return self._show_widget_map

    @property
    def active_panel_id(self) -> int | None:
        return self._active_panel_id

    @active_panel_id.setter
    def active_panel_id(self, panel_id: int | None) -> None:
        self._active_panel_id = panel_id

    @property
    def last_non_source_panel_id(self) -> int | None:
        return self._last_non_source_panel_id

    @last_non_source_panel_id.setter
    def last_non_source_panel_id(self, panel_id: int | None) -> None:
        self._last_non_source_panel_id = panel_id

    @property
    def layout_rows(self) -> PanelRows:
        return [list(row) for row in self._layout_rows]

    @layout_rows.setter
    def layout_rows(self, rows: PanelRows) -> None:
        self._layout_rows = [list(row) for row in rows]

    @property
    def show_storage_overview_enabled(self) -> bool:
        return self._show_storage_overview_status_row

    @property
    def initial_path(self) -> Path:
        return Path(self._initial_path)

    @property
    def show_root_dropdown_enabled(self) -> bool:
        return self._show_root_dropdown

    @property
    def show_refresh_button_enabled(self) -> bool:
        return self._show_refresh_button

    @property
    def show_root_buttons_enabled(self) -> bool:
        return self._show_root_buttons

    @property
    def show_address_bar_enabled(self) -> bool:
        return self._show_address_bar

    @property
    def show_navigation_buttons_enabled(self) -> bool:
        return self._show_navigation_buttons

    @property
    def column_width_auto_align_mode(self) -> str:
        return self._column_width_auto_align_mode

    @property
    def central_layout(self) -> QVBoxLayout:
        return self._central_layout

    @property
    def operation_queue_view_mode(self) -> str:
        return self._operation_queue_view_mode

    @property
    def operation_shortcut_behavior(self) -> str:
        return self._operation_shortcut_behavior

    @property
    def default_copy_move_backend(self) -> str:
        return self._default_copy_move_backend

    @property
    def default_delete_backend(self) -> str:
        return self._default_delete_backend

    @property
    def default_operation_dispatch_mode(self) -> str:
        return self._default_operation_dispatch_mode

    @property
    def default_operation_conflict_policy(self) -> str:
        return self._default_operation_conflict_policy

    def clone_current_window(self) -> None:
        new_window = self.controller.new_window(from_window=self, show=False)
        new_window.persistence_coordinator.apply_cloned_state(
            self.persistence_coordinator.serialize_state()
        )
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
            view_name,
            self.persistence_coordinator.serialize_state(include_geometry=True),
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
        new_window.persistence_coordinator.apply_cloned_state(
            view_state,
            restore_geometry=True,
        )
        new_window.show()

    def replace_view(self) -> None:
        view_state = self._prompt_saved_view("Replace View")
        if view_state is None:
            return
        self.persistence_coordinator.apply_cloned_state(
            view_state,
            restore_geometry=True,
        )

    def set_on_top(self, enabled: bool) -> None:
        on_top = bool(enabled)
        with QSignalBlocker(self.on_top_action):
            self.on_top_action.setChecked(on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.show()

    @property
    def roots_provider(self) -> RootsProvider | None:
        return self._roots_provider

    def panel_role_visual_preferences(self) -> tuple[str, int, str, int]:
        return (
            self._active_panel_tint_color_hex,
            self._active_panel_tint_intensity_percent,
            self._target_panel_tint_color_hex,
            self._target_panel_tint_intensity_percent,
        )

    def panel_toolbar_visibility_preferences(
        self,
    ) -> tuple[bool, bool, bool, bool, bool]:
        return (
            self._show_refresh_button,
            self._show_root_buttons,
            self._show_root_dropdown,
            self._show_address_bar,
            self._show_navigation_buttons,
        )

    # ----- QWidget/QWindow events -----
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowActivate:
            self.window_activated.emit()
            self._refresh_context_menu()
        return super().event(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.controller.close_window(self)
        super().closeEvent(event)

    def toggle_queue_dock(self, enabled: bool) -> None:
        self.queue_dock.setVisible(bool(enabled))

    def on_queue_dock_visibility_changed(self, visible: bool) -> None:
        with QSignalBlocker(self.show_queue_dock_action):
            self.show_queue_dock_action.setChecked(bool(visible))

    def _on_operation_job_updated(self, job_obj: object) -> None:
        job = job_obj
        if not hasattr(job, "request") or not hasattr(job, "status"):
            return
        request = cast("Any", job).request
        created_by = str(getattr(request, "created_by", ""))
        if not created_by.startswith(f"window:{self.window_id}"):
            return
        status = str(getattr(job, "status", ""))
        if status not in {"succeeded", "failed", "cancelled"}:
            return
        panel = self.panels_coordinator.active_panel()
        if panel is not None:
            panel.navigation_coordinator.refresh_current_path()
        target_id = (
            self.panels_coordinator.resolve_target_panel_id(self._active_panel_id)
            if self._active_panel_id is not None
            else None
        )
        if target_id is not None:
            target_panel = self.panel_widgets.get(target_id)
            if target_panel is not None:
                target_panel.navigation_coordinator.refresh_current_path()

    def focus_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        menu_bar.setActiveAction(self.menu_file_action)

    def show_help(self) -> None:
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

    def open_settings_dialog(self) -> None:
        from .dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(controller=self.controller, parent=self)
        dialog.exec()

    def populate_restore_view_menu(self) -> None:
        self.restore_view_menu.clear()
        names = self.settings.list_saved_views()
        if not names:
            empty_action = self.restore_view_menu.addAction("(N&o saved views)")
            empty_action.setEnabled(False)
            return

        for view_name in names:
            action = self.restore_view_menu.addAction(view_name.replace("&", "&&"))
            action.triggered.connect(
                lambda _checked=False, name=view_name: self.restore_view_named(name)
            )

    def quit_application(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

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

        with QSignalBlocker(self.show_hidden_action):
            self.show_hidden_action.setChecked(self._show_hidden)

        file_list_font, navigation_font = self.effective_panel_fonts()
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
                file_list_size_formatter=self.format_file_list_bytes,
                properties_size_formatter=self.format_properties_bytes,
            )
            panel.set_role_visual_preferences(
                active_color_hex=self._active_panel_tint_color_hex,
                active_intensity_percent=self._active_panel_tint_intensity_percent,
                target_color_hex=self._target_panel_tint_color_hex,
                target_intensity_percent=self._target_panel_tint_intensity_percent,
            )
        self._ui_composer.apply_operation_queue_visibility()
        self._status_coordinator.set_storage_bytes_formatter(
            self._format_status_bar_bytes
        )
        self._status_coordinator.set_storage_label_template(
            self._status_bar_storage_label_template
        )
        self._status_coordinator.set_storage_overview_enabled(
            self._show_storage_overview_status_row
        )
        self.update_pane_visuals()

    def effective_panel_fonts(self) -> tuple[QFont, QFont]:
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

    def format_file_list_bytes(self, value: int) -> str:
        return self._format_bytes_for_scope(
            value, self._byte_format_preferences.file_list
        )

    def _format_status_bar_bytes(self, value: int) -> str:
        return self._format_bytes_for_scope(
            value, self._byte_format_preferences.status_bar
        )

    def format_properties_bytes(self, value: int) -> str:
        return self._format_bytes_for_scope(
            value, self._byte_format_preferences.properties
        )

    def resolve_new_context_path(self, active_path: Path | None) -> Path:
        mode = self._new_context_mode.strip().lower()
        if mode == "home":
            return Path.home()
        if mode == "cwd":
            return Path.cwd()
        if active_path is not None:
            return Path(active_path)
        return Path.home()

    def toggle_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        self.settings.show_hidden_default = self._show_hidden
        for panel in self.panel_widgets.values():
            panel.set_show_hidden(self._show_hidden)

    def toggle_show_widget_map(self, enabled: bool) -> None:
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

    def update_pane_visuals(self) -> None:
        self._status_coordinator.update_pane_visuals()
        self._refresh_context_menu()

    def _refresh_context_menu(self) -> None:
        if self.context_menu_controller is None:
            return
        self.context_menu_controller.rebuild()

    def default_close_warning(self) -> bool:
        return self.panels_coordinator.default_close_warning()
