from __future__ import annotations

import shutil
import uuid
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from PySide6.QtCore import QByteArray, QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import file_ops
from .panel_tree import (
    ORIENTATION_HORIZONTAL,
    ORIENTATION_VERTICAL,
    LeafNode,
    PanelTreeModel,
    SplitNode,
)
from .panel_widget import PanelWidget

if TYPE_CHECKING:
    from .app_controller import AppController
    from .settings import SettingsManager


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

        self.panel_tree = PanelTreeModel()
        self._layout_rows: PanelRows = self._rows_from_tree(self.panel_tree.root)
        self.panel_widgets: dict[int, PanelWidget] = {}

        self._central = QWidget(self)
        self._central_layout = QVBoxLayout(self._central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self._central)
        self.statusBar().showMessage("")

        self._show_hidden = self.settings.show_hidden_default

        self._build_actions()
        self._build_menus()
        self._build_shortcuts()

        self.setWindowTitle("Many Panelz Explorer")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self._neutralize_menu_overlap_widgets()

        empty_state: TabsState = {}
        self._sync_panel_tree_from_rows()
        self._rebuild_from_tree(tabs_state=empty_state, preferred_active_panel=None)

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
                tabs_state[new_panel_id] = self._new_panel_state(new_panel_id, seed_path)
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

        source_state = tabs_state.get(self._active_panel_id) or self._default_panel_state(
            self._active_panel_id
        )
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
        return super().event(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.controller.close_window(self)
        super().closeEvent(event)

    # ----- UI composition -----
    def _build_actions(self) -> None:
        self._new_tab_action = QAction("&New Tab", self)
        self._new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        self._new_tab_action.triggered.connect(self.new_tab_in_active_panel)

        self._new_vertical_panel_action = QAction("New &Vertical Panel", self)
        self._new_vertical_panel_action.setShortcut(QKeySequence("Ctrl+P"))
        self._new_vertical_panel_action.triggered.connect(
            lambda: self.split_active_panel(Qt.Orientation.Horizontal)
        )

        self._new_horizontal_panel_action = QAction("New &Horizontal Panel", self)
        self._new_horizontal_panel_action.setShortcut(QKeySequence("Ctrl+H"))
        self._new_horizontal_panel_action.triggered.connect(
            lambda: self.split_active_panel(Qt.Orientation.Vertical)
        )

        self._clone_vertical_panel_action = QAction(
            "Clone Current Panel (Ver&tical)", self
        )
        self._clone_vertical_panel_action.triggered.connect(
            lambda: self.clone_active_panel(Qt.Orientation.Horizontal)
        )

        self._clone_horizontal_panel_action = QAction(
            "Clone Current Panel (Hori&zontal)", self
        )
        self._clone_horizontal_panel_action.triggered.connect(
            lambda: self.clone_active_panel(Qt.Orientation.Vertical)
        )

        self._copy_to_target_action = QAction("&Copy to Target Pane", self)
        self._copy_to_target_action.setShortcut(QKeySequence("F5"))
        self._copy_to_target_action.triggered.connect(self._copy_selected_to_target)

        self._move_to_target_action = QAction("&Move to Target Pane", self)
        self._move_to_target_action.setShortcut(QKeySequence("F6"))
        self._move_to_target_action.triggered.connect(self._move_selected_to_target)

        self._delete_selection_action = QAction("&Delete Selection", self)
        self._delete_selection_action.setShortcut(QKeySequence("F8"))
        self._delete_selection_action.triggered.connect(self._delete_selected_items)

        self._new_window_action = QAction("New &Window", self)
        self._new_window_action.setShortcut(QKeySequence("Ctrl+N"))
        self._new_window_action.triggered.connect(self.request_new_window.emit)

        self._clone_window_action = QAction("Clone Current W&indow", self)
        self._clone_window_action.triggered.connect(self.clone_current_window)

        self._save_view_action = QAction("&Save View", self)
        self._save_view_action.triggered.connect(self.save_view)

        self._restore_view_action = QAction("&Restore View...", self)
        self._restore_view_action.triggered.connect(self.restore_view)

        self._replace_view_action = QAction("Re&place View", self)
        self._replace_view_action.triggered.connect(self.replace_view)

        self._close_tab_action = QAction("Close Ta&b", self)
        self._close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        self._close_tab_action.triggered.connect(self.close_active_tab)

        self._close_panel_action = QAction("Close Pane&l", self)
        self._close_panel_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self._close_panel_action.triggered.connect(self.close_active_panel)

        self._close_window_action = QAction("Close Win&dow", self)
        self._close_window_action.setShortcut(QKeySequence("Alt+W"))
        self._close_window_action.triggered.connect(self.close)

        self._exit_action = QAction("E&xit", self)
        self._exit_action.setShortcuts([QKeySequence("Ctrl+Q"), QKeySequence("Alt+X")])
        self._exit_action.triggered.connect(self._quit_application)

        self._refresh_action = QAction("&Refresh", self)
        self._refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        self._refresh_action.triggered.connect(self._refresh_active_panel)

        self._on_top_action = QAction("On &Top", self)
        self._on_top_action.setCheckable(True)
        self._on_top_action.toggled.connect(self.set_on_top)

        self._show_hidden_action = QAction("Show &Hidden Files", self)
        self._show_hidden_action.setCheckable(True)
        self._show_hidden_action.setChecked(self._show_hidden)
        self._show_hidden_action.toggled.connect(self._toggle_show_hidden)

        self._help_action = QAction("&Help", self)
        self._help_action.setShortcut(QKeySequence("F1"))
        self._help_action.triggered.connect(self._show_help)

    def _build_shortcuts(self) -> None:
        self._next_pane_shortcut = QShortcut(QKeySequence("Tab"), self)
        self._next_pane_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._next_pane_shortcut.activated.connect(self._focus_next_panel)

        self._previous_pane_shortcut = QShortcut(QKeySequence("Shift+Tab"), self)
        self._previous_pane_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._previous_pane_shortcut.activated.connect(self._focus_previous_panel)

        self._menu_focus_shortcut = QShortcut(QKeySequence("F10"), self)
        self._menu_focus_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._menu_focus_shortcut.activated.connect(self._focus_menu_bar)

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(True)

        file_menu = QMenu("&File", self)
        file_menu.addAction(self._new_tab_action)
        file_menu.addAction(self._new_vertical_panel_action)
        file_menu.addAction(self._new_horizontal_panel_action)
        file_menu.addAction(self._clone_vertical_panel_action)
        file_menu.addAction(self._clone_horizontal_panel_action)
        file_menu.addSeparator()
        file_menu.addAction(self._copy_to_target_action)
        file_menu.addAction(self._move_to_target_action)
        file_menu.addAction(self._delete_selection_action)
        file_menu.addSeparator()
        file_menu.addAction(self._new_window_action)
        file_menu.addAction(self._clone_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self._save_view_action)
        self._restore_view_menu = QMenu("&Restore View", self)
        self._restore_view_menu.aboutToShow.connect(self._populate_restore_view_menu)
        file_menu.addMenu(self._restore_view_menu)
        file_menu.addAction(self._replace_view_action)
        file_menu.addSeparator()
        file_menu.addAction(self._close_tab_action)
        file_menu.addAction(self._close_panel_action)
        file_menu.addAction(self._close_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self._exit_action)

        view_menu = QMenu("&View", self)
        view_menu.addAction(self._refresh_action)
        view_menu.addSeparator()
        view_menu.addAction(self._on_top_action)
        view_menu.addAction(self._show_hidden_action)

        help_menu = QMenu("&Help", self)
        help_menu.addAction(self._help_action)

        self._menu_file_action = menu_bar.addMenu(file_menu)
        self._menu_view_action = menu_bar.addMenu(view_menu)
        self._menu_help_action = menu_bar.addMenu(help_menu)

        self.addActions(
            [
                self._new_tab_action,
                self._new_vertical_panel_action,
                self._new_horizontal_panel_action,
                self._clone_vertical_panel_action,
                self._clone_horizontal_panel_action,
                self._copy_to_target_action,
                self._move_to_target_action,
                self._delete_selection_action,
                self._new_window_action,
                self._clone_window_action,
                self._save_view_action,
                self._restore_view_action,
                self._replace_view_action,
                self._close_tab_action,
                self._close_panel_action,
                self._close_window_action,
                self._exit_action,
                self._refresh_action,
                self._help_action,
            ]
        )

    def _focus_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        menu_bar.setActiveAction(self._menu_file_action)

    def _neutralize_menu_overlap_widgets(self) -> None:
        menu_bar = self.menuBar()
        menu_rect = menu_bar.geometry()
        direct_children = self.findChildren(
            QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
        )
        protected = {self._central, menu_bar, self.statusBar()}
        for child in direct_children:
            if child in protected:
                continue
            if type(child) is not QWidget:
                continue
            if not child.isVisible():
                continue
            if child.geometry().intersects(menu_rect):
                # Defensive cleanup for accidental top-level placeholders that can
                # block menubar mouse hits.
                child.hide()
                child.deleteLater()

    def _refresh_active_panel(self) -> None:
        panel = self.active_panel()
        if panel is not None:
            panel.refresh_current_path()

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "Help",
            "Keyboard shortcuts:\n"
            "F5: Copy to target pane\n"
            "F6: Move to target pane\n"
            "F8: Delete selection\n"
            "Tab / Shift+Tab: Switch active pane\n"
            "Alt or F10: Focus main menu\n"
            "Ctrl+Q / Alt+X: Exit application",
        )

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
        for panel_id in panel_ids:
            panel_state = tabs_state.get(panel_id)
            panel = PanelWidget(
                panel_id=panel_id,
                default_path=self._resolve_new_context_path(self._initial_path),
                show_hidden=self._show_hidden,
                show_root_dropdown=self.settings.show_root_dropdown,
                roots_provider=self._roots_provider,
                parent=self,
            )
            panel.activated.connect(lambda pid=panel_id: self._set_active_panel(pid))
            panel.became_empty.connect(
                lambda pid=panel_id: self._close_panel_by_id(pid)
            )

            if isinstance(panel_state, dict):
                panel.restore_state(panel_state)
            else:
                panel.add_tab(self._resolve_new_context_path(self._initial_path))

            new_panel_widgets[panel_id] = panel

        self.panel_widgets = new_panel_widgets

        root_widget = self._build_rows_widget(self._layout_rows)
        if root_widget is None:
            root_widget = QWidget()

        self._clear_layout()
        self._central_layout.addWidget(root_widget)
        self._neutralize_menu_overlap_widgets()

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
        if previous is not None and previous != panel_id and previous in self.panel_widgets:
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

    def _resolve_new_context_path(self, active_path: Path | None) -> Path:
        mode = self.settings.new_context_mode.strip().lower()
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

    def _copy_selected_to_target(self) -> None:
        self._transfer_selected_to_target(move=False)

    def _move_selected_to_target(self) -> None:
        self._transfer_selected_to_target(move=True)

    def _delete_selected_items(self) -> None:
        panel = self.active_panel()
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is None:
            return
        selected = tab.selected_paths()
        if not selected:
            self.statusBar().showMessage("No items selected in source pane.", 3000)
            return

        names = "\n".join(path.name for path in selected[:10])
        confirm = QMessageBox.question(
            self,
            "Delete to Recycle Bin",
            f"Move selected items to Recycle Bin?\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            file_ops.delete_to_recycle_bin(selected)
            panel.refresh_current_path()
            self.statusBar().showMessage(
                f"Deleted {len(selected)} item(s) from source pane.", 4000
            )
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self, "Delete Failed", str(exc))

    def _transfer_selected_to_target(self, *, move: bool) -> None:
        source_panel = self.active_panel()
        source_id = self._active_panel_id
        if source_panel is None or source_id is None:
            return
        source_tab = source_panel.current_tab()
        if source_tab is None:
            return

        selected = source_tab.selected_paths()
        if not selected:
            self.statusBar().showMessage("No items selected in source pane.", 3000)
            return

        target_id = self._resolve_target_panel_id(source_id)
        if target_id is None:
            QMessageBox.information(
                self,
                "Target Pane",
                "No target pane is available. Create another pane first.",
            )
            return
        target_panel = self.panel_widgets.get(target_id)
        if target_panel is None:
            return
        destination = target_panel.current_path()

        transferred = 0
        for source_path in selected:
            outcome = self._copy_or_move_one(
                source=Path(source_path), destination_dir=destination, move=move
            )
            if outcome == "cancel":
                break
            if outcome == "done":
                transferred += 1

        if transferred > 0:
            source_panel.refresh_current_path()
            target_panel.refresh_current_path()
            verb = "Moved" if move else "Copied"
            self.statusBar().showMessage(
                f"{verb} {transferred} item(s) from pane {source_id} to pane {target_id}.",
                4000,
            )

    def _copy_or_move_one(
        self, *, source: Path, destination_dir: Path, move: bool
    ) -> Literal["done", "skip", "cancel"]:
        destination_dir = Path(destination_dir)
        destination = destination_dir / source.name

        if destination.exists():
            choice = self._prompt_conflict_resolution(source, destination)
            if choice == "cancel":
                return "cancel"
            if choice == "skip":
                return "skip"
            if choice == "rename":
                destination = self._next_available_path(destination_dir, source.name)
            elif choice == "overwrite":
                if source.resolve() == destination.resolve():
                    return "skip"
                self._remove_existing_path(destination)

        try:
            if move:
                shutil.move(str(source), str(destination))
            else:
                if source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self, "File Operation Failed", str(exc))
            return "cancel"
        return "done"

    def _prompt_conflict_resolution(self, source: Path, destination: Path) -> ConflictChoice:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Name Conflict")
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(
            f'"{destination.name}" already exists in target pane.\n\n'
            f"Source: {source}\nTarget: {destination}"
        )
        overwrite_button = dialog.addButton(
            "Overwrite", QMessageBox.ButtonRole.AcceptRole
        )
        skip_button = dialog.addButton("Skip", QMessageBox.ButtonRole.ActionRole)
        rename_button = dialog.addButton("Rename", QMessageBox.ButtonRole.ActionRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is overwrite_button:
            return "overwrite"
        if clicked is skip_button:
            return "skip"
        if clicked is rename_button:
            return "rename"
        _ = cancel_button
        return "cancel"

    def _next_available_path(self, destination_dir: Path, base_name: str) -> Path:
        candidate = destination_dir / base_name
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while True:
            candidate = destination_dir / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _remove_existing_path(self, path: Path) -> None:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
            return
        path.unlink()

    def _resolve_target_panel_id(self, source_panel_id: int) -> int | None:
        ordered = self._ordered_panel_ids(self._layout_rows)
        candidates = [pid for pid in ordered if pid != source_panel_id]
        if not candidates:
            return None
        if self._last_non_source_panel_id in candidates:
            return self._last_non_source_panel_id
        return candidates[0]

    def _update_pane_visuals(self) -> None:
        source_id = self._active_panel_id
        target_id = (
            self._resolve_target_panel_id(source_id) if source_id is not None else None
        )

        for panel_id, panel in self.panel_widgets.items():
            panel.set_role_visual_state(
                is_active=panel_id == source_id,
                is_target=panel_id == target_id,
            )

        if source_id is None:
            self.statusBar().showMessage("")
            return
        if target_id is None:
            self.statusBar().showMessage(f"Source pane: {source_id}", 3000)
            return
        self.statusBar().showMessage(
            f"Source pane: {source_id} | Target pane: {target_id}", 3000
        )

    # ----- persistence -----
    def _encode_geometry(self) -> str:
        geometry = self.saveGeometry()
        encoded = geometry.toBase64().data()
        return bytes(encoded).decode("ascii")

    def _restore_geometry_from_b64(self, encoded: str) -> None:
        raw = QByteArray.fromBase64(encoded.encode("ascii"))
        if not raw.isEmpty():
            self.restoreGeometry(raw)

    def serialize_state(self, *, include_geometry: bool = False) -> dict[str, Any]:
        self._sync_panel_tree_from_rows()
        payload: dict[str, Any] = {
            "window_id": self.window_id,
            "panel_tree": self.panel_tree.to_dict(),
            "tabs": self._serialize_tabs_state(),
            "active_panel_id": self._active_panel_id,
            "on_top": self._on_top_action.isChecked(),
        }
        if include_geometry:
            payload["geometry_b64"] = self._encode_geometry()
        return payload

    def save_to_settings(self) -> None:
        payload = self.serialize_state()
        self.settings.set_json(
            self.settings.window_key(self.window_id, "panel_tree"),
            payload["panel_tree"],
        )

        tabs_payload = {
            "active_panel_id": payload["active_panel_id"],
            "panels": {str(pid): state for pid, state in payload["tabs"].items()},
        }
        self.settings.set_json(
            self.settings.window_key(self.window_id, "tabs"), tabs_payload
        )
        self.settings.set_value(
            self.settings.window_key(self.window_id, "on_top"), payload["on_top"]
        )
        self.settings.set_value(
            self.settings.window_key(self.window_id, "geometry"), self.saveGeometry()
        )

    def restore_from_settings(self) -> None:
        panel_tree_data = self.settings.get_json(
            self.settings.window_key(self.window_id, "panel_tree"), None
        )
        if isinstance(panel_tree_data, dict):
            try:
                self.panel_tree = PanelTreeModel.from_dict(
                    cast("dict[str, Any]", panel_tree_data)
                )
            except Exception as exc:  # pragma: no cover - defensive path
                QMessageBox.warning(
                    self, "Restore", f"Could not restore panel tree: {exc}"
                )
                self.panel_tree = PanelTreeModel()
        self._layout_rows = self._rows_from_tree(self.panel_tree.root)

        tabs_payload_raw = self.settings.get_json(
            self.settings.window_key(self.window_id, "tabs"), {}
        )
        tabs_payload = (
            cast("dict[str, Any]", tabs_payload_raw)
            if isinstance(tabs_payload_raw, dict)
            else {}
        )
        raw_panels_obj = tabs_payload.get("panels", {})
        tabs_state: TabsState = {}
        raw_panels = (
            cast("dict[str, Any]", raw_panels_obj)
            if isinstance(raw_panels_obj, dict)
            else {}
        )
        for panel_id_str, state in raw_panels.items():
            try:
                panel_id = int(panel_id_str)
            except (TypeError, ValueError):
                continue
            if isinstance(state, dict):
                tabs_state[panel_id] = state
        self._layout_rows = self._append_missing_panel_ids(
            self._layout_rows, list(tabs_state.keys())
        )
        self._sync_panel_tree_from_rows()

        preferred_active = None
        raw_active = tabs_payload.get("active_panel_id")
        if raw_active is not None:
            try:
                preferred_active = int(raw_active)
            except (TypeError, ValueError):
                preferred_active = None

        self._rebuild_from_tree(
            tabs_state=tabs_state, preferred_active_panel=preferred_active
        )

        on_top_value = self.settings.value(
            self.settings.window_key(self.window_id, "on_top"), False
        )
        on_top = (
            on_top_value
            if isinstance(on_top_value, bool)
            else str(on_top_value).strip().lower() in {"1", "true", "yes", "on"}
        )
        self.set_on_top(bool(on_top))

        geometry = self.settings.value(
            self.settings.window_key(self.window_id, "geometry")
        )
        if isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)

    def apply_cloned_state(
        self, state: dict[str, Any], *, restore_geometry: bool = False
    ) -> None:
        panel_tree_data = state.get("panel_tree")
        if isinstance(panel_tree_data, dict):
            self.panel_tree = PanelTreeModel.from_dict(
                cast("dict[str, Any]", panel_tree_data)
            )
        self._layout_rows = self._rows_from_tree(self.panel_tree.root)

        tabs_state: TabsState = {}
        raw_tabs = deepcopy(state.get("tabs", {}))
        if isinstance(raw_tabs, dict):
            for panel_id, panel_state in cast("dict[str, Any]", raw_tabs).items():
                try:
                    panel_id_int = int(panel_id)
                except (TypeError, ValueError):
                    continue
                if isinstance(panel_state, dict):
                    tabs_state[panel_id_int] = panel_state
        self._layout_rows = self._append_missing_panel_ids(
            self._layout_rows, list(tabs_state.keys())
        )
        self._sync_panel_tree_from_rows()

        preferred_active_panel: int | None
        raw_active_panel = state.get("active_panel_id")
        try:
            preferred_active_panel = (
                int(raw_active_panel) if raw_active_panel is not None else None
            )
        except (TypeError, ValueError):
            preferred_active_panel = None

        self._rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
        )
        self.set_on_top(bool(state.get("on_top", False)))
        if restore_geometry:
            geometry_b64 = state.get("geometry_b64")
            if isinstance(geometry_b64, str) and geometry_b64:
                self._restore_geometry_from_b64(geometry_b64)

    def _new_panel_state(self, panel_id: int, seed_path: Path) -> PanelState:
        return {
            "panel_id": panel_id,
            "current_index": 0,
            "tabs": [{"path": str(seed_path)}],
        }

    def _default_panel_state(self, panel_id: int) -> PanelState:
        panel = self.panel_widgets.get(panel_id)
        path = panel.current_path() if panel is not None else Path.home()
        return self._new_panel_state(panel_id, path)

    def _find_panel_position(
        self, panel_id: int, rows: PanelRows
    ) -> tuple[int | None, int | None]:
        for row_index, row in enumerate(rows):
            for col_index, row_panel_id in enumerate(row):
                if row_panel_id == panel_id:
                    return row_index, col_index
        return None, None

    def _allocate_panel_id(self, rows: PanelRows, tabs_state: TabsState) -> int:
        ids = set(self._ordered_panel_ids(rows)) | set(tabs_state.keys())
        return (max(ids) + 1) if ids else 1

    @staticmethod
    def _ordered_panel_ids(rows: PanelRows) -> list[int]:
        ordered: list[int] = []
        for row in rows:
            ordered.extend(row)
        return ordered

    def _normalize_rows(self, rows: PanelRows) -> PanelRows:
        normalized: PanelRows = []
        seen: set[int] = set()
        for row in rows:
            cleaned_row: list[int] = []
            for panel_id in row:
                panel_id_int = int(panel_id)
                if panel_id_int in seen:
                    continue
                cleaned_row.append(panel_id_int)
                seen.add(panel_id_int)
            if cleaned_row:
                normalized.append(cleaned_row)
        if not normalized:
            return [[1]]
        return normalized

    def _append_missing_panel_ids(
        self, rows: PanelRows, panel_ids: list[int]
    ) -> PanelRows:
        normalized_rows = self._normalize_rows(rows)
        present = set(self._ordered_panel_ids(normalized_rows))
        missing = [int(panel_id) for panel_id in panel_ids if int(panel_id) not in present]
        if missing:
            normalized_rows.append(missing)
        return self._normalize_rows(normalized_rows)

    def _rows_from_tree(self, node: LeafNode | SplitNode | None) -> PanelRows:
        if node is None:
            return [[1]]

        def split_into_rows(tree_node: LeafNode | SplitNode) -> list[LeafNode | SplitNode]:
            if isinstance(tree_node, LeafNode):
                return [tree_node]
            if tree_node.orientation == ORIENTATION_VERTICAL:
                return split_into_rows(tree_node.left) + split_into_rows(tree_node.right)
            return [tree_node]

        def flatten_row(tree_node: LeafNode | SplitNode) -> list[int]:
            if isinstance(tree_node, LeafNode):
                return [tree_node.panel_id]
            if tree_node.orientation != ORIENTATION_HORIZONTAL:
                raise ValueError("row contains vertical split")
            return flatten_row(tree_node.left) + flatten_row(tree_node.right)

        try:
            rows = [flatten_row(row_node) for row_node in split_into_rows(node)]
        except ValueError:
            rows = [self.panel_tree.leaf_ids()]
        return self._normalize_rows(rows)

    def _sync_panel_tree_from_rows(self) -> None:
        self._layout_rows = self._normalize_rows(self._layout_rows)
        root = self._build_tree_root_from_rows(self._layout_rows)
        self.panel_tree = PanelTreeModel(root=root if root is not None else LeafNode(1))

    def _build_tree_root_from_rows(
        self, rows: PanelRows
    ) -> LeafNode | SplitNode | None:
        if not rows:
            return None

        def build_row(row: list[int]) -> LeafNode | SplitNode:
            if len(row) == 1:
                return LeafNode(panel_id=row[0])
            return SplitNode(
                orientation=ORIENTATION_HORIZONTAL,
                ratio=1.0 / float(len(row)),
                left=LeafNode(panel_id=row[0]),
                right=build_row(row[1:]),
            )

        if len(rows) == 1:
            return build_row(rows[0])
        return SplitNode(
            orientation=ORIENTATION_VERTICAL,
            ratio=1.0 / float(len(rows)),
            left=build_row(rows[0]),
            right=cast("LeafNode | SplitNode", self._build_tree_root_from_rows(rows[1:])),
        )

    def default_close_warning(self) -> bool:
        if len(self.panel_widgets) > 1:
            return True
        panel = self.active_panel()
        return panel is not None and panel.tab_count() > 1
