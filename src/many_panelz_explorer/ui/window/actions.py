from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDockWidget,
    QMenu,
)

from ... import widget_naming
from ...operation_queue_widgets import OperationQueuePanel

if TYPE_CHECKING:
    from ...window import ExplorerWindow


class WindowUiComposer:
    def __init__(self, window: ExplorerWindow) -> None:
        self.window = window

    def build_actions(self) -> None:
        self.window._new_tab_action = QAction("&New Tab", self.window)
        self.window._new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        self.window._new_tab_action.triggered.connect(self.window.new_tab_in_active_panel)

        self.window._new_vertical_panel_action = QAction(
            "New &Vertical Panel", self.window
        )
        self.window._new_vertical_panel_action.setShortcut(QKeySequence("Ctrl+P"))
        self.window._new_vertical_panel_action.triggered.connect(
            lambda: self.window.split_active_panel(Qt.Orientation.Horizontal)
        )

        self.window._new_horizontal_panel_action = QAction(
            "New &Horizontal Panel", self.window
        )
        self.window._new_horizontal_panel_action.setShortcut(QKeySequence("Ctrl+H"))
        self.window._new_horizontal_panel_action.triggered.connect(
            lambda: self.window.split_active_panel(Qt.Orientation.Vertical)
        )

        self.window._clone_vertical_panel_action = QAction(
            "Clone Current Panel (Ver&tical)", self.window
        )
        self.window._clone_vertical_panel_action.triggered.connect(
            lambda: self.window.clone_active_panel(Qt.Orientation.Horizontal)
        )

        self.window._clone_horizontal_panel_action = QAction(
            "Clone Current Panel (Hori&zontal)", self.window
        )
        self.window._clone_horizontal_panel_action.triggered.connect(
            lambda: self.window.clone_active_panel(Qt.Orientation.Vertical)
        )

        self.window._copy_to_target_action = QAction(
            "&Copy to Target Pane", self.window
        )
        self.window._copy_to_target_action.setShortcut(QKeySequence("F5"))
        self.window._copy_to_target_action.triggered.connect(
            self.window._copy_selected_to_target
        )

        self.window._copy_to_target_configure_action = QAction(
            "Copy to Target Pane (Configure...)", self.window
        )
        self.window._copy_to_target_configure_action.triggered.connect(
            lambda: self.window._copy_selected_to_target(configure=True)
        )

        self.window._move_to_target_action = QAction(
            "&Move to Target Pane", self.window
        )
        self.window._move_to_target_action.setShortcut(QKeySequence("F6"))
        self.window._move_to_target_action.triggered.connect(
            self.window._move_selected_to_target
        )

        self.window._move_to_target_configure_action = QAction(
            "Move to Target Pane (Configure...)", self.window
        )
        self.window._move_to_target_configure_action.triggered.connect(
            lambda: self.window._move_selected_to_target(configure=True)
        )

        self.window._delete_selection_action = QAction(
            "&Delete Selection", self.window
        )
        self.window._delete_selection_action.setShortcut(QKeySequence("F8"))
        self.window._delete_selection_action.triggered.connect(
            self.window._delete_selected_items
        )

        self.window._delete_selection_configure_action = QAction(
            "Delete Selection (Configure...)", self.window
        )
        self.window._delete_selection_configure_action.triggered.connect(
            lambda: self.window._delete_selected_items(configure=True)
        )

        self.window._new_window_action = QAction("New &Window", self.window)
        self.window._new_window_action.setShortcut(QKeySequence("Ctrl+N"))
        self.window._new_window_action.triggered.connect(
            self.window.request_new_window.emit
        )

        self.window._clone_window_action = QAction(
            "Clone Current W&indow", self.window
        )
        self.window._clone_window_action.triggered.connect(
            self.window.clone_current_window
        )

        self.window._save_view_action = QAction("&Save View", self.window)
        self.window._save_view_action.triggered.connect(self.window.save_view)

        self.window._restore_view_action = QAction("&Restore View...", self.window)
        self.window._restore_view_action.triggered.connect(self.window.restore_view)

        self.window._replace_view_action = QAction("Re&place View", self.window)
        self.window._replace_view_action.triggered.connect(self.window.replace_view)

        self.window._close_tab_action = QAction("Close Ta&b", self.window)
        self.window._close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        self.window._close_tab_action.triggered.connect(self.window.close_active_tab)

        self.window._close_panel_action = QAction("Close Pane&l", self.window)
        self.window._close_panel_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self.window._close_panel_action.triggered.connect(
            self.window.close_active_panel
        )

        self.window._close_window_action = QAction("Close Win&dow", self.window)
        self.window._close_window_action.setShortcut(QKeySequence("Alt+W"))
        self.window._close_window_action.triggered.connect(self.window.close)

        self.window._exit_action = QAction("E&xit", self.window)
        self.window._exit_action.setShortcuts(
            [QKeySequence("Ctrl+Q"), QKeySequence("Alt+X")]
        )
        self.window._exit_action.triggered.connect(self.window._quit_application)

        self.window._refresh_action = QAction("&Refresh", self.window)
        self.window._refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        self.window._refresh_action.triggered.connect(self.window._refresh_active_panel)

        self.window._on_top_action = QAction("On &Top", self.window)
        self.window._on_top_action.setCheckable(True)
        self.window._on_top_action.toggled.connect(self.window.set_on_top)

        self.window._show_hidden_action = QAction("Show &Hidden Files", self.window)
        self.window._show_hidden_action.setCheckable(True)
        self.window._show_hidden_action.setChecked(self.window._show_hidden)
        self.window._show_hidden_action.toggled.connect(self.window._toggle_show_hidden)

        self.window._show_widget_map_action = QAction(
            "Show &Widget Map", self.window
        )
        self.window._show_widget_map_action.setCheckable(True)
        self.window._show_widget_map_action.setChecked(self.window._show_widget_map)
        self.window._show_widget_map_action.toggled.connect(
            self.window._toggle_show_widget_map
        )

        self.window._align_columns_current_panel_tabs_action = QAction(
            "Align Columns: Current Panel Tabs", self.window
        )
        self.window._align_columns_current_panel_tabs_action.triggered.connect(
            self.window._align_columns_current_panel_tabs
        )

        self.window._align_columns_all_panels_tabs_action = QAction(
            "Align Columns: All Panels and Tabs", self.window
        )
        self.window._align_columns_all_panels_tabs_action.triggered.connect(
            self.window._align_columns_all_panels_tabs
        )

        self.window._show_queue_dock_action = QAction("Show Queue Dock", self.window)
        self.window._show_queue_dock_action.setCheckable(True)
        self.window._show_queue_dock_action.toggled.connect(self.window._toggle_queue_dock)

        self.window._show_queue_window_action = QAction(
            "Show Queue Window", self.window
        )
        self.window._show_queue_window_action.triggered.connect(
            self.window.controller.show_queue_floating_window
        )

        self.window._settings_action = QAction("&Settings...", self.window)
        self.window._settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.window._settings_action.triggered.connect(self.window._open_settings_dialog)

        self.window._help_action = QAction("&Help", self.window)
        self.window._help_action.setShortcut(QKeySequence("F1"))
        self.window._help_action.triggered.connect(self.window._show_help)

    def build_shortcuts(self) -> None:
        self.window._next_pane_shortcut = QShortcut(QKeySequence("Tab"), self.window)
        self.window._next_pane_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.window._next_pane_shortcut.activated.connect(self.window._focus_next_panel)

        self.window._previous_pane_shortcut = QShortcut(
            QKeySequence("Shift+Tab"), self.window
        )
        self.window._previous_pane_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.window._previous_pane_shortcut.activated.connect(
            self.window._focus_previous_panel
        )

        self.window._menu_focus_shortcut = QShortcut(QKeySequence("F10"), self.window)
        self.window._menu_focus_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.window._menu_focus_shortcut.activated.connect(self.window._focus_menu_bar)

    def build_menus(self) -> None:
        menu_bar = self.window.menuBar()
        menu_bar.setNativeMenuBar(True)

        file_menu = QMenu("&File", self.window)
        file_menu.addAction(self.window._new_tab_action)
        file_menu.addAction(self.window._new_vertical_panel_action)
        file_menu.addAction(self.window._new_horizontal_panel_action)
        file_menu.addAction(self.window._clone_vertical_panel_action)
        file_menu.addAction(self.window._clone_horizontal_panel_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window._copy_to_target_action)
        file_menu.addAction(self.window._copy_to_target_configure_action)
        file_menu.addAction(self.window._move_to_target_action)
        file_menu.addAction(self.window._move_to_target_configure_action)
        file_menu.addAction(self.window._delete_selection_action)
        file_menu.addAction(self.window._delete_selection_configure_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window._new_window_action)
        file_menu.addAction(self.window._clone_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window._save_view_action)
        self.window._restore_view_menu = QMenu("&Restore View", self.window)
        self.window._restore_view_menu.aboutToShow.connect(
            self.window._populate_restore_view_menu
        )
        file_menu.addMenu(self.window._restore_view_menu)
        file_menu.addAction(self.window._replace_view_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window._close_tab_action)
        file_menu.addAction(self.window._close_panel_action)
        file_menu.addAction(self.window._close_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self.window._exit_action)

        view_menu = QMenu("&View", self.window)
        view_menu.addAction(self.window._refresh_action)
        view_menu.addAction(self.window._align_columns_current_panel_tabs_action)
        view_menu.addAction(self.window._align_columns_all_panels_tabs_action)
        view_menu.addSeparator()
        view_menu.addAction(self.window._show_queue_dock_action)
        view_menu.addAction(self.window._show_queue_window_action)
        view_menu.addSeparator()
        view_menu.addAction(self.window._on_top_action)
        view_menu.addAction(self.window._show_hidden_action)
        view_menu.addAction(self.window._show_widget_map_action)
        view_menu.addSeparator()
        view_menu.addAction(self.window._settings_action)

        help_menu = QMenu("&Help", self.window)
        help_menu.addAction(self.window._help_action)

        self.window._menu_file_action = menu_bar.addMenu(file_menu)
        self.window._menu_view_action = menu_bar.addMenu(view_menu)
        self.window._menu_help_action = menu_bar.addMenu(help_menu)

        self.window.addActions(
            [
                self.window._new_tab_action,
                self.window._new_vertical_panel_action,
                self.window._new_horizontal_panel_action,
                self.window._clone_vertical_panel_action,
                self.window._clone_horizontal_panel_action,
                self.window._copy_to_target_action,
                self.window._copy_to_target_configure_action,
                self.window._move_to_target_action,
                self.window._move_to_target_configure_action,
                self.window._delete_selection_action,
                self.window._delete_selection_configure_action,
                self.window._new_window_action,
                self.window._clone_window_action,
                self.window._save_view_action,
                self.window._restore_view_action,
                self.window._replace_view_action,
                self.window._close_tab_action,
                self.window._close_panel_action,
                self.window._close_window_action,
                self.window._exit_action,
                self.window._refresh_action,
                self.window._align_columns_current_panel_tabs_action,
                self.window._align_columns_all_panels_tabs_action,
                self.window._show_queue_dock_action,
                self.window._show_queue_window_action,
                self.window._show_widget_map_action,
                self.window._settings_action,
                self.window._help_action,
            ]
        )

    def build_operation_queue_widgets(self) -> None:
        self.window._queue_dock = QDockWidget("Operation Queue", self.window)
        self.window._queue_dock.setObjectName(
            widget_naming.object_name_for_id(
                f"{widget_naming.window_widget_id(self.window.window_id)}:queue_dock"
            )
        )
        self.window._queue_panel = OperationQueuePanel(
            manager=self.window.controller.operation_queue_manager,
            model=self.window.controller.operation_queue_model,
            parent=self.window._queue_dock,
        )
        self.window._queue_dock.setWidget(self.window._queue_panel)
        self.window._queue_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.window.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self.window._queue_dock
        )
        self.window._queue_dock.visibilityChanged.connect(
            self.window._on_queue_dock_visibility_changed
        )

    def apply_operation_queue_visibility(self) -> None:
        mode = str(self.window._operation_queue_view_mode or "").strip().lower()
        show_dock = mode in {"dock_tab", "both"}
        with QSignalBlocker(self.window._show_queue_dock_action):
            self.window._show_queue_dock_action.setChecked(show_dock)
        self.window._queue_dock.setVisible(show_dock)
        if mode in {"floating_window", "both"}:
            self.window.controller.show_queue_floating_window()

