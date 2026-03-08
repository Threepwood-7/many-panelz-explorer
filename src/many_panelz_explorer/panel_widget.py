from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QRect,
    QStringListModel,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QKeyEvent, QPaintEvent, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QCompleter,
    QComboBox,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .explorer_tab import ExplorerTab
from .mounts import list_roots_for_navigation
from . import widget_naming

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def _tab_label(path: Path) -> str:
    anchor = path.anchor
    if anchor and path == Path(anchor):
        return str(path)
    return path.name or str(path)


def _strip_windows_long_path(path: str) -> str:
    return path[4:] if path.startswith("\\\\?\\") else path


def _is_hidden_or_system_entry(entry: os.DirEntry[str]) -> bool:
    hidden = entry.name.startswith(".")
    if os.name != "nt":
        return hidden
    try:
        stat_result = entry.stat(follow_symlinks=False)
    except OSError:
        return hidden
    attributes = int(getattr(stat_result, "st_file_attributes", 0))
    hidden = hidden or bool(attributes & 0x2)
    system = bool(attributes & 0x4)
    return hidden or system


def _is_path_under_root(path: Path, root: Path) -> bool:
    norm_path = os.path.normcase(os.path.normpath(str(path)))
    norm_root = os.path.normcase(os.path.normpath(str(root)))
    if norm_path == norm_root:
        return True
    prefix = norm_root if norm_root.endswith(os.sep) else f"{norm_root}{os.sep}"
    return norm_path.startswith(prefix)


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


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


@dataclass(frozen=True)
class _WidgetMapEntry:
    widget: QWidget
    alias: str
    widget_id: str


class _WidgetMapOverlay(QWidget):
    def __init__(self, owner: "PanelWidget") -> None:
        super().__init__(owner)
        self._owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()

    def refresh(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        self.raise_()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        _ = event
        entries = self._owner.widget_map_entries()
        if not entries:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        text_flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        for entry in entries:
            widget = entry.widget
            if not widget.isVisible():
                continue
            top_left = widget.mapTo(self, QPoint(0, 0))
            rect = QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)
            if rect.width() <= 2 or rect.height() <= 2:
                continue

            color = QColor("#22c55e")
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            label = f"{entry.alias}"
            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(label) + 12
            text_height = metrics.height() + 8

            label_x = rect.left() + 2
            label_y = rect.top() - text_height - 2
            if label_y < 2:
                label_y = rect.top() + 2
            if label_x + text_width > self.width() - 2:
                label_x = max(2, self.width() - text_width - 2)

            label_rect = QRect(label_x, label_y, text_width, text_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 190))
            painter.drawRoundedRect(label_rect, 4, 4)
            painter.setPen(QColor("#f8fafc"))
            painter.drawText(label_rect.adjusted(6, 0, -6, 0), int(text_flags), label)


class PanelWidget(QWidget):
    COLUMN_SYNC_DEBOUNCE_MS = 120
    ADDRESS_COMPLETION_DEBOUNCE_MS = 140

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
        self._pending_column_widths_sync: list[int] = []
        self._pending_column_widths_source_tab: ExplorerTab | None = None
        self._restoring_state = False
        self.root_buttons: list[QPushButton] = []
        self._history_menu: QMenu | None = None
        self._pane_role = "normal"
        self._show_widget_map = False
        self._address_completions_enabled = True

        self._panel_widget_id = widget_naming.panel_widget_id(self.panel_id)
        self.setObjectName(widget_naming.object_name_for_id(self._panel_widget_id))
        self.setProperty("widget_id", self._panel_widget_id)
        self.setProperty("widget_alias", widget_naming.panel_alias(self.panel_id))
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self.focus_watcher = _FocusWatcher(self)
        self.focus_watcher.focused.connect(self.activated)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        toolbar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMinimumWidth(0)
        self.refresh_btn.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self.refresh_btn)

        self.root_buttons_host = QWidget()
        self.root_buttons_host.setMinimumWidth(0)
        self.root_buttons_host.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.root_buttons_layout = QHBoxLayout(self.root_buttons_host)
        self.root_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.root_buttons_layout.setSpacing(4)
        toolbar.addWidget(self.root_buttons_host, 1)

        self.root_combo = QComboBox()
        self.root_combo.activated.connect(self._on_root_selected)
        self.root_combo.setVisible(self._show_root_dropdown)
        self.root_combo.setMinimumWidth(0)
        self.root_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        toolbar.addWidget(self.root_combo)

        self.address_edit = QLineEdit()
        self.address_edit.returnPressed.connect(self._on_address_submitted)
        self.address_edit.setMinimumWidth(0)
        self.address_edit.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        toolbar.addWidget(self.address_edit, 1)
        self._address_completion_model = QStringListModel(self)
        self._address_completer = QCompleter(self._address_completion_model, self)
        self._address_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._address_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._address_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self._address_completer.setMaxVisibleItems(14)
        self._address_completer.activated[str].connect(
            self._on_address_completion_activated
        )
        self.address_edit.setCompleter(self._address_completer)
        self.address_edit.textEdited.connect(self._schedule_address_completion_update)

        self.back_btn = QPushButton("<")
        self.back_btn.setMinimumWidth(28)
        self.back_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.back_btn.clicked.connect(self._go_back)
        toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton(">")
        self.forward_btn.setMinimumWidth(28)
        self.forward_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.forward_btn.clicked.connect(self._go_forward)
        toolbar.addWidget(self.forward_btn)

        self.up_btn = QPushButton("..")
        self.up_btn.setMinimumWidth(32)
        self.up_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.up_btn.clicked.connect(self._go_up)
        toolbar.addWidget(self.up_btn)

        self.root_btn = QPushButton("\\")
        self.root_btn.setMinimumWidth(28)
        self.root_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.root_btn.clicked.connect(self._go_root)
        toolbar.addWidget(self.root_btn)

        root.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(0)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.tabCloseRequested.connect(self._close_tab_at)
        self.tabs.installEventFilter(self.focus_watcher)
        self.tabs.installEventFilter(self)
        tab_bar = self.tabs.tabBar()
        tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
        tab_bar.setExpanding(True)
        tab_bar.setUsesScrollButtons(False)
        tab_bar.setMinimumWidth(0)

        root.addWidget(self.tabs)

        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter active pane...")
        self.filter_edit.setVisible(False)
        self.filter_edit.setMinimumWidth(0)
        self.filter_edit.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.filter_edit.textChanged.connect(self._on_filter_text_changed)
        self.filter_edit.installEventFilter(self)
        self.installEventFilter(self)
        self._assign_identity(
            self.refresh_btn,
            widget_naming.panel_control_widget_id(self.panel_id, "refresh"),
            widget_naming.panel_control_alias(self.panel_id, "refresh"),
        )
        self._assign_identity(
            self.address_edit,
            widget_naming.panel_control_widget_id(self.panel_id, "address"),
            widget_naming.panel_control_alias(self.panel_id, "address"),
        )
        self._assign_identity(
            self.back_btn,
            widget_naming.panel_control_widget_id(self.panel_id, "back"),
            widget_naming.panel_control_alias(self.panel_id, "back"),
        )
        self._assign_identity(
            self.forward_btn,
            widget_naming.panel_control_widget_id(self.panel_id, "forward"),
            widget_naming.panel_control_alias(self.panel_id, "forward"),
        )
        self._assign_identity(
            self.up_btn,
            widget_naming.panel_control_widget_id(self.panel_id, "up"),
            widget_naming.panel_control_alias(self.panel_id, "up"),
        )
        self._assign_identity(
            self.root_btn,
            widget_naming.panel_control_widget_id(self.panel_id, "root"),
            widget_naming.panel_control_alias(self.panel_id, "root"),
        )
        self._assign_identity(
            self.tabs,
            widget_naming.panel_control_widget_id(self.panel_id, "tabs"),
            widget_naming.panel_control_alias(self.panel_id, "tabs"),
        )
        self._assign_identity(
            self.tabs.tabBar(),
            widget_naming.panel_control_widget_id(self.panel_id, "tab_bar"),
            widget_naming.panel_control_alias(self.panel_id, "tab_bar"),
        )
        self._assign_identity(
            self.filter_edit,
            widget_naming.panel_control_widget_id(self.panel_id, "filter"),
            widget_naming.panel_control_alias(self.panel_id, "filter"),
        )

        self._widget_map_overlay = _WidgetMapOverlay(self)

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
        self._alt_down_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._alt_down_shortcut.activated.connect(self._show_history_menu)
        self._ctrl_f_shortcut = QShortcut("Ctrl+F", self)
        self._ctrl_f_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._ctrl_f_shortcut.activated.connect(
            lambda: self._show_filter_overlay(seed_text="")
        )
        self._column_sync_timer = QTimer(self)
        self._column_sync_timer.setSingleShot(True)
        self._column_sync_timer.timeout.connect(self._flush_pending_column_width_sync)
        self._address_completion_timer = QTimer(self)
        self._address_completion_timer.setSingleShot(True)
        self._address_completion_timer.timeout.connect(self._refresh_address_completions)

        self._sync_toolbar_for_current_tab()
        self._apply_visual_role()
        self._sync_widget_map_overlay()

    def add_tab(self, path: Path) -> ExplorerTab:
        source_tab = self.current_tab()
        source_widths = source_tab.column_widths() if source_tab is not None else []
        tab = ExplorerTab(path, show_hidden=self._show_hidden, parent=self)
        self._assign_tab_identity(tab)

        def _on_path_changed(_path: str, t: ExplorerTab = tab) -> None:
            self._on_tab_path_changed(t)

        def _on_path_retitle(_path: str, t: ExplorerTab = tab) -> None:
            self._retitle_tab(t)

        def _on_history_changed(
            _back: bool, _forward: bool, t: ExplorerTab = tab
        ) -> None:
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
        self._sync_widget_map_overlay()
        return tab

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize and (
            obj is self or self._is_active_files_list_source(obj)
        ):
            self._position_filter_overlay()
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.KeyPress:
            key_event = cast("QKeyEvent", event)
            if obj is self.filter_edit and key_event.key() in {
                int(Qt.Key.Key_Escape),
                int(Qt.Key.Key_Return),
                int(Qt.Key.Key_Enter),
            }:
                if key_event.key() == int(Qt.Key.Key_Escape):
                    self.clear_inline_filter()
                self._hide_filter_overlay()
                self._focus_current_view()
                return True
            if (
                key_event.modifiers() == Qt.KeyboardModifier.AltModifier
                and key_event.key() == int(Qt.Key.Key_Down)
            ):
                self._show_history_menu()
                return True
            if self._is_active_files_list_source(
                obj
            ) and self._should_start_inline_filter(key_event):
                self._show_filter_overlay(seed_text=key_event.text())
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
        if self.address_edit.hasFocus():
            self._schedule_address_completion_update(self.address_edit.text())

    def set_widget_map_enabled(self, enabled: bool) -> None:
        self._show_widget_map = bool(enabled)
        self._sync_widget_map_overlay()

    def widget_map_enabled(self) -> bool:
        return self._show_widget_map

    def widget_map_entries(self) -> list[_WidgetMapEntry]:
        widgets: list[QWidget] = [
            self.tabs,
            self.tabs.tabBar(),
            self.address_edit,
            self.refresh_btn,
            self.back_btn,
            self.forward_btn,
            self.up_btn,
            self.root_btn,
            self.filter_edit,
        ]
        tab = self.current_tab()
        if tab is not None:
            widgets.extend([tab, tab.view])

        entries: list[_WidgetMapEntry] = []
        for widget in widgets:
            entry = self._entry_for_widget(widget)
            if entry is not None:
                entries.append(entry)
        return entries

    def _assign_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        widget.setObjectName(widget_naming.object_name_for_id(widget_id))
        widget.setProperty("widget_id", widget_id)
        widget.setProperty("widget_alias", alias)

    def _assign_tab_identity(self, tab: ExplorerTab) -> None:
        tab_id = widget_naming.tab_widget_id(self.panel_id, tab.tab_uuid)
        tab_alias = widget_naming.tab_alias(self.panel_id, tab.tab_uuid)
        self._assign_identity(tab, tab_id, tab_alias)
        self._assign_identity(
            tab.view,
            widget_naming.file_list_widget_id(self.panel_id, tab.tab_uuid),
            widget_naming.file_list_alias(self.panel_id, tab.tab_uuid),
        )

    def _entry_for_widget(self, widget: QWidget) -> _WidgetMapEntry | None:
        widget_id = str(widget.property("widget_id") or "").strip()
        alias = str(widget.property("widget_alias") or "").strip()
        if not widget_id or not alias:
            return None
        return _WidgetMapEntry(widget=widget, alias=alias, widget_id=widget_id)

    def _sync_widget_map_overlay(self) -> None:
        if not self._show_widget_map:
            self._widget_map_overlay.hide()
            return
        self._widget_map_overlay.show()
        self._widget_map_overlay.refresh()

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
            self._column_widths = self._coerce_column_widths(
                cast("list[object]", raw_widths)
            )

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
        self._sync_widget_map_overlay()

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
            if tab is not None and self.filter_edit.isVisible():
                tab.set_inline_filter(self.filter_edit.text())
        self._sync_toolbar_for_current_tab()
        self._sync_widget_map_overlay()

    def _on_tab_path_changed(self, tab: ExplorerTab) -> None:
        if tab is self.current_tab():
            self._sync_toolbar_for_current_tab()

    def _on_tab_history_changed(self, tab: ExplorerTab) -> None:
        if tab is self.current_tab():
            self._sync_toolbar_for_current_tab()

    def _on_tab_column_widths_changed(
        self, tab: ExplorerTab, widths: list[object]
    ) -> None:
        if self._syncing_column_widths or self._restoring_state:
            return
        if not widths:
            return

        normalized = self._coerce_column_widths(widths)
        if not normalized:
            return
        self._column_widths = normalized
        self._pending_column_widths_sync = list(normalized)
        self._pending_column_widths_source_tab = tab
        self._column_sync_timer.start(self.COLUMN_SYNC_DEBOUNCE_MS)

    def _flush_pending_column_width_sync(self) -> None:
        if not self._pending_column_widths_sync:
            return
        source_tab = self._pending_column_widths_source_tab
        widths = list(self._pending_column_widths_sync)
        self._pending_column_widths_sync = []
        self._pending_column_widths_source_tab = None
        self._apply_column_widths_to_all_tabs(widths, source_tab=source_tab)

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
            self._set_address_text_programmatically("")
            self._rebuild_root_controls(None)
            self._sync_widget_map_overlay()
            return

        self.back_btn.setEnabled(tab.can_go_back())
        self.forward_btn.setEnabled(tab.can_go_forward())
        self.up_btn.setEnabled(True)
        self.root_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self._set_address_text_programmatically(
            _strip_windows_long_path(str(tab.current_path()))
        )
        self._rebuild_root_controls(tab.current_path())
        if self.filter_edit.isVisible():
            tab.set_inline_filter(self.filter_edit.text())
        self._sync_widget_map_overlay()

    def _rebuild_root_controls(self, current_path: Path | None) -> None:
        roots = self._safe_roots(current_path)
        self._root_paths = roots
        self._rebuild_root_buttons(current_path, roots)
        self._rebuild_root_combo(current_path, roots)

    def _rebuild_root_buttons(
        self, current_path: Path | None, roots: list[Path]
    ) -> None:
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
            button.setMinimumWidth(0)
            button.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
            button.setToolTip(_strip_windows_long_path(str(root_path)))
            button.setCheckable(True)
            button.setChecked(
                current_path is not None
                and _is_path_under_root(current_path, root_path)
            )
            button.clicked.connect(
                lambda _checked=False, p=root_path: self._navigate_to_root(p)
            )
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
            provided_roots = [Path(p) for p in self._roots_provider(current_path)]
        except Exception:
            provided_roots = []
        roots = self._existing_unique_paths(provided_roots)
        if not roots:
            roots = self._fallback_roots(current_path)
        return sorted(
            roots,
            key=lambda p: (
                _root_display_text(p).lower(),
                _strip_windows_long_path(str(p)).lower(),
            ),
        )

    def _existing_unique_paths(self, paths: list[Path]) -> list[Path]:
        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in paths:
            path = Path(candidate).expanduser()
            if not path.exists() or not path.is_dir():
                continue
            key = _path_key(path)
            if key in seen:
                continue
            seen.add(key)
            unique.append(path)
        return unique

    def _fallback_roots(self, current_path: Path | None) -> list[Path]:
        candidates: list[Path] = []
        if current_path is not None:
            current = Path(current_path).expanduser()
            candidates.append(current)
            if current.anchor:
                candidates.append(Path(current.anchor))

        home = Path.home()
        candidates.append(home)
        if home.anchor:
            candidates.append(Path(home.anchor))

        root_path = Path(os.sep)
        candidates.append(root_path)

        fallback = self._existing_unique_paths(candidates)
        if fallback:
            return fallback
        return [home]

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
        matches = [
            root for root in self._root_paths if _is_path_under_root(current_path, root)
        ]
        if matches:
            root_path = max(matches, key=lambda p: len(os.path.normpath(str(p))))
            tab.set_path(root_path)
            return

        if current_path.anchor:
            tab.set_path(Path(current_path.anchor))

    def refresh_current_path(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.refresh()

    def _refresh(self) -> None:
        self.refresh_current_path()

    def _on_address_submitted(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return

        text = self.address_edit.text().strip()
        if not text:
            return
        self._address_completion_timer.stop()
        self._hide_address_completion_popup()
        tab.set_path(Path(text))

    def _set_address_text_programmatically(self, text: str) -> None:
        self._address_completions_enabled = False
        try:
            self.address_edit.setText(text)
        finally:
            self._address_completions_enabled = True
        self._address_completion_timer.stop()
        self._address_completion_model.setStringList([])
        self._hide_address_completion_popup()

    def _schedule_address_completion_update(self, _text: str) -> None:
        if not self._address_completions_enabled:
            return
        self._address_completion_timer.start(self.ADDRESS_COMPLETION_DEBOUNCE_MS)

    def _refresh_address_completions(self) -> None:
        if not self._address_completions_enabled or not self.address_edit.hasFocus():
            self._hide_address_completion_popup()
            return
        raw_text = self.address_edit.text().strip()
        suggestions = self._collect_address_completion_paths(raw_text)
        self._address_completion_model.setStringList(suggestions)
        if not suggestions:
            self._hide_address_completion_popup()
            return
        self._address_completer.setCompletionPrefix("")
        self._address_completer.complete(self.address_edit.rect())

    def _on_address_completion_activated(self, path_text: str) -> None:
        selected = str(path_text).strip()
        if not selected:
            return
        self._set_address_text_programmatically(selected)
        self.address_edit.setFocus()
        self.address_edit.setCursorPosition(len(selected))

    def _hide_address_completion_popup(self) -> None:
        popup = self._address_completer.popup()
        if popup.isVisible():
            popup.hide()

    def _collect_address_completion_paths(self, raw_text: str) -> list[str]:
        context = self._resolve_address_completion_context(raw_text)
        if context is None:
            return []
        parent_dir, prefix = context
        if not parent_dir.exists() or not parent_dir.is_dir():
            return []

        prefix_cmp = prefix.casefold()
        suggestions: list[str] = []
        try:
            with os.scandir(parent_dir) as iterator:
                for entry in iterator:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    if not is_dir:
                        continue
                    if not self._show_hidden and _is_hidden_or_system_entry(entry):
                        continue
                    name = entry.name
                    if prefix_cmp and not name.casefold().startswith(prefix_cmp):
                        continue
                    suggestions.append(
                        _strip_windows_long_path(str(parent_dir / name))
                    )
        except OSError:
            return []
        return sorted(set(suggestions), key=str.casefold)

    def _resolve_address_completion_context(
        self, raw_text: str
    ) -> tuple[Path, str] | None:
        text = str(raw_text or "").strip()
        if not text:
            return None

        base_path = self.current_path()
        expanded = os.path.expanduser(text)
        has_trailing_separator = expanded.endswith(("\\", "/"))
        candidate = Path(expanded)
        if has_trailing_separator:
            parent_dir = candidate if candidate.is_absolute() else (base_path / candidate)
            return parent_dir.expanduser(), ""

        prefix = candidate.name
        parent_part = candidate.parent
        if candidate.is_absolute():
            parent_dir = parent_part if str(parent_part) not in {"", "."} else candidate
        else:
            parent_dir = base_path if str(parent_part) in {"", "."} else (base_path / parent_part)
        return parent_dir.expanduser(), prefix

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
            action.triggered.connect(
                lambda _checked=False, i=index: tab.go_to_history_index(i)
            )

        self._history_menu = menu
        menu.popup(self.address_edit.mapToGlobal(self.address_edit.rect().bottomLeft()))

    def set_role_visual_state(self, *, is_active: bool, is_target: bool) -> None:
        if is_active:
            self._pane_role = "active"
        elif is_target:
            self._pane_role = "target"
        else:
            self._pane_role = "normal"
        self._apply_visual_role()
        self._sync_widget_map_overlay()

    def clear_inline_filter(self) -> None:
        self.filter_edit.blockSignals(True)
        self.filter_edit.setText("")
        self.filter_edit.blockSignals(False)
        tab = self.current_tab()
        if tab is not None:
            tab.clear_inline_filter()

    def _position_filter_overlay(self) -> None:
        margin = 8
        height = 30
        tab = self.current_tab()
        if tab is not None:
            view = tab.view
            view_top_left = view.mapTo(self, QPoint(0, 0))
            view_width = max(1, view.width())
            view_height = max(1, view.height())
            desired_width = max(220, int(view_width * 0.35))
            max_width = max(1, view_width - (margin * 2))
            width = min(desired_width, max_width)
            x = max(
                view_top_left.x() + margin,
                view_top_left.x() + view_width - margin - width,
            )
            y = max(
                view_top_left.y() + margin,
                view_top_left.y() + view_height - margin - height,
            )
            self.filter_edit.setGeometry(x, y, width, height)
            self.filter_edit.raise_()
            self._sync_widget_map_overlay()
            return

        width = max(220, int(self.width() * 0.35))
        x = max(margin, self.width() - width - margin)
        self.filter_edit.setGeometry(x, margin, width, height)
        self.filter_edit.raise_()
        self._sync_widget_map_overlay()

    def _show_filter_overlay(self, *, seed_text: str) -> None:
        self._position_filter_overlay()
        self.filter_edit.setVisible(True)
        self.filter_edit.raise_()
        self._sync_widget_map_overlay()
        self.filter_edit.setFocus()
        if seed_text:
            self.filter_edit.setText(self.filter_edit.text() + seed_text)
            self.filter_edit.setCursorPosition(len(self.filter_edit.text()))

    def _hide_filter_overlay(self) -> None:
        self.filter_edit.setVisible(False)
        self._sync_widget_map_overlay()

    def _on_filter_text_changed(self, text: str) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.set_inline_filter(text)

    def _should_start_inline_filter(self, key_event: QKeyEvent) -> bool:
        if key_event.modifiers() not in {
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        }:
            return False
        text = key_event.text()
        if not text:
            return False
        if len(text) != 1 or text.isspace():
            return False
        return text.isprintable()

    def _is_active_files_list_source(self, obj: QObject) -> bool:
        tab = self.current_tab()
        if tab is None:
            return False
        return obj is tab.view

    def _focus_current_view(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.view.setFocus()

    def _apply_visual_role(self) -> None:
        if self._pane_role == "active":
            color = "#f4b400"
        elif self._pane_role == "target":
            color = "#0088cc"
        else:
            color = "#555555"
        panel_object_name = self.objectName()
        self.setStyleSheet(
            f"QWidget#{panel_object_name} {{ border: 2px solid {color}; border-radius: 2px; }}"
        )
