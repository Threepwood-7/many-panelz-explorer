"""Action, menu, shortcut, and queue-widget composition for the window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDockWidget,
    QMenu,
)
from threep_commons.qt.widget_identity import object_name_for_id

from ... import widget_naming
from ...operation_queue_widgets import OperationQueuePanel

if TYPE_CHECKING:
    from ...window import ExplorerWindow


class WindowUiComposer:
    """Build window-level actions, menus, shortcuts, and queue widgets."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Store the owning window."""
        self.window = window

    def build_actions(self) -> None:
        """Create the QAction instances used by the main window."""
        self._build_panel_actions()
        self._build_operation_actions()
        self._build_window_actions()
        self._build_view_actions()
        self._build_settings_actions()

    def _build_panel_actions(self) -> None:
        self.window.new_tab_action = QAction("&New Tab", self.window)
        self.window.new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        self.window.new_tab_action.triggered.connect(
            self.window.panels_coordinator.new_tab_in_active_panel
        )

        self.window.new_vertical_panel_action = QAction(
            "New &Vertical Panel", self.window
        )
        self.window.new_vertical_panel_action.setShortcut(QKeySequence("Ctrl+P"))
        self.window.new_vertical_panel_action.triggered.connect(
            lambda: self.window.panels_coordinator.split_active_panel(
                Qt.Orientation.Horizontal
            )
        )

        self.window.new_horizontal_panel_action = QAction(
            "New &Horizontal Panel", self.window
        )
        self.window.new_horizontal_panel_action.setShortcut(QKeySequence("Ctrl+H"))
        self.window.new_horizontal_panel_action.triggered.connect(
            lambda: self.window.panels_coordinator.split_active_panel(
                Qt.Orientation.Vertical
            )
        )

        self.window.clone_vertical_panel_action = QAction(
            "Clone Current Panel (Ver&tical)", self.window
        )
        self.window.clone_vertical_panel_action.triggered.connect(
            lambda: self.window.panels_coordinator.clone_active_panel(
                Qt.Orientation.Horizontal
            )
        )

        self.window.clone_horizontal_panel_action = QAction(
            "Clone Current Panel (Hori&zontal)", self.window
        )
        self.window.clone_horizontal_panel_action.triggered.connect(
            lambda: self.window.panels_coordinator.clone_active_panel(
                Qt.Orientation.Vertical
            )
        )

        self.window.close_tab_action = QAction("Close Ta&b", self.window)
        self.window.close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        self.window.close_tab_action.triggered.connect(
            self.window.panels_coordinator.close_active_tab
        )

        self.window.close_panel_action = QAction("Close Pane&l", self.window)
        self.window.close_panel_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self.window.close_panel_action.triggered.connect(
            self.window.panels_coordinator.close_active_panel
        )

        self.window.refresh_action = QAction("&Refresh", self.window)
        self.window.refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        self.window.refresh_action.triggered.connect(
            self.window.panels_coordinator.refresh_active_panel
        )

        self.window.align_columns_current_panel_tabs_action = QAction(
            "Align Columns: Current Panel Tabs", self.window
        )
        self.window.align_columns_current_panel_tabs_action.triggered.connect(
            self.window.panels_coordinator.align_columns_current_panel_tabs
        )

        self.window.align_columns_all_panels_tabs_action = QAction(
            "Align Columns: All Panels and Tabs", self.window
        )
        self.window.align_columns_all_panels_tabs_action.triggered.connect(
            self.window.panels_coordinator.align_columns_all_panels_tabs
        )

        self.window.align_columns_all_windows_action = QAction(
            "Align Columns: All Windows", self.window
        )
        self.window.align_columns_all_windows_action.triggered.connect(
            self.window.panels_coordinator.align_columns_all_windows
        )

    def _build_operation_actions(self) -> None:
        self.window.copy_to_target_action = QAction("&Copy to Target Pane", self.window)
        self.window.copy_to_target_action.setShortcut(QKeySequence("F5"))
        self.window.copy_to_target_action.triggered.connect(
            lambda: self.window.operations_coordinator.transfer_selected_to_target(
                move=False
            )
        )

        self.window.copy_to_target_configure_action = QAction(
            "Copy to Target Pane (Configure...)", self.window
        )
        self.window.copy_to_target_configure_action.triggered.connect(
            lambda: self.window.operations_coordinator.transfer_selected_to_target(
                move=False,
                configure=True,
            )
        )

        self.window.move_to_target_action = QAction("&Move to Target Pane", self.window)
        self.window.move_to_target_action.setShortcut(QKeySequence("F6"))
        self.window.move_to_target_action.triggered.connect(
            lambda: self.window.operations_coordinator.transfer_selected_to_target(
                move=True
            )
        )

        self.window.move_to_target_configure_action = QAction(
            "Move to Target Pane (Configure...)", self.window
        )
        self.window.move_to_target_configure_action.triggered.connect(
            lambda: self.window.operations_coordinator.transfer_selected_to_target(
                move=True,
                configure=True,
            )
        )

        self.window.delete_selection_action = QAction("&Delete Selection", self.window)
        self.window.delete_selection_action.setShortcut(QKeySequence("F8"))
        self.window.delete_selection_action.triggered.connect(
            self.window.operations_coordinator.delete_selected_items
        )

        self.window.delete_selection_configure_action = QAction(
            "Delete Selection (Configure...)", self.window
        )
        self.window.delete_selection_configure_action.triggered.connect(
            lambda: self.window.operations_coordinator.delete_selected_items(
                configure=True
            )
        )

    def _build_window_actions(self) -> None:
        self.window.new_window_action = QAction("New &Window", self.window)
        self.window.new_window_action.setShortcut(QKeySequence("Ctrl+N"))
        self.window.new_window_action.triggered.connect(
            self.window.request_new_window.emit
        )

        self.window.clone_window_action = QAction("Clone Current W&indow", self.window)
        self.window.clone_window_action.triggered.connect(
            self.window.clone_current_window
        )

        self.window.close_window_action = QAction("Close Win&dow", self.window)
        self.window.close_window_action.setShortcut(QKeySequence("Alt+W"))
        self.window.close_window_action.triggered.connect(self.window.close)

        self.window.exit_action = QAction("E&xit", self.window)
        self.window.exit_action.setShortcuts(
            [QKeySequence("Ctrl+Q"), QKeySequence("Alt+X")]
        )
        self.window.exit_action.triggered.connect(self.window.quit_application)

    def _build_view_actions(self) -> None:
        self.window.save_view_action = QAction("&Save View", self.window)
        self.window.save_view_action.triggered.connect(
            self.window.views_coordinator.save_view
        )

        self.window.restore_view_action = QAction("&Restore View...", self.window)
        self.window.restore_view_action.triggered.connect(
            self.window.views_coordinator.restore_view
        )

        self.window.replace_view_action = QAction("Re&place View", self.window)
        self.window.replace_view_action.triggered.connect(
            self.window.views_coordinator.replace_view
        )

    def _build_settings_actions(self) -> None:

        self.window.on_top_action = QAction("On &Top", self.window)
        self.window.on_top_action.setCheckable(True)
        self.window.on_top_action.toggled.connect(self.window.set_on_top)

        self.window.show_hidden_action = QAction("Show &Hidden Files", self.window)
        self.window.show_hidden_action.setCheckable(True)
        self.window.show_hidden_action.setChecked(
            self.window.preferences_coordinator.show_hidden_enabled
        )
        self.window.show_hidden_action.toggled.connect(
            self.window.preferences_coordinator.set_show_hidden
        )

        self.window.show_widget_map_action = QAction("Show &Widget Map", self.window)
        self.window.show_widget_map_action.setCheckable(True)
        self.window.show_widget_map_action.setChecked(
            self.window.preferences_coordinator.show_widget_map_enabled
        )
        self.window.show_widget_map_action.toggled.connect(
            self.window.preferences_coordinator.set_show_widget_map
        )

        self.window.show_queue_dock_action = QAction("Show Queue Dock", self.window)
        self.window.show_queue_dock_action.setCheckable(True)
        self.window.show_queue_dock_action.toggled.connect(
            self.window.toggle_queue_dock
        )

        self.window.show_queue_window_action = QAction("Show Queue Window", self.window)
        self.window.show_queue_window_action.triggered.connect(
            self.window.controller.show_queue_floating_window
        )

        self.window.settings_action = QAction("&Settings...", self.window)
        self.window.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.window.settings_action.triggered.connect(self.window.open_settings_dialog)

        self.window.help_action = QAction("&Help", self.window)
        self.window.help_action.setShortcut(QKeySequence("F1"))
        self.window.help_action.triggered.connect(self.window.show_help)

    def build_shortcuts(self) -> None:
        """Create the global shortcuts that are not QAction-based."""
        self.window.next_pane_shortcut = QShortcut(QKeySequence("Tab"), self.window)
        self.window.next_pane_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.window.next_pane_shortcut.activated.connect(
            self.window.panels_coordinator.focus_next_panel
        )

        self.window.previous_pane_shortcut = QShortcut(
            QKeySequence("Shift+Tab"), self.window
        )
        self.window.previous_pane_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.window.previous_pane_shortcut.activated.connect(
            self.window.panels_coordinator.focus_previous_panel
        )

        self.window.menu_focus_shortcut = QShortcut(QKeySequence("F10"), self.window)
        self.window.menu_focus_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.window.menu_focus_shortcut.activated.connect(self.window.focus_menu_bar)

    def build_menus(self) -> None:
        """Build the main menubar and register the exposed actions."""
        menu_bar = self.window.menuBar()
        menu_bar.setNativeMenuBar(True)

        file_menu = QMenu("&File", self.window)
        file_menu.addAction(self.window.new_tab_action)
        file_menu.addAction(self.window.new_vertical_panel_action)
        file_menu.addAction(self.window.new_horizontal_panel_action)
        file_menu.addAction(self.window.clone_vertical_panel_action)
        file_menu.addAction(self.window.clone_horizontal_panel_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window.copy_to_target_action)
        file_menu.addAction(self.window.copy_to_target_configure_action)
        file_menu.addAction(self.window.move_to_target_action)
        file_menu.addAction(self.window.move_to_target_configure_action)
        file_menu.addAction(self.window.delete_selection_action)
        file_menu.addAction(self.window.delete_selection_configure_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window.new_window_action)
        file_menu.addAction(self.window.clone_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window.save_view_action)
        self.window.restore_view_menu = QMenu("&Restore View", self.window)
        self.window.restore_view_menu.aboutToShow.connect(
            self._populate_restore_view_menu
        )
        file_menu.addMenu(self.window.restore_view_menu)
        file_menu.addAction(self.window.replace_view_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window.close_tab_action)
        file_menu.addAction(self.window.close_panel_action)
        file_menu.addAction(self.window.close_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window.exit_action)

        view_menu = QMenu("&View", self.window)
        view_menu.addAction(self.window.refresh_action)
        view_menu.addAction(self.window.align_columns_current_panel_tabs_action)
        view_menu.addAction(self.window.align_columns_all_panels_tabs_action)
        view_menu.addAction(self.window.align_columns_all_windows_action)
        view_menu.addSeparator()
        view_menu.addAction(self.window.show_queue_dock_action)
        view_menu.addAction(self.window.show_queue_window_action)
        view_menu.addSeparator()
        view_menu.addAction(self.window.on_top_action)
        view_menu.addAction(self.window.show_hidden_action)
        view_menu.addAction(self.window.show_widget_map_action)
        view_menu.addSeparator()
        view_menu.addAction(self.window.settings_action)

        self.window.context_menu = QMenu("&Context", self.window)

        help_menu = QMenu("&Help", self.window)
        help_menu.addAction(self.window.help_action)

        self.window.menu_file_action = menu_bar.addMenu(file_menu)
        self.window.menu_view_action = menu_bar.addMenu(view_menu)
        self.window.menu_context_action = menu_bar.addMenu(self.window.context_menu)
        self.window.menu_context_action.setVisible(False)
        self.window.menu_help_action = menu_bar.addMenu(help_menu)

        self.window.addActions(
            [
                self.window.new_tab_action,
                self.window.new_vertical_panel_action,
                self.window.new_horizontal_panel_action,
                self.window.clone_vertical_panel_action,
                self.window.clone_horizontal_panel_action,
                self.window.copy_to_target_action,
                self.window.copy_to_target_configure_action,
                self.window.move_to_target_action,
                self.window.move_to_target_configure_action,
                self.window.delete_selection_action,
                self.window.delete_selection_configure_action,
                self.window.new_window_action,
                self.window.clone_window_action,
                self.window.save_view_action,
                self.window.restore_view_action,
                self.window.replace_view_action,
                self.window.close_tab_action,
                self.window.close_panel_action,
                self.window.close_window_action,
                self.window.exit_action,
                self.window.refresh_action,
                self.window.align_columns_current_panel_tabs_action,
                self.window.align_columns_all_panels_tabs_action,
                self.window.align_columns_all_windows_action,
                self.window.show_queue_dock_action,
                self.window.show_queue_window_action,
                self.window.show_widget_map_action,
                self.window.settings_action,
                self.window.help_action,
            ]
        )

    def build_operation_queue_widgets(self) -> None:
        """Create the docked operation queue widgets."""
        self.window.queue_dock = QDockWidget("Operation Queue", self.window)
        self.window.queue_dock.setObjectName(
            object_name_for_id(
                f"{widget_naming.window_widget_id(self.window.window_id)}:queue_dock"
            )
        )
        self.window.queue_panel = OperationQueuePanel(
            manager=self.window.controller.operation_queue_manager,
            model=self.window.controller.operation_queue_model,
            parent=self.window.queue_dock,
        )
        self.window.queue_dock.setWidget(self.window.queue_panel)
        self.window.queue_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.window.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self.window.queue_dock
        )
        self.window.queue_dock.visibilityChanged.connect(
            self.window.on_queue_dock_visibility_changed
        )

    def apply_operation_queue_visibility(self) -> None:
        """Apply the preferred queue docking and floating-window visibility."""
        mode = (
            str(self.window.preferences_coordinator.operation_queue_view_mode or "")
            .strip()
            .lower()
        )
        show_dock = mode in {"dock_tab", "both"}
        with QSignalBlocker(self.window.show_queue_dock_action):
            self.window.show_queue_dock_action.setChecked(show_dock)
        self.window.queue_dock.setVisible(show_dock)
        if mode in {"floating_window", "both"}:
            self.window.controller.show_queue_floating_window()

    def _populate_restore_view_menu(self) -> None:
        self.window.views_coordinator.populate_restore_view_menu(
            self.window.restore_view_menu
        )
