"""Panel widget that hosts navigation controls and explorer tabs."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import (
    QEvent,
    QObject,
    QSignalBlocker,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent
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
from .panel_groups import (
    DEFAULT_TAB_GROUP_ID,
    DEFAULT_TAB_GROUP_TITLE,
    is_default_tab_group,
    new_tab_group_id,
    normalize_tab_group_id,
    normalize_tab_group_title,
)
from .panel_tab_positions import (
    TAB_POSITION_MODE_BOTTOM,
    TAB_POSITION_MODE_DEFAULT,
    TAB_POSITION_MODE_LEFT,
    TAB_POSITION_MODE_LEFT_HORIZONTAL,
    TAB_POSITION_MODE_RIGHT,
    TAB_POSITION_MODE_RIGHT_HORIZONTAL,
    TAB_POSITION_MODE_TOP,
    normalize_panel_tab_position_mode,
    resolve_tab_position_mode,
)
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

    from .ui.window.state_types import TabGroupState


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


@dataclass(slots=True)
class _PanelTabGroupRuntime:
    """Track one panel-local tab group and its live tab widgets."""

    group_id: str
    title: str
    tabs: list[ExplorerTab] = field(default_factory=list)
    current_index: int = 0
    column_widths: list[int] = field(default_factory=list)


class PanelWidget(QWidget):
    """Own one pane of tabs, navigation widgets, and focus state."""

    COLUMN_SYNC_DEBOUNCE_MS = 120
    ADDRESS_COMPLETION_DEBOUNCE_MS = 140
    ROOT_COMBO_MIN_WIDTH = 108
    COLUMN_ALIGN_MODE_CURRENT_PANEL_TABS = "current_panel_tabs"
    COLUMN_ALIGN_MODE_CURRENT_WINDOW_PANELS_TABS = "current_window_panels_tabs"
    COLUMN_ALIGN_MODE_ALL_WINDOWS_PANELS_TABS = "all_windows_panels_tabs"
    COLUMN_ALIGN_MODE_NONE = "none"
    TAB_POSITION_MODE_DEFAULT = TAB_POSITION_MODE_DEFAULT
    TAB_POSITION_MODE_TOP = TAB_POSITION_MODE_TOP
    TAB_POSITION_MODE_BOTTOM = TAB_POSITION_MODE_BOTTOM
    TAB_POSITION_MODE_LEFT = TAB_POSITION_MODE_LEFT
    TAB_POSITION_MODE_LEFT_HORIZONTAL = TAB_POSITION_MODE_LEFT_HORIZONTAL
    TAB_POSITION_MODE_RIGHT = TAB_POSITION_MODE_RIGHT
    TAB_POSITION_MODE_RIGHT_HORIZONTAL = TAB_POSITION_MODE_RIGHT_HORIZONTAL

    activated = Signal()
    current_context_changed = Signal()
    column_widths_sync_requested = Signal(list, object)
    became_empty = Signal()
    tab_closed = Signal(str)
    focus_watcher: _FocusWatcher
    refresh_btn: QPushButton
    root_buttons_host: QWidget
    root_buttons_layout: QHBoxLayout
    root_combo: QComboBox
    group_picker_combo: QComboBox
    new_group_btn: QPushButton
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
        show_tab_close_buttons: bool = True,
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
        self._root_picker_menu: QMenu | None = None
        self._tab_groups: dict[str, _PanelTabGroupRuntime] = {}
        self._group_order: list[str] = []
        self._active_group_id = DEFAULT_TAB_GROUP_ID
        self._mounted_group_id: str | None = None
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
        self.show_tab_close_buttons = bool(show_tab_close_buttons)
        self.tab_position_mode = normalize_panel_tab_position_mode(
            self.TAB_POSITION_MODE_DEFAULT
        )
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
        self._ensure_default_group()
        build_panel_filter(self)
        assign_panel_control_identities(self)
        install_panel_focus_watchers(self)
        configure_panel_shortcuts_and_timers(self)
        finalize_panel_ui(self)

    @property
    def active_group_id(self) -> str:
        """Return the identifier of the active tab group."""

        return self._active_group_id

    @property
    def active_group_title(self) -> str:
        """Return the title of the active tab group."""

        return self._active_group().title

    def group_count(self) -> int:
        """Return the number of tab groups owned by this panel."""

        return len(self._group_order)

    def total_tab_count(self) -> int:
        """Return the total number of tabs across all panel groups."""

        return sum(len(group.tabs) for group in self._tab_groups.values())

    def ordered_group_choices(
        self,
        *,
        include_active: bool = True,
    ) -> list[tuple[str, str]]:
        """Return ordered `(group_id, title)` pairs for this panel."""

        choices: list[tuple[str, str]] = []
        for group_id in self._group_order:
            if not include_active and group_id == self._active_group_id:
                continue
            group = self._tab_groups.get(group_id)
            if group is None:
                continue
            choices.append((group.group_id, group.title))
        return choices

    def can_close_active_group(self) -> bool:
        """Return whether the active tab group can be closed."""

        return self.group_count() > 1

    def create_group(
        self,
        *,
        title: str | None = None,
        seed_paths: list[Path] | None = None,
        activate: bool = True,
    ) -> str:
        """Create a new tab group and optionally activate it."""

        group_id = new_tab_group_id()
        group_title = normalize_tab_group_title(
            title,
            fallback=self._next_group_title(),
        )
        group = _PanelTabGroupRuntime(group_id=group_id, title=group_title)
        if seed_paths is not None:
            group.tabs = [self._build_tab_widget(Path(path)) for path in seed_paths]
            if group.tabs:
                group.current_index = len(group.tabs) - 1
        self._tab_groups[group_id] = group
        self._group_order.append(group_id)
        if activate:
            self.switch_to_group(group_id, focus_view=bool(group.tabs))
        else:
            self._sync_group_picker_controls()
            self.current_context_changed.emit()
            self.widget_map_coordinator.sync_overlay()
        return group_id

    def rename_group(self, group_id: str, title: str) -> bool:
        """Rename one existing tab group."""

        group = self._tab_groups.get(normalize_tab_group_id(group_id))
        if group is None:
            return False
        group.title = normalize_tab_group_title(title, fallback=group.title)
        self._sync_group_picker_controls()
        self.current_context_changed.emit()
        self.widget_map_coordinator.sync_overlay()
        return True

    def close_group(self, group_id: str) -> bool:
        """Close one tab group when more than one group exists."""

        normalized_group_id = normalize_tab_group_id(group_id)
        if normalized_group_id not in self._tab_groups or self.group_count() <= 1:
            return False

        if normalized_group_id == self._active_group_id:
            self._save_active_group_state()
            self._remove_visible_tabs(delete_widgets=True)
        group = self._tab_groups.pop(normalized_group_id)
        self._group_order = [
            current_group_id
            for current_group_id in self._group_order
            if current_group_id != normalized_group_id
        ]
        if normalized_group_id != self._active_group_id:
            for tab in group.tabs:
                tab.deleteLater()

        if not self._group_order:
            self._active_group_id = DEFAULT_TAB_GROUP_ID
            self._ensure_default_group()
        target_group_id = (
            self._active_group_id
            if self._active_group_id in self._tab_groups
            else self._group_order[0]
        )
        self.switch_to_group(target_group_id, focus_view=True)
        return True

    def switch_to_group(self, group_id: str, *, focus_view: bool = False) -> bool:
        """Switch the visible tab strip to the requested group."""

        normalized_group_id = normalize_tab_group_id(group_id)
        if normalized_group_id not in self._tab_groups:
            return False

        current_group_id = self._mounted_group_id
        with QSignalBlocker(self.tabs):
            if current_group_id in self._tab_groups:
                self._save_active_group_state()
            self._remove_visible_tabs(delete_widgets=False)
            target_group = self._tab_groups[normalized_group_id]
            for tab in target_group.tabs:
                self.tabs.addTab(tab, _tab_label(tab.navigation.path))
            if target_group.tabs:
                target_index = max(
                    0,
                    min(target_group.current_index, len(target_group.tabs) - 1),
                )
                self.tabs.setCurrentIndex(target_index)
                target_group.current_index = target_index
            self._active_group_id = normalized_group_id
            self._mounted_group_id = normalized_group_id

        active_group = self._active_group()
        self.column_widths = list(active_group.column_widths)
        if (
            self.column_widths
            and self.column_width_auto_align_mode != self.COLUMN_ALIGN_MODE_NONE
        ):
            self.state_coordinator.apply_column_widths_to_panel_tabs(self.column_widths)
        self._sync_group_picker_controls()
        self.presentation_coordinator.sync_toolbar_for_current_tab()
        self.current_context_changed.emit()
        self.widget_map_coordinator.sync_overlay()
        if focus_view:
            self._focus_current_view()
        return True

    def focus_relative_group(self, step: int) -> bool:
        """Move forward or backward through ordered tab groups."""

        if not self._group_order:
            return False
        if self._active_group_id in self._group_order:
            current_index = self._group_order.index(self._active_group_id)
            next_index = (current_index + step) % len(self._group_order)
        else:
            next_index = 0
        return self.switch_to_group(self._group_order[next_index], focus_view=True)

    def clone_current_tab_to_new_group(self) -> str | None:
        """Create a new group seeded with a copy of the current tab path."""

        tab = self.current_tab()
        if tab is None:
            return None
        return self.create_group(
            seed_paths=[tab.navigation.path],
            activate=True,
        )

    def move_current_tab_to_group(self, target_group_id: str) -> bool:
        """Move the current tab into another group and activate that group."""

        normalized_target_group_id = normalize_tab_group_id(target_group_id)
        if normalized_target_group_id == self._active_group_id:
            return False
        target_group = self._tab_groups.get(normalized_target_group_id)
        if target_group is None:
            return False

        current_index = self.tabs.currentIndex()
        widget = self.tabs.widget(current_index)
        if current_index < 0 or not isinstance(widget, ExplorerTab):
            return False

        with QSignalBlocker(self.tabs):
            self.tabs.removeTab(current_index)
        source_group = self._active_group()
        source_group.tabs = self._visible_tabs()
        source_group.current_index = max(self.tabs.currentIndex(), 0)
        source_group.column_widths = list(self.column_widths)

        target_group.tabs.append(widget)
        target_group.current_index = len(target_group.tabs) - 1

        if not source_group.tabs and self.group_count() > 1:
            self._tab_groups.pop(source_group.group_id, None)
            self._group_order = [
                group_id
                for group_id in self._group_order
                if group_id != source_group.group_id
            ]

        return self.switch_to_group(normalized_target_group_id, focus_view=True)

    def move_current_tab_to_new_group(self) -> str | None:
        """Move the current tab into a newly created tab group."""

        current_tab = self.current_tab()
        if current_tab is None:
            return None
        target_group_id = self.create_group(activate=False)
        moved = self.move_current_tab_to_group(target_group_id)
        if not moved:
            self.close_group(target_group_id)
            return None
        return target_group_id

    def add_tab(self, path: Path) -> ExplorerTab:
        """Add one explorer tab to the active tab group."""

        source_tab = self.current_tab()
        source_widths = (
            list(source_tab.columns.widths) if source_tab is not None else []
        )
        tab = self._build_tab_widget(path)
        self.tabs.addTab(tab, _tab_label(path))
        self.tabs.setCurrentWidget(tab)
        self._mounted_group_id = self._active_group_id
        self.retitle_tab(tab)
        self.state_coordinator.initialize_new_tab_column_widths(
            tab=tab,
            source_widths=source_widths,
        )
        self._save_active_group_state()
        self.presentation_coordinator.sync_toolbar_for_current_tab()
        self.activated.emit()
        self.current_context_changed.emit()
        self.widget_map_coordinator.sync_overlay()
        return tab

    def serialize_tab_groups(self) -> list[TabGroupState]:
        """Serialize all tab groups owned by this panel."""

        self._save_active_group_state()
        return [
            {
                "group_id": group.group_id,
                "title": group.title,
                "current_index": group.current_index,
                "tabs": [tab.serialize_state() for tab in group.tabs],
                "column_widths": list(group.column_widths),
            }
            for group in self._ordered_group_runtimes()
        ]

    def sync_active_group_state(self) -> None:
        """Persist the visible tab widget state back into the active group."""

        self._save_active_group_state()

    def restore_tab_groups(
        self,
        groups: list[TabGroupState],
        *,
        active_group_id: str,
    ) -> None:
        """Restore this panel from serialized tab-group state."""

        self._clear_all_group_tabs()
        self._tab_groups = {}
        self._group_order = []

        for group_state in groups:
            group_id = normalize_tab_group_id(
                group_state.get("group_id"),
                fallback=new_tab_group_id(),
            )
            if group_id in self._tab_groups:
                continue
            title = normalize_tab_group_title(
                group_state.get("title"),
                fallback=self._next_group_title(),
            )
            tabs: list[ExplorerTab] = [
                self._build_tab_widget(Path(tab_state["path"]))
                for tab_state in group_state.get("tabs", [])
            ]
            group = _PanelTabGroupRuntime(
                group_id=group_id,
                title=title,
                tabs=tabs,
                current_index=max(0, int(group_state.get("current_index", 0))),
                column_widths=[
                    width
                    for width in group_state.get("column_widths", [])
                    if width > 0
                ],
            )
            self._tab_groups[group_id] = group
            self._group_order.append(group_id)

        if not self._group_order:
            self._ensure_default_group()

        requested_group_id = normalize_tab_group_id(
            active_group_id,
            fallback=self._group_order[0],
        )
        target_group_id = (
            requested_group_id
            if requested_group_id in self._tab_groups
            else self._group_order[0]
        )
        self.switch_to_group(target_group_id)

    def on_group_picker_index_changed(self, index: int) -> None:
        """Switch groups when the toolbar picker changes selection."""

        if index < 0:
            return
        group_id = str(self.group_picker_combo.itemData(index) or "").strip()
        if not group_id:
            return
        self.switch_to_group(group_id, focus_view=True)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize and (
            obj is self or self._is_active_files_list_source(obj)
        ):
            self.inline_filter_coordinator.position_overlay()
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.MouseButtonDblClick and obj is self.tabs:
            mouse_event = cast("QMouseEvent", event)
            if self._is_tab_strip_blank_double_click(mouse_event):
                self.duplicate_current_tab()
                return True
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

    def duplicate_current_tab(self) -> ExplorerTab | None:
        """Duplicate the active tab into a newly selected tab."""

        tab = self.current_tab()
        if tab is None:
            return None
        return self.add_tab(tab.navigation.path)

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

    def take_root_picker_menu(self) -> QMenu | None:
        menu = self._root_picker_menu
        self._root_picker_menu = None
        return menu

    def set_root_picker_menu(self, menu: QMenu | None) -> None:
        self._root_picker_menu = menu

    def tab_count(self) -> int:
        return self.tabs.count()

    def set_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        for tab in self.iter_all_tabs():
            tab.navigation.set_show_hidden(self._show_hidden)
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

    def resolved_tab_position_mode(self, *, default_tab_position: str) -> str:
        """Return the effective tab-position mode for this panel."""

        return resolve_tab_position_mode(
            self.tab_position_mode,
            default_tab_position=default_tab_position,
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

    def iter_all_tabs(self) -> list[ExplorerTab]:
        """Return all explorer tabs across every tab group."""

        self._save_active_group_state()
        tabs: list[ExplorerTab] = []
        for group in self._ordered_group_runtimes():
            tabs.extend(group.tabs)
        return tabs

    def _ordered_group_runtimes(self) -> list[_PanelTabGroupRuntime]:
        """Return tab groups in their current visual order."""

        groups: list[_PanelTabGroupRuntime] = []
        for group_id in self._group_order:
            group = self._tab_groups.get(group_id)
            if group is not None:
                groups.append(group)
        return groups

    def _active_group(self) -> _PanelTabGroupRuntime:
        """Return the active tab group runtime, creating the default when needed."""

        group = self._tab_groups.get(self._active_group_id)
        if group is not None:
            return group
        self._ensure_default_group()
        active_group = self._tab_groups.get(self._active_group_id)
        if active_group is None:
            raise RuntimeError("Active tab group is missing after initialization.")
        return active_group

    def _ensure_default_group(self) -> None:
        """Ensure the panel has an implicit default tab group."""

        if self._group_order:
            self._sync_group_picker_controls()
            return
        default_group = _PanelTabGroupRuntime(
            group_id=DEFAULT_TAB_GROUP_ID,
            title=DEFAULT_TAB_GROUP_TITLE,
        )
        self._tab_groups = {DEFAULT_TAB_GROUP_ID: default_group}
        self._group_order = [DEFAULT_TAB_GROUP_ID]
        self._active_group_id = DEFAULT_TAB_GROUP_ID
        self._mounted_group_id = None
        self._sync_group_picker_controls()

    def _next_group_title(self) -> str:
        """Return the next default title for a newly created tab group."""

        existing_titles = {group.title for group in self._tab_groups.values()}
        candidate = 1
        while True:
            title = f"Group {candidate}"
            if title not in existing_titles:
                return title
            candidate += 1

    def _sync_group_picker_controls(self) -> None:
        """Refresh the toolbar group picker and its visibility."""

        with QSignalBlocker(self.group_picker_combo):
            self.group_picker_combo.clear()
            current_index = -1
            for index, group in enumerate(self._ordered_group_runtimes()):
                self.group_picker_combo.addItem(group.title, group.group_id)
                if group.group_id == self._active_group_id:
                    current_index = index
            if current_index >= 0:
                self.group_picker_combo.setCurrentIndex(current_index)
        self.group_picker_combo.setVisible(self._should_show_group_picker())

    def _should_show_group_picker(self) -> bool:
        """Return whether the group picker should be shown for this panel."""

        if self.group_count() != 1:
            return True
        group = self._active_group()
        return not is_default_tab_group(group_id=group.group_id, title=group.title)

    def _visible_tabs(self) -> list[ExplorerTab]:
        """Return the explorer tabs currently mounted in the visible tab widget."""

        tabs: list[ExplorerTab] = []
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if isinstance(widget, ExplorerTab):
                tabs.append(widget)
        return tabs

    def _save_active_group_state(self) -> None:
        """Copy the visible tab widget state back into the active group runtime."""

        mounted_group_id = self._mounted_group_id
        if mounted_group_id is None:
            return
        group = self._tab_groups.get(mounted_group_id)
        if group is None:
            return
        group.tabs = self._visible_tabs()
        group.current_index = max(self.tabs.currentIndex(), 0) if group.tabs else 0
        group.column_widths = list(self.column_widths)

    def _remove_visible_tabs(self, *, delete_widgets: bool) -> list[ExplorerTab]:
        """Remove all visible tabs, optionally deleting their widgets."""

        tabs: list[ExplorerTab] = []
        while self.tabs.count() > 0:
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if isinstance(widget, ExplorerTab):
                tabs.append(widget)
        if delete_widgets:
            for tab in tabs:
                tab.deleteLater()
        self._mounted_group_id = None
        return tabs

    def _build_tab_widget(self, path: Path) -> ExplorerTab:
        """Create and connect one explorer tab widget for the given path."""

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
        return tab

    def _clear_all_group_tabs(self) -> None:
        """Delete every live tab widget tracked by this panel."""

        self._save_active_group_state()
        self._remove_visible_tabs(delete_widgets=False)
        seen_tab_ids: set[int] = set()
        for group in self._tab_groups.values():
            for tab in group.tabs:
                tab_key = id(tab)
                if tab_key in seen_tab_ids:
                    continue
                seen_tab_ids.add(tab_key)
                tab.deleteLater()
        self.column_widths = []

    def _is_active_files_list_source(self, obj: QObject) -> bool:
        tab = self.current_tab()
        if tab is None:
            return False
        return obj is tab.view

    def _focus_current_view(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.view.setFocus()

    def _is_tab_strip_blank_double_click(self, event: QMouseEvent) -> bool:
        """Return whether a double click landed in blank tab-strip space."""

        if event.button() != Qt.MouseButton.LeftButton:
            return False
        tab_bar_rect = self.tabs.tabBar().geometry()
        position = event.position().toPoint()
        if position.y() < tab_bar_rect.top() or position.y() > tab_bar_rect.bottom():
            return False
        return position.x() > tab_bar_rect.right()
