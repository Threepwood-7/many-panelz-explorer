"""Panel widget that hosts navigation controls and explorer tabs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import (
    QEvent,
    QObject,
    QStringListModel,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QKeyEvent, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
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
)

if TYPE_CHECKING:
    from collections.abc import Callable


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


def _build_panel_toolbar(panel: PanelWidget, root: QVBoxLayout) -> None:
    """Create the toolbar widgets and add them to the panel layout."""

    toolbar = QHBoxLayout()

    panel.refresh_btn = QPushButton("Refresh")
    panel.refresh_btn.setMinimumWidth(0)
    panel.refresh_btn.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Fixed,
    )
    panel.refresh_btn.clicked.connect(panel.navigation_coordinator.refresh_current_path)
    toolbar.addWidget(panel.refresh_btn)

    panel.root_buttons_host = QWidget()
    panel.root_buttons_host.setMinimumWidth(0)
    panel.root_buttons_host.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Fixed,
    )
    panel.root_buttons_layout = QHBoxLayout(panel.root_buttons_host)
    panel.root_buttons_layout.setContentsMargins(0, 0, 0, 0)
    panel.root_buttons_layout.setSpacing(4)
    toolbar.addWidget(panel.root_buttons_host, 1)

    panel.root_combo = QComboBox()
    panel.root_combo.activated.connect(panel.navigation_coordinator.on_root_selected)
    panel.root_combo.setVisible(panel.show_root_dropdown)
    panel.root_combo.setMinimumWidth(panel.ROOT_COMBO_MIN_WIDTH)
    panel.root_combo.setSizePolicy(
        QSizePolicy.Policy.Preferred,
        QSizePolicy.Policy.Fixed,
    )
    toolbar.addWidget(panel.root_combo)

    panel.address_edit = QLineEdit()
    panel.address_edit.returnPressed.connect(
        panel.navigation_coordinator.on_address_submitted
    )
    panel.address_edit.setMinimumWidth(0)
    panel.address_edit.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Fixed,
    )
    toolbar.addWidget(panel.address_edit, 1)
    panel.address_completion_model = QStringListModel(panel)
    panel.address_completer = QCompleter(panel.address_completion_model, panel)
    panel.address_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    panel.address_completer.setFilterMode(Qt.MatchFlag.MatchContains)
    panel.address_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    panel.address_completer.setMaxVisibleItems(14)
    panel.address_completer.activated.connect(panel.handle_address_completion_activated)
    panel.address_edit.setCompleter(panel.address_completer)
    panel.address_edit.textEdited.connect(
        panel.navigation_coordinator.schedule_address_completion_update
    )

    panel.back_btn = QPushButton("<")
    panel.back_btn.setMinimumWidth(28)
    panel.back_btn.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    panel.back_btn.clicked.connect(panel.navigation_coordinator.go_back)
    toolbar.addWidget(panel.back_btn)

    panel.forward_btn = QPushButton(">")
    panel.forward_btn.setMinimumWidth(28)
    panel.forward_btn.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    panel.forward_btn.clicked.connect(panel.navigation_coordinator.go_forward)
    toolbar.addWidget(panel.forward_btn)

    panel.up_btn = QPushButton("..")
    panel.up_btn.setMinimumWidth(32)
    panel.up_btn.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    panel.up_btn.clicked.connect(panel.navigation_coordinator.go_up)
    toolbar.addWidget(panel.up_btn)

    panel.root_btn = QPushButton("\\")
    panel.root_btn.setMinimumWidth(28)
    panel.root_btn.setSizePolicy(
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    panel.root_btn.clicked.connect(panel.navigation_coordinator.go_root)
    toolbar.addWidget(panel.root_btn)
    panel.navigation_buttons = [
        panel.back_btn,
        panel.forward_btn,
        panel.up_btn,
        panel.root_btn,
    ]

    root.addLayout(toolbar)


def _build_panel_tabs(panel: PanelWidget, root: QVBoxLayout) -> None:
    """Create the tab host and connect tab lifecycle signals."""

    panel.tabs = QTabWidget()
    panel.tabs.setMinimumWidth(0)
    panel.tabs.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Expanding,
    )
    panel.tabs.setTabsClosable(True)
    panel.tabs.currentChanged.connect(panel.state_coordinator.on_current_changed)
    panel.tabs.tabCloseRequested.connect(panel.state_coordinator.close_tab_at)
    panel.tabs.installEventFilter(panel.focus_watcher)
    panel.tabs.installEventFilter(panel)
    tab_bar = panel.tabs.tabBar()
    tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
    tab_bar.setExpanding(True)
    tab_bar.setUsesScrollButtons(False)
    tab_bar.setMinimumWidth(0)
    root.addWidget(panel.tabs)


def _build_panel_filter(panel: PanelWidget) -> None:
    """Create the inline filter control used by the active pane."""

    panel.filter_edit = QLineEdit(panel)
    panel.filter_edit.setPlaceholderText("Filter active pane...")
    panel.filter_edit.setVisible(False)
    panel.filter_edit.setMinimumWidth(0)
    panel.filter_edit.setSizePolicy(
        QSizePolicy.Policy.Ignored,
        QSizePolicy.Policy.Fixed,
    )
    panel.filter_edit.textChanged.connect(
        panel.inline_filter_coordinator.on_text_changed
    )
    panel.filter_edit.installEventFilter(panel)
    panel.installEventFilter(panel)


def _assign_panel_control_identities(panel: PanelWidget) -> None:
    """Assign stable widget identities to the panel controls."""

    panel.assign_identity(
        panel.refresh_btn,
        widget_naming.panel_control_widget_id(panel.panel_id, "refresh"),
        widget_naming.panel_control_alias(panel.panel_id, "refresh"),
    )
    panel.assign_identity(
        panel.address_edit,
        widget_naming.panel_control_widget_id(panel.panel_id, "address"),
        widget_naming.panel_control_alias(panel.panel_id, "address"),
    )
    panel.assign_identity(
        panel.back_btn,
        widget_naming.panel_control_widget_id(panel.panel_id, "back"),
        widget_naming.panel_control_alias(panel.panel_id, "back"),
    )
    panel.assign_identity(
        panel.forward_btn,
        widget_naming.panel_control_widget_id(panel.panel_id, "forward"),
        widget_naming.panel_control_alias(panel.panel_id, "forward"),
    )
    panel.assign_identity(
        panel.up_btn,
        widget_naming.panel_control_widget_id(panel.panel_id, "up"),
        widget_naming.panel_control_alias(panel.panel_id, "up"),
    )
    panel.assign_identity(
        panel.root_btn,
        widget_naming.panel_control_widget_id(panel.panel_id, "root"),
        widget_naming.panel_control_alias(panel.panel_id, "root"),
    )
    panel.assign_identity(
        panel.tabs,
        widget_naming.panel_control_widget_id(panel.panel_id, "tabs"),
        widget_naming.panel_control_alias(panel.panel_id, "tabs"),
    )
    panel.assign_identity(
        panel.tabs.tabBar(),
        widget_naming.panel_control_widget_id(panel.panel_id, "tab_bar"),
        widget_naming.panel_control_alias(panel.panel_id, "tab_bar"),
    )
    panel.assign_identity(
        panel.filter_edit,
        widget_naming.panel_control_widget_id(panel.panel_id, "filter"),
        widget_naming.panel_control_alias(panel.panel_id, "filter"),
    )


def _install_panel_focus_watchers(panel: PanelWidget) -> None:
    """Install the focus watcher on toolbar and tab controls."""

    panel.back_btn.installEventFilter(panel.focus_watcher)
    panel.forward_btn.installEventFilter(panel.focus_watcher)
    panel.up_btn.installEventFilter(panel.focus_watcher)
    panel.root_btn.installEventFilter(panel.focus_watcher)
    panel.refresh_btn.installEventFilter(panel.focus_watcher)
    panel.root_buttons_host.installEventFilter(panel.focus_watcher)
    panel.root_combo.installEventFilter(panel.focus_watcher)
    panel.address_edit.installEventFilter(panel.focus_watcher)
    panel.address_edit.installEventFilter(panel)


def _configure_panel_shortcuts_and_timers(panel: PanelWidget) -> None:
    """Create shortcuts and timers used by the panel chrome."""

    panel.alt_down_shortcut = QShortcut("Alt+Down", panel)
    panel.alt_down_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    panel.alt_down_shortcut.activated.connect(
        panel.navigation_coordinator.show_history_menu
    )
    panel.ctrl_f_shortcut = QShortcut("Ctrl+F", panel)
    panel.ctrl_f_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    panel.ctrl_f_shortcut.activated.connect(
        lambda: panel.inline_filter_coordinator.show_overlay(seed_text="")
    )
    panel.column_sync_timer = QTimer(panel)
    panel.column_sync_timer.setSingleShot(True)
    panel.column_sync_timer.timeout.connect(
        panel.state_coordinator.flush_pending_column_width_sync
    )
    panel.address_completion_timer = QTimer(panel)
    panel.address_completion_timer.setSingleShot(True)
    panel.address_completion_timer.timeout.connect(
        panel.navigation_coordinator.refresh_address_completions
    )


def _finalize_panel_ui(panel: PanelWidget) -> None:
    """Apply presentation defaults after the chrome is constructed."""

    panel.presentation_coordinator.sync_toolbar_for_current_tab()
    panel.presentation_coordinator.apply_toolbar_visibility(
        show_refresh_button=panel.show_refresh_button,
        show_root_buttons=panel.show_root_buttons,
        show_root_dropdown=panel.show_root_dropdown,
        show_address_bar=panel.show_address_bar,
        show_navigation_buttons=panel.show_navigation_buttons,
    )
    panel.presentation_coordinator.apply_font_preferences(
        file_list_font=panel.file_list_font_value,
        navigation_font=panel.navigation_font_value,
    )
    panel.presentation_coordinator.set_role_visual_state(
        is_active=False,
        is_target=False,
    )
    panel.widget_map_coordinator.sync_overlay()


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
        _build_panel_toolbar(self, root)
        _build_panel_tabs(self, root)
        _build_panel_filter(self)
        _assign_panel_control_identities(self)
        _install_panel_focus_watchers(self)
        _configure_panel_shortcuts_and_timers(self)
        _finalize_panel_ui(self)

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
