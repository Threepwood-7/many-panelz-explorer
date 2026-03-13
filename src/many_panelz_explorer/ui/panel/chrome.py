"""Panel chrome construction helpers for PanelWidget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QStringListModel, Qt, QTimer
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ... import widget_naming

if TYPE_CHECKING:
    from ...panel_widget import PanelWidget


def build_panel_toolbar(panel: PanelWidget, root: QVBoxLayout) -> None:
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


def build_panel_tabs(panel: PanelWidget, root: QVBoxLayout) -> None:
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


def build_panel_filter(panel: PanelWidget) -> None:
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


def assign_panel_control_identities(panel: PanelWidget) -> None:
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


def install_panel_focus_watchers(panel: PanelWidget) -> None:
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


def configure_panel_shortcuts_and_timers(panel: PanelWidget) -> None:
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


def finalize_panel_ui(panel: PanelWidget) -> None:
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
