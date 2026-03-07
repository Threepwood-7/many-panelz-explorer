from __future__ import annotations

import uuid
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QByteArray, QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
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

from .panel_tree import (
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
type RootsProvider = Callable[[Path | None], list[Path]]


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
        self._splitter_nodes: dict[QSplitter, SplitNode] = {}

        self.panel_tree = PanelTreeModel()
        self.panel_widgets: dict[int, PanelWidget] = {}

        self._central = QWidget(self)
        self._central_layout = QVBoxLayout(self._central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self._central)

        self._show_hidden = self.settings.show_hidden_default

        self._build_actions()
        self._build_menus()

        self.setWindowTitle("Many Panelz Explorer")
        self.setWindowFlag(Qt.WindowType.Window, True)

        empty_state: TabsState = {}
        self._rebuild_from_tree(tabs_state=empty_state, preferred_active_panel=None)

    # ----- public API -----
    def split_active_panel(self, orientation: Qt.Orientation) -> None:
        active_panel = self.active_panel()
        if self._active_panel_id is None or active_panel is None:
            return

        tabs_state = self._serialize_tabs_state()
        orientation_value = 1 if orientation == Qt.Orientation.Horizontal else 2
        new_panel_id = self.panel_tree.split_leaf(
            self._active_panel_id, orientation_value
        )

        seed_path = self._resolve_new_context_path(active_panel.current_path())
        tabs_state[new_panel_id] = {
            "panel_id": new_panel_id,
            "current_index": 0,
            "tabs": [{"path": str(seed_path)}],
        }

        self._rebuild_from_tree(
            tabs_state=tabs_state, preferred_active_panel=new_panel_id
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
        source_state = tabs_state.get(self._active_panel_id)

        orientation_value = 1 if orientation == Qt.Orientation.Horizontal else 2
        new_panel_id = self.panel_tree.split_leaf(
            self._active_panel_id, orientation_value
        )

        if source_state is None:
            source_panel = self.active_panel()
            source_path = (
                source_panel.current_path() if source_panel is not None else Path.home()
            )
            source_state = {
                "panel_id": self._active_panel_id,
                "current_index": 0,
                "tabs": [{"path": str(source_path)}],
            }

        cloned_state = cast("PanelState", deepcopy(source_state))
        cloned_state["panel_id"] = new_panel_id
        tabs_state[new_panel_id] = cloned_state
        self._rebuild_from_tree(
            tabs_state=tabs_state, preferred_active_panel=new_panel_id
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
        self._refresh_action.setShortcut(QKeySequence("F5"))
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

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = QMenu("&File", self)
        file_menu.addAction(self._new_tab_action)
        file_menu.addAction(self._new_vertical_panel_action)
        file_menu.addAction(self._new_horizontal_panel_action)
        file_menu.addAction(self._clone_vertical_panel_action)
        file_menu.addAction(self._clone_horizontal_panel_action)
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

        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(view_menu)
        menu_bar.addMenu(help_menu)

        self.addActions(
            [
                self._new_tab_action,
                self._new_vertical_panel_action,
                self._new_horizontal_panel_action,
                self._clone_vertical_panel_action,
                self._clone_horizontal_panel_action,
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

    def _refresh_active_panel(self) -> None:
        panel = self.active_panel()
        if panel is not None:
            panel.refresh_current_path()

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "Help",
            "Keyboard shortcuts:\n"
            "F5: Refresh active panel\n"
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
                widget.setParent(None)
                widget.deleteLater()

    def _rebuild_from_tree(
        self,
        tabs_state: TabsState,
        preferred_active_panel: int | None,
    ) -> None:
        self._splitter_nodes = {}

        new_panel_widgets: dict[int, PanelWidget] = {}
        for panel_id in self.panel_tree.leaf_ids():
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

        root_widget = self._build_widget_tree(self.panel_tree.root)
        if root_widget is None:
            placeholder = QWidget(self)
            root_widget = placeholder

        self._clear_layout()
        self._central_layout.addWidget(root_widget)

        target_active = preferred_active_panel
        if target_active is None or target_active not in self.panel_widgets:
            target_active = next(iter(self.panel_widgets), None)
        if target_active is not None:
            self._set_active_panel(target_active)

    def _build_widget_tree(self, node: LeafNode | SplitNode | None) -> QWidget | None:
        if node is None:
            return None
        if isinstance(node, LeafNode):
            return self.panel_widgets[node.panel_id]

        splitter = QSplitter(Qt.Orientation(node.orientation), self)
        left_widget = self._build_widget_tree(node.left)
        right_widget = self._build_widget_tree(node.right)
        splitter.addWidget(left_widget if left_widget is not None else QWidget(self))
        splitter.addWidget(right_widget if right_widget is not None else QWidget(self))

        splitter.setChildrenCollapsible(False)
        left_size = max(1, int(node.ratio * 1000))
        splitter.setSizes([left_size, max(1, 1000 - left_size)])

        def _on_splitter_moved(_pos: int, _index: int) -> None:
            self._update_split_ratio(splitter, node)

        splitter.splitterMoved.connect(_on_splitter_moved)
        self._splitter_nodes[splitter] = node

        return splitter

    def _update_split_ratio(self, splitter: QSplitter, node: SplitNode) -> None:
        sizes = splitter.sizes()
        if len(sizes) != 2:
            return
        total = sizes[0] + sizes[1]
        if total <= 0:
            return
        node.ratio = sizes[0] / total

    def _set_active_panel(self, panel_id: int) -> None:
        if panel_id in self.panel_widgets:
            self._active_panel_id = panel_id

    def active_panel(self) -> PanelWidget | None:
        if self._active_panel_id is None:
            return None
        return self.panel_widgets.get(self._active_panel_id)

    def _close_panel_by_id(self, panel_id: int) -> None:
        if panel_id not in self.panel_widgets:
            return

        tabs_state = self._serialize_tabs_state()
        result = self.panel_tree.remove_leaf(panel_id)
        if not result["removed"]:
            return

        tabs_state.pop(panel_id, None)
        if result["removed_last"]:
            self.close()
            return

        remaining = result["remaining_panel_ids"]
        preferred = remaining[0] if remaining else None
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

    def default_close_warning(self) -> bool:
        if len(self.panel_widgets) > 1:
            return True
        panel = self.active_panel()
        return panel is not None and panel.tab_count() > 1
