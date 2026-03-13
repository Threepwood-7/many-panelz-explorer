"""Panel widget that hosts navigation controls and explorer tabs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import (
    QEvent,
    QObject,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from threep_commons.fs_paths import display_path_text
from threep_commons.qt.widget_identity import assign_widget_identity

from . import widget_naming
from .explorer_tab import ExplorerTab
from .mounts import list_roots_for_navigation
from .ui.panel import (
    PanelInlineFilterCoordinator,
    PanelNavigationCoordinator,
    PanelPresentationCoordinator,
    PanelStateCoordinator,
    PanelWidgetMapCoordinator,
    assign_panel_control_identities,
    build_panel_filter,
    build_panel_tabs,
    build_panel_toolbar,
    configure_panel_shortcuts_and_timers,
    finalize_panel_ui,
    install_panel_focus_watchers,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtCore import QStringListModel, QTimer
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import QCompleter, QHBoxLayout, QTabWidget


def _tab_label(path: Path) -> str:
    anchor = path.anchor
    if anchor and path == Path(anchor):
        return display_path_text(path)
    return path.name or display_path_text(path)


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


class _FocusWatcher(QObject):
    focused = Signal()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in {QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress}:
            self.focused.emit()
        return super().eventFilter(obj, event)


class PanelWidget(QWidget):
    """Own one pane of tabs, navigation widgets, and focus state."""

    COLUMN_SYNC_DEBOUNCE_MS = 120
    ADDRESS_COMPLETION_DEBOUNCE_MS = 140
    ROOT_COMBO_MIN_WIDTH = 108
    COLUMN_ALIGN_MODE_ALL_PANELS_TABS = "all_panels_tabs"
    COLUMN_ALIGN_MODE_CURRENT_PANEL_TABS = "current_panel_tabs"
    COLUMN_ALIGN_MODE_NONE = "none"

    activated = Signal()
    current_context_changed = Signal()
    column_widths_sync_requested = Signal(list, object)
    became_empty = Signal()
    focus_watcher: _FocusWatcher
    refresh_btn: QPushButton
    root_buttons_host: QWidget
    root_buttons_layout: QHBoxLayout
    root_combo: QComboBox
    address_edit: QLineEdit
    back_btn: QPushButton
    forward_btn: QPushButton
    up_btn: QPushButton
    root_btn: QPushButton
    navigation_buttons: list[QPushButton]
    tabs: QTabWidget
    filter_edit: QLineEdit
    column_sync_timer: QTimer
    address_completion_model: QStringListModel
    address_completer: QCompleter
    alt_down_shortcut: QShortcut
    ctrl_f_shortcut: QShortcut
    address_completion_timer: QTimer

    def __init__(
        self,
        panel_id: int,
        default_path: Path,
        show_hidden: bool,
        show_root_dropdown: bool = False,
        roots_provider: Callable[[Path | None], list[Path]] | None = None,
        parent: QWidget | None = None,
        *,
        file_list_size_formatter: Callable[[int], str] | None = None,
        properties_size_formatter: Callable[[int], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self._show_hidden = show_hidden
        self.show_root_dropdown = bool(show_root_dropdown)
        self.default_path = Path(default_path)
        self._roots_provider = roots_provider or list_roots_for_navigation
        self._root_paths: list[Path] = []
        self.column_widths: list[int] = []
        self.syncing_column_widths = False
        self.pending_column_widths_sync: list[int] = []
        self.pending_column_widths_source_tab: ExplorerTab | None = None
        self.restoring_state = False
        self.column_width_auto_align_mode = self.COLUMN_ALIGN_MODE_CURRENT_PANEL_TABS
        self.root_buttons: list[QPushButton] = []
        self._history_menu: QMenu | None = None
        self.pane_role = "normal"
        self._address_completions_enabled = True
        self.active_role_color = QColor("#A8B6C4")
        self.active_role_intensity_percent = 24
        self.target_role_color = QColor("#D2CCAA")
        self.target_role_intensity_percent = 28
        self.show_refresh_button = True
        self.show_root_buttons = True
        self.show_address_bar = True
        self.show_navigation_buttons = True
        self.file_list_font_value = QFont(self.font())
        self.navigation_font_value = QFont(self.font())
        self.file_list_size_formatter = (
            file_list_size_formatter or self.default_file_list_size_formatter
        )
        self.properties_size_formatter = (
            properties_size_formatter or self.default_properties_size_formatter
        )
        self.navigation_coordinator = PanelNavigationCoordinator(
            self,
            is_hidden_or_system_entry=_is_hidden_or_system_entry,
        )
        self.inline_filter_coordinator = PanelInlineFilterCoordinator(self)
        self.presentation_coordinator = PanelPresentationCoordinator(self)
        self.state_coordinator = PanelStateCoordinator(self)
        self.widget_map_coordinator = PanelWidgetMapCoordinator(self)

        self._panel_widget_id = widget_naming.panel_widget_id(self.panel_id)
        assign_widget_identity(
            self,
            widget_id=self._panel_widget_id,
            widget_alias=widget_naming.panel_alias(self.panel_id),
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self.focus_watcher = _FocusWatcher(self)
        self.focus_watcher.focused.connect(self.activated)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        build_panel_toolbar(self, root)
        build_panel_tabs(self, root)
        build_panel_filter(self)
        assign_panel_control_identities(self)
        install_panel_focus_watchers(self)
        configure_panel_shortcuts_and_timers(self)
        finalize_panel_ui(self)

    def add_tab(self, path: Path) -> ExplorerTab:
        source_tab = self.current_tab()
        source_widths = (
            list(source_tab.columns.widths) if source_tab is not None else []
        )
        tab = ExplorerTab(
            path,
            show_hidden=self._show_hidden,
            file_list_size_formatter=self.file_list_size_formatter,
            properties_size_formatter=self.properties_size_formatter,
            parent=self,
        )
        self.widget_map_coordinator.assign_tab_identity(tab)

        def _on_navigation_changed(t: ExplorerTab = tab) -> None:
            self.state_coordinator.on_tab_navigation_changed(t)

        def _on_widths_changed(widths: object, t: ExplorerTab = tab) -> None:
            self.state_coordinator.on_tab_column_widths_changed(t, widths)

        tab.navigation.changed.connect(_on_navigation_changed)
        tab.columns.changed.connect(_on_widths_changed)
        tab.view.setFont(self.file_list_font_value)

        tab.installEventFilter(self.focus_watcher)
        tab.view.installEventFilter(self.focus_watcher)
        tab.installEventFilter(self)
        tab.view.installEventFilter(self)

        self.tabs.addTab(tab, _tab_label(path))
        self.tabs.setCurrentWidget(tab)
        self.retitle_tab(tab)
        self.state_coordinator.initialize_new_tab_column_widths(
            tab=tab,
            source_widths=source_widths,
        )
        self.presentation_coordinator.sync_toolbar_for_current_tab()
        self.activated.emit()
        self.widget_map_coordinator.sync_overlay()
        return tab

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize and (
            obj is self or self._is_active_files_list_source(obj)
        ):
            self.inline_filter_coordinator.position_overlay()
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.KeyPress:
            key_event = cast("QKeyEvent", event)
            if obj is self.filter_edit and key_event.key() in {
                int(Qt.Key.Key_Escape),
                int(Qt.Key.Key_Return),
                int(Qt.Key.Key_Enter),
            }:
                if key_event.key() == int(Qt.Key.Key_Escape):
                    self.inline_filter_coordinator.clear()
                self.inline_filter_coordinator.hide_overlay()
                self._focus_current_view()
                return True
            if (
                key_event.modifiers() == Qt.KeyboardModifier.AltModifier
                and key_event.key() == int(Qt.Key.Key_Down)
            ):
                self.navigation_coordinator.show_history_menu()
                return True
            if self._is_active_files_list_source(
                obj
            ) and self.inline_filter_coordinator.should_start_from_key(key_event):
                self.inline_filter_coordinator.show_overlay(seed_text=key_event.text())
                return True
        return super().eventFilter(obj, event)

    def close_current_tab(self) -> None:
        index = self.tabs.currentIndex()
        if index < 0:
            return
        self.state_coordinator.close_tab_at(index)

    def current_path(self) -> Path:
        tab = self.current_tab()
        return tab.navigation.path if tab else self.default_path

    def current_tab(self) -> ExplorerTab | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, ExplorerTab) else None

    @property
    def navigation_font(self) -> QFont:
        return QFont(self.navigation_font_value)

    @property
    def show_root_dropdown_enabled(self) -> bool:
        return self.show_root_dropdown

    @property
    def show_hidden_enabled(self) -> bool:
        return self._show_hidden

    @property
    def root_paths(self) -> list[Path]:
        return list(self._root_paths)

    def set_root_paths(self, paths: list[Path]) -> None:
        self._root_paths = [Path(path) for path in paths]

    def provided_roots(self, current_path: Path | None) -> list[Path]:
        return list(self._roots_provider(current_path))

    @property
    def address_completions_enabled(self) -> bool:
        return self._address_completions_enabled

    def set_address_completions_enabled(self, enabled: bool) -> None:
        self._address_completions_enabled = bool(enabled)

    def stop_address_completion_timer(self) -> None:
        self.address_completion_timer.stop()

    def start_address_completion_timer(self, interval_ms: int) -> None:
        self.address_completion_timer.start(int(interval_ms))

    def set_address_completion_suggestions(self, suggestions: list[str]) -> None:
        self.address_completion_model.setStringList([str(item) for item in suggestions])

    def show_address_completion_popup(self) -> None:
        self.address_completer.setCompletionPrefix("")
        self.address_completer.complete(self.address_edit.rect())

    def completion_popup(self) -> QAbstractItemView | None:
        return self.address_completer.popup()

    def take_history_menu(self) -> QMenu | None:
        menu = self._history_menu
        self._history_menu = None
        return menu

    def set_history_menu(self, menu: QMenu | None) -> None:
        self._history_menu = menu

    def tab_count(self) -> int:
        return self.tabs.count()

    def set_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, ExplorerTab):
                widget.navigation.set_show_hidden(self._show_hidden)
        if self.address_edit.hasFocus():
            self.navigation_coordinator.schedule_address_completion_update(
                self.address_edit.text()
            )

    def set_show_root_dropdown(self, enabled: bool) -> None:
        self.presentation_coordinator.apply_toolbar_visibility(
            show_refresh_button=self.show_refresh_button,
            show_root_buttons=self.show_root_buttons,
            show_root_dropdown=enabled,
            show_address_bar=self.show_address_bar,
            show_navigation_buttons=self.show_navigation_buttons,
        )

    def assign_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        assign_widget_identity(widget, widget_id=widget_id, widget_alias=alias)

    def retitle_tab(self, tab: ExplorerTab) -> None:
        index = self.tabs.indexOf(tab)
        if index == -1:
            return
        self.tabs.setTabText(index, _tab_label(tab.navigation.path))

    def default_file_list_size_formatter(self, value: int) -> str:
        return f"{int(value):,}"

    def default_properties_size_formatter(self, value: int) -> str:
        return f"{int(value):,}"

    def handle_address_completion_activated(self, path_text: object) -> None:
        self.navigation_coordinator.on_address_completion_activated(str(path_text))

    def _is_active_files_list_source(self, obj: QObject) -> bool:
        tab = self.current_tab()
        if tab is None:
            return False
        return obj is tab.view

    def _focus_current_view(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.view.setFocus()
