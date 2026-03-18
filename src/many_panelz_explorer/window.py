"""Main explorer window composition and high-level user interactions."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeGuard

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
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
from .external_file_managers import ExternalFileManagerLauncher
from .ui.window import (
    WindowLayoutCoordinator,
    WindowOperationsCoordinator,
    WindowPanelsCoordinator,
    WindowPersistenceCoordinator,
    WindowPreferencesCoordinator,
    WindowStatusCoordinator,
    WindowUiComposer,
    WindowViewsCoordinator,
)
from .ui.window.panels import (
    resolve_window_target_panel_id,
    window_default_close_warning,
)

if TYPE_CHECKING:
    from PySide6.QtGui import (
        QAction,
        QActionGroup,
        QCloseEvent,
        QResizeEvent,
        QShortcut,
        QShowEvent,
    )

    from ._settings.manager import SettingsManager
    from .app_controller import AppController
    from .operation_queue_widgets import OperationQueuePanel
    from .panel_widget import PanelWidget
    from .ui.window.state_types import ClosedTabState, PanelRows, TabsState
    from .ui.window.status import StorageOverviewLabel


type RootsProvider = Callable[[Path | None], list[Path]]


class _OperationJobRequest(Protocol):
    created_by: str


class _OperationJob(Protocol):
    request: _OperationJobRequest
    status: str


def _is_operation_job(value: object) -> TypeGuard[_OperationJob]:
    """Return whether the runtime payload matches the operation-job contract."""

    request = getattr(value, "request", None)
    created_by = getattr(request, "created_by", None)
    status = getattr(value, "status", None)
    return isinstance(created_by, str) and isinstance(status, str)


class ExplorerWindow(QMainWindow):
    """Main explorer window composed from focused UI coordinators."""

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
    explorer_here_source_action: QAction
    explorer_here_source_target_action: QAction
    total_commander_here_source_action: QAction
    total_commander_here_source_target_action: QAction
    double_commander_here_source_action: QAction
    double_commander_here_source_target_action: QAction
    new_window_action: QAction
    clone_window_action: QAction
    save_view_action: QAction
    restore_view_action: QAction
    replace_view_action: QAction
    close_tab_action: QAction
    reopen_closed_tab_action: QAction
    close_panel_action: QAction
    close_window_action: QAction
    exit_action: QAction
    refresh_action: QAction
    fit_columns_action: QAction
    follow_default_tab_position_action: QAction
    top_tab_position_action: QAction
    bottom_tab_position_action: QAction
    left_tab_position_action: QAction
    left_horizontal_tab_position_action: QAction
    right_tab_position_action: QAction
    right_horizontal_tab_position_action: QAction
    on_top_action: QAction
    show_hidden_action: QAction
    show_widget_map_action: QAction
    align_columns_current_panel_tabs_action: QAction
    align_columns_all_panels_tabs_action: QAction
    align_columns_all_windows_action: QAction
    show_queue_dock_action: QAction
    show_queue_window_action: QAction
    settings_action: QAction
    help_action: QAction
    active_panel_tab_position_action_group: QActionGroup
    active_panel_tab_position_menu: QMenu
    restore_view_menu: QMenu
    context_menu: QMenu
    menu_file_action: QAction
    menu_view_action: QAction
    menu_context_action: QAction
    menu_help_action: QAction
    next_pane_shortcut: QShortcut
    previous_pane_shortcut: QShortcut
    menu_focus_shortcut: QShortcut
    reread_visible_lists_shortcut: QShortcut
    list_files_shortcut: QShortcut
    alt_list_files_shortcut: QShortcut
    edit_files_shortcut: QShortcut
    new_text_file_shortcut: QShortcut
    create_directory_shortcut: QShortcut
    pack_files_shortcut: QShortcut
    copy_path_shortcut: QShortcut
    root_picker_shortcut: QShortcut
    minimize_windows_shortcut: QShortcut
    queue_dock: QDockWidget
    queue_panel: OperationQueuePanel
    source_path_label: QLabel
    target_path_label: QLabel
    status_rows_host: QWidget
    status_paths_row: QWidget
    storage_overview_row: QWidget
    storage_entries_host: QWidget
    storage_entries_layout: QHBoxLayout
    storage_overview_labels: list[StorageOverviewLabel]

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
        self.roots_provider = roots_provider
        self.active_panel_id: int | None = None
        self.last_non_source_panel_id: int | None = None

        self.layout_coordinator = WindowLayoutCoordinator(self)
        self.panel_tree = self.layout_coordinator.default_startup_tree()
        self.panels_coordinator = WindowPanelsCoordinator(self)
        self.status_coordinator = WindowStatusCoordinator(self)
        self.operations_coordinator = WindowOperationsCoordinator(self)
        self.external_file_manager_launcher = ExternalFileManagerLauncher(self)
        self.persistence_coordinator = WindowPersistenceCoordinator(self)
        ui_preferences = self.settings.ui_preferences()
        self.preferences_coordinator = WindowPreferencesCoordinator(
            self,
            initial_path=initial_path,
            preferences=ui_preferences,
        )
        self.views_coordinator = WindowViewsCoordinator(self)
        self.ui_composer = WindowUiComposer(self)
        self.context_menu_controller: ContextMenuController | None = None

        self.layout_rows: PanelRows = self.layout_coordinator.rows_from_tree(
            self.panel_tree.root
        )
        self.panel_widgets: dict[int, PanelWidget] = {}
        self.recently_closed_tabs: list[ClosedTabState] = []

        self._central = QWidget(self)
        self.central_layout = QVBoxLayout(self._central)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self._central)
        self.default_maximize_on_first_show = True
        self._did_schedule_initial_autofit = False

        self.ui_composer.build_actions()
        self.ui_composer.build_menus()
        self.context_menu_controller = ContextMenuController(self, self.context_menu)
        self.ui_composer.build_shortcuts()
        self.ui_composer.build_operation_queue_widgets()
        self.status_coordinator.set_storage_bytes_formatter(
            self.preferences_coordinator.format_status_bar_bytes
        )
        self.status_coordinator.set_storage_label_template(
            self.preferences_coordinator.status_bar_storage_label_template
        )
        self.status_coordinator.set_storage_overview_enabled(
            self.preferences_coordinator.show_storage_overview_enabled
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
        self.ui_composer.apply_operation_queue_visibility()
        self._refresh_context_menu()

    def clone_current_window(self) -> None:
        new_window = self.controller.new_window(from_window=self, show=False)
        new_window.persistence_coordinator.apply_cloned_state(
            self.persistence_coordinator.serialize_state()
        )
        new_window.show()

    def set_on_top(self, enabled: bool) -> None:
        on_top = bool(enabled)
        was_maximized = self.isMaximized()
        with QSignalBlocker(self.on_top_action):
            self.on_top_action.setChecked(on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.show()
        if was_maximized:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    # ----- QWidget/QWindow events -----
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowActivate:
            self.window_activated.emit()
            self._refresh_context_menu()
        return super().event(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.controller.close_window(self)
        super().closeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self.default_maximize_on_first_show and not self.isMaximized():
            self.default_maximize_on_first_show = False
            self.showMaximized()
            return
        if not self._did_schedule_initial_autofit:
            self._did_schedule_initial_autofit = True
            self.panels_coordinator.column_sync_coordinator.schedule_autofit_columns()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.panels_coordinator.column_sync_coordinator.schedule_autofit_columns()

    def toggle_queue_dock(self, enabled: bool) -> None:
        self.queue_dock.setVisible(bool(enabled))

    def on_queue_dock_visibility_changed(self, visible: bool) -> None:
        with QSignalBlocker(self.show_queue_dock_action):
            self.show_queue_dock_action.setChecked(bool(visible))

    def _on_operation_job_updated(self, job_obj: object) -> None:
        if not _is_operation_job(job_obj):
            return
        created_by = job_obj.request.created_by
        if not created_by.startswith(f"window:{self.window_id}"):
            return
        status = job_obj.status
        if status not in {"succeeded", "failed", "cancelled"}:
            return
        panel = self.panels_coordinator.active_panel()
        if panel is not None:
            panel.navigation_coordinator.refresh_current_path()
        target_id = (
            resolve_window_target_panel_id(self, self.active_panel_id)
            if self.active_panel_id is not None
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

    def minimize_managed_windows(self) -> None:
        """Minimize this app's managed windows."""

        minimize_all = getattr(self.controller, "minimize_all_windows", None)
        if callable(minimize_all):
            minimize_all()
            return
        self.showMinimized()

    def show_help(self) -> None:
        QMessageBox.information(
            self,
            "Help",
            "Keyboard shortcuts:\n"
            "F2: Refresh all visible panes\n"
            "F3 / Alt+F3: View selected file(s)\n"
            "F4 / Shift+F4: Edit selected file(s) / create text file\n"
            "F5: Copy to target pane\n"
            "F6: Move to target pane\n"
            "F7: Create directory\n"
            "F8 / Delete: Delete selection\n"
            "Alt+F1: Open root picker for active tab\n"
            "Alt+F5: Create ZIP from selection\n"
            "Tab / Shift+Tab: Switch active pane\n"
            "Ctrl+A: Select all items in file list\n"
            "Ctrl+P: Copy selected item path or active pane path\n"
            "Ctrl+Shift+T: Reopen last closed tab\n"
            "Ctrl+, : Open settings\n"
            "Alt or F10: Focus main menu\n"
            "Shift+Esc: Minimize app windows\n"
            "Ctrl+Q / Alt+X: Exit application",
        )

    def open_settings_dialog(self) -> None:
        from .dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(controller=self.controller, parent=self)
        dialog.exec()

    def quit_application(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def update_pane_visuals(self) -> None:
        self.status_coordinator.update_pane_visuals()
        self.ui_composer.sync_active_panel_tab_position_actions()
        self._refresh_context_menu()

    def _refresh_context_menu(self) -> None:
        if self.context_menu_controller is None:
            return
        self.context_menu_controller.rebuild()

    def default_close_warning(self) -> bool:
        return window_default_close_warning(self)
