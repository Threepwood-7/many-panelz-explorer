from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .explorer_tab import ExplorerTab
from .mounts import list_roots_for_navigation

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def _tab_label(path: Path) -> str:
    anchor = path.anchor
    if anchor and path == Path(anchor):
        return str(path)
    return path.name or str(path)


def _strip_windows_long_path(path: str) -> str:
    return path[4:] if path.startswith("\\\\?\\") else path


def _is_path_under_root(path: Path, root: Path) -> bool:
    norm_path = os.path.normcase(os.path.normpath(str(path)))
    norm_root = os.path.normcase(os.path.normpath(str(root)))
    if norm_path == norm_root:
        return True
    prefix = norm_root if norm_root.endswith(os.sep) else f"{norm_root}{os.sep}"
    return norm_path.startswith(prefix)


def _is_windows() -> bool:
    return os.name == "nt"


def _is_drive_root(path: Path) -> bool:
    drive = path.drive
    if drive:
        drive_root = Path(f"{drive}{os.sep}")
        if os.path.normcase(os.path.normpath(str(path))) == os.path.normcase(
            os.path.normpath(str(drive_root))
        ):
            return True
    return False


def _root_display_text(path: Path) -> str:
    if _is_drive_root(path):
        return path.drive
    if _is_windows():
        name = path.name.strip()
        if name:
            return name
    return _strip_windows_long_path(str(path))


class _FocusWatcher(QObject):
    focused = Signal()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in {QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress}:
            self.focused.emit()
        return super().eventFilter(obj, event)


class PanelWidget(QWidget):
    activated = Signal()
    became_empty = Signal()

    def __init__(
        self,
        panel_id: int,
        default_path: Path,
        show_hidden: bool,
        show_root_dropdown: bool = False,
        roots_provider: Callable[[Path | None], list[Path]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self._show_hidden = show_hidden
        self._show_root_dropdown = bool(show_root_dropdown)
        self._default_path = Path(default_path)
        self._roots_provider = roots_provider or list_roots_for_navigation
        self._root_paths: list[Path] = []
        self._column_widths: list[int] = []
        self._syncing_column_widths = False
        self._restoring_state = False
        self.root_buttons: list[QPushButton] = []
        self._history_menu: QMenu | None = None

        self.focus_watcher = _FocusWatcher(self)
        self.focus_watcher.focused.connect(self.activated)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()

        self.back_btn = QPushButton("<")
        self.back_btn.clicked.connect(self._go_back)
        toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton(">")
        self.forward_btn.clicked.connect(self._go_forward)
        toolbar.addWidget(self.forward_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self.refresh_btn)

        self.root_buttons_host = QWidget()
        self.root_buttons_layout = QHBoxLayout(self.root_buttons_host)
        self.root_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.root_buttons_layout.setSpacing(4)
        toolbar.addWidget(self.root_buttons_host)

        self.root_combo = QComboBox()
        self.root_combo.setMinimumWidth(180)
        self.root_combo.activated.connect(self._on_root_selected)
        self.root_combo.setVisible(self._show_root_dropdown)
        toolbar.addWidget(self.root_combo)

        self.address_edit = QLineEdit()
        self.address_edit.returnPressed.connect(self._on_address_submitted)
        toolbar.addWidget(self.address_edit, 1)

        self.up_btn = QPushButton("..")
        self.up_btn.clicked.connect(self._go_up)
        toolbar.addWidget(self.up_btn)

        self.root_btn = QPushButton("\\")
        self.root_btn.clicked.connect(self._go_root)
        toolbar.addWidget(self.root_btn)

        root.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.tabCloseRequested.connect(self._close_tab_at)
        self.tabs.installEventFilter(self.focus_watcher)
        self.tabs.installEventFilter(self)

        root.addWidget(self.tabs)

        self.back_btn.installEventFilter(self.focus_watcher)
        self.forward_btn.installEventFilter(self.focus_watcher)
        self.up_btn.installEventFilter(self.focus_watcher)
        self.root_btn.installEventFilter(self.focus_watcher)
        self.refresh_btn.installEventFilter(self.focus_watcher)
        self.root_buttons_host.installEventFilter(self.focus_watcher)
        self.root_combo.installEventFilter(self.focus_watcher)
        self.address_edit.installEventFilter(self.focus_watcher)
        self.address_edit.installEventFilter(self)

        self._alt_down_shortcut = QShortcut("Alt+Down", self)
        self._alt_down_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._alt_down_shortcut.activated.connect(self._show_history_menu)

        self._sync_toolbar_for_current_tab()

    def add_tab(self, path: Path) -> ExplorerTab:
        source_tab = self.current_tab()
        source_widths = source_tab.column_widths() if source_tab is not None else []
        tab = ExplorerTab(path, show_hidden=self._show_hidden, parent=self)

        def _on_path_changed(_path: str, t: ExplorerTab = tab) -> None:
            self._on_tab_path_changed(t)

        def _on_path_retitle(_path: str, t: ExplorerTab = tab) -> None:
            self._retitle_tab(t)

        def _on_history_changed(_back: bool, _forward: bool, t: ExplorerTab = tab) -> None:
            self._on_tab_history_changed(t)

        def _on_widths_changed(widths: list[object], t: ExplorerTab = tab) -> None:
            self._on_tab_column_widths_changed(t, widths)

        tab.path_changed.connect(_on_path_changed)
        tab.path_changed.connect(_on_path_retitle)
        tab.history_changed.connect(_on_history_changed)
        tab.column_widths_changed.connect(_on_widths_changed)

        tab.installEventFilter(self.focus_watcher)
        tab.view.installEventFilter(self.focus_watcher)
        tab.installEventFilter(self)
        tab.view.installEventFilter(self)

        self.tabs.addTab(tab, _tab_label(path))
        self.tabs.setCurrentWidget(tab)
        self._retitle_tab(tab)
        if source_widths and not self._restoring_state:
            self._column_widths = self._coerce_column_widths(source_widths)
        if self._column_widths:
            tab.apply_column_widths(self._column_widths)
        else:
            self._column_widths = tab.column_widths()
        self._sync_toolbar_for_current_tab()
        self.activated.emit()
        return tab

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            key_event = cast("QKeyEvent", event)
            if (
                key_event.modifiers() == Qt.KeyboardModifier.AltModifier
                and key_event.key() == int(Qt.Key.Key_Down)
            ):
                self._show_history_menu()
                return True
        return super().eventFilter(obj, event)

    def close_current_tab(self) -> None:
        index = self.tabs.currentIndex()
        if index < 0:
            return
        self._close_tab_at(index)

    def current_path(self) -> Path:
        tab = self.current_tab()
        return tab.current_path() if tab else self._default_path

    def current_tab(self) -> ExplorerTab | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, ExplorerTab) else None

    def tab_count(self) -> int:
        return self.tabs.count()

    def set_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, ExplorerTab):
                widget.set_show_hidden(self._show_hidden)

    def serialize_state(self) -> dict[str, object]:
        tabs: list[dict[str, str]] = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, ExplorerTab):
                tabs.append(widget.serialize_state())

        return {
            "panel_id": self.panel_id,
            "current_index": self.tabs.currentIndex(),
            "tabs": tabs,
            "column_widths": list(self._column_widths),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        raw_widths = state.get("column_widths", [])
        if isinstance(raw_widths, list):
            self._column_widths = self._coerce_column_widths(cast("list[object]", raw_widths))

        self._restoring_state = True
        try:
            tabs = state.get("tabs", [])
            if not isinstance(tabs, list) or not tabs:
                self.add_tab(self._default_path)
                if self._column_widths:
                    self._apply_column_widths_to_all_tabs(self._column_widths)
                return

            for tab_state_raw in cast("list[Any]", tabs):
                if not isinstance(tab_state_raw, dict):
                    continue
                tab_state = cast("dict[str, Any]", tab_state_raw)
                path_value = tab_state.get("path", str(self._default_path))
                path = Path(str(path_value))
                self.add_tab(path)

            current_index_raw = state.get("current_index", 0)
            try:
                current_index = int(current_index_raw)
            except (TypeError, ValueError):
                current_index = 0
            current_index = max(0, min(current_index, self.tabs.count() - 1))
            self.tabs.setCurrentIndex(current_index)
            if self._column_widths:
                self._apply_column_widths_to_all_tabs(self._column_widths)
            self._sync_toolbar_for_current_tab()
        finally:
            self._restoring_state = False

    def _close_tab_at(self, index: int) -> None:
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        if self.tabs.count() == 0:
            self.became_empty.emit()
            return
        self._sync_toolbar_for_current_tab()

    def _retitle_tab(self, tab: ExplorerTab) -> None:
        index = self.tabs.indexOf(tab)
        if index == -1:
            return
        self.tabs.setTabText(index, _tab_label(tab.current_path()))

    def _on_current_changed(self, index: int) -> None:
        if index >= 0:
            self.activated.emit()
            tab = self.current_tab()
            if tab is not None and self._column_widths:
                tab.apply_column_widths(self._column_widths)
        self._sync_toolbar_for_current_tab()

    def _on_tab_path_changed(self, tab: ExplorerTab) -> None:
        if tab is self.current_tab():
            self._sync_toolbar_for_current_tab()

    def _on_tab_history_changed(self, tab: ExplorerTab) -> None:
        if tab is self.current_tab():
            self._sync_toolbar_for_current_tab()

    def _on_tab_column_widths_changed(self, tab: ExplorerTab, widths: list[object]) -> None:
        if self._syncing_column_widths or self._restoring_state:
            return
        if not widths:
            return

        normalized = self._coerce_column_widths(widths)
        if not normalized:
            return
        self._column_widths = normalized
        self._apply_column_widths_to_all_tabs(self._column_widths, source_tab=tab)

    def _apply_column_widths_to_all_tabs(
        self,
        widths: list[int],
        *,
        source_tab: ExplorerTab | None = None,
    ) -> None:
        self._syncing_column_widths = True
        try:
            for index in range(self.tabs.count()):
                widget = self.tabs.widget(index)
                if not isinstance(widget, ExplorerTab):
                    continue
                if source_tab is not None and widget is source_tab:
                    continue
                widget.apply_column_widths(widths)
        finally:
            self._syncing_column_widths = False

    def _coerce_column_widths(self, widths: Sequence[object]) -> list[int]:
        normalized: list[int] = []
        for width in widths:
            if isinstance(width, bool):
                value = int(width)
            elif isinstance(width, int):
                value = width
            elif isinstance(width, float):
                value = int(width)
            elif isinstance(width, str):
                try:
                    value = int(width)
                except ValueError:
                    continue
            else:
                continue
            if value > 0:
                normalized.append(value)
        return normalized

    def _sync_toolbar_for_current_tab(self) -> None:
        tab = self.current_tab()
        if tab is None:
            self.back_btn.setEnabled(False)
            self.forward_btn.setEnabled(False)
            self.up_btn.setEnabled(False)
            self.root_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.address_edit.setText("")
            self._rebuild_root_controls(None)
            return

        self.back_btn.setEnabled(tab.can_go_back())
        self.forward_btn.setEnabled(tab.can_go_forward())
        self.up_btn.setEnabled(True)
        self.root_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.address_edit.setText(_strip_windows_long_path(str(tab.current_path())))
        self._rebuild_root_controls(tab.current_path())

    def _rebuild_root_controls(self, current_path: Path | None) -> None:
        roots = self._safe_roots(current_path)
        self._root_paths = roots
        self._rebuild_root_buttons(current_path, roots)
        self._rebuild_root_combo(current_path, roots)

    def _rebuild_root_buttons(self, current_path: Path | None, roots: list[Path]) -> None:
        while self.root_buttons_layout.count():
            item = self.root_buttons_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.root_buttons = []
        for root_path in roots:
            button = QPushButton(_root_display_text(root_path))
            button.setToolTip(_strip_windows_long_path(str(root_path)))
            button.setCheckable(True)
            button.setChecked(current_path is not None and _is_path_under_root(current_path, root_path))
            button.clicked.connect(lambda _checked=False, p=root_path: self._navigate_to_root(p))
            button.installEventFilter(self.focus_watcher)
            self.root_buttons_layout.addWidget(button)
            self.root_buttons.append(button)

        self.root_buttons_layout.addStretch(1)

    def _rebuild_root_combo(self, current_path: Path | None, roots: list[Path]) -> None:
        self.root_combo.setVisible(self._show_root_dropdown)
        if not self._show_root_dropdown:
            return

        self.root_combo.blockSignals(True)
        try:
            self.root_combo.clear()
            for root_path in roots:
                self.root_combo.addItem(_root_display_text(root_path), str(root_path))
                combo_idx = self.root_combo.count() - 1
                self.root_combo.setItemData(
                    combo_idx,
                    _strip_windows_long_path(str(root_path)),
                    Qt.ItemDataRole.ToolTipRole,
                )

            if current_path is None:
                return

            match_index = -1
            for index, root_path in enumerate(roots):
                if _is_path_under_root(current_path, root_path):
                    match_index = index
                    break

            if match_index >= 0:
                self.root_combo.setCurrentIndex(match_index)
        finally:
            self.root_combo.blockSignals(False)

    def _safe_roots(self, current_path: Path | None) -> list[Path]:
        try:
            roots = [Path(p) for p in self._roots_provider(current_path)]
        except Exception:
            return []
        return sorted(
            roots,
            key=lambda p: (
                _root_display_text(p).lower(),
                _strip_windows_long_path(str(p)).lower(),
            ),
        )

    def _go_back(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.go_back()

    def _go_forward(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.go_forward()

    def _go_up(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.go_up()

    def _go_root(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return

        current_path = tab.current_path()
        matches = [root for root in self._root_paths if _is_path_under_root(current_path, root)]
        if matches:
            root_path = max(matches, key=lambda p: len(os.path.normpath(str(p))))
            tab.set_path(root_path)
            return

        if current_path.anchor:
            tab.set_path(Path(current_path.anchor))

    def _refresh(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.refresh()

    def _on_address_submitted(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return

        text = self.address_edit.text().strip()
        if not text:
            return
        tab.set_path(Path(text))

    def _on_root_selected(self, index: int) -> None:
        if index < 0 or index >= len(self._root_paths):
            return
        self._navigate_to_root(self._root_paths[index])

    def _navigate_to_root(self, root_path: Path) -> None:
        tab = self.current_tab()
        if tab is None:
            return
        tab.set_path(root_path)

    def _show_history_menu(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return

        history_entries, current_index = tab.history_snapshot()
        if not history_entries:
            return

        if self._history_menu is not None:
            self._history_menu.close()
            self._history_menu.deleteLater()
            self._history_menu = None

        menu = QMenu(self)
        for index in range(len(history_entries) - 1, -1, -1):
            entry = history_entries[index]
            action = menu.addAction(_strip_windows_long_path(str(entry)))
            action.setToolTip(_strip_windows_long_path(str(entry)))
            action.setCheckable(True)
            action.setChecked(index == current_index)
            action.triggered.connect(lambda _checked=False, i=index: tab.go_to_history_index(i))

        self._history_menu = menu
        menu.popup(self.address_edit.mapToGlobal(self.address_edit.rect().bottomLeft()))
