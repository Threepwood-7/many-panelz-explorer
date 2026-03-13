import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QDir, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from many_panelz_explorer._operations.queue_manager import OperationQueueManager
from many_panelz_explorer._operations.types import OperationExecutionPreferences
from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer.operation_queue_widgets import OperationQueueTableModel
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def __init__(self) -> None:
        self.operation_queue_manager = OperationQueueManager(
            preferences=OperationExecutionPreferences()
        )
        self.operation_queue_model = OperationQueueTableModel(
            self.operation_queue_manager
        )

    def close_window(self, _window) -> None:
        return

    def show_queue_floating_window(self):
        return None

    def broadcast_column_widths(self, *_a, **_k) -> None:
        return


def _test_roots_provider(tmp_path: Path):
    root = tmp_path / "roots"
    root.mkdir(parents=True, exist_ok=True)
    return lambda _current: [root]


def test_shortcuts_and_menu_parity(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="smoke",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    assert panel.tab_count() == 1

    window.new_tab_action.trigger()
    assert window.panels_coordinator.active_panel().tab_count() == 2

    assert window.new_tab_action.shortcut().toString() == "Ctrl+T"
    window.new_tab_action.trigger()
    assert window.panels_coordinator.active_panel().tab_count() == 3

    window.new_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 2

    assert window.new_horizontal_panel_action.shortcut().toString() == "Ctrl+H"
    window.new_horizontal_panel_action.trigger()
    assert len(window.panel_widgets) == 4

    assert window.copy_to_target_action.shortcut().toString() == "F5"
    assert window.move_to_target_action.shortcut().toString() == "F6"
    assert window.delete_selection_action.shortcut().toString() == "F8"

    assert window.close_window_action.shortcut().toString() == "Alt+W"
    exit_shortcuts = {seq.toString() for seq in window.exit_action.shortcuts()}
    assert {"Ctrl+Q", "Alt+X"} <= exit_shortcuts

    menu_titles = [
        action.text().replace("&", "") for action in window.menuBar().actions()
    ]
    assert menu_titles[:4] == ["File", "View", "Context", "Help"]

    file_menu = window.menuBar().actions()[0].menu()
    assert file_menu is not None
    file_labels = [
        action.text().replace("&", "")
        for action in file_menu.actions()
        if action.text()
    ]
    assert "Close Window" in file_labels
    assert "Exit" in file_labels
    assert "Save View" in file_labels
    assert "Restore View" in file_labels
    assert "Replace View" in file_labels

    restore_action = next(
        action
        for action in file_menu.actions()
        if action.text().replace("&", "") == "Restore View"
    )
    assert restore_action.menu() is not None

    view_menu = window.menuBar().actions()[1].menu()
    assert view_menu is not None
    refresh_action = next(
        (action for action in view_menu.actions() if action.text() == "&Refresh"), None
    )
    assert refresh_action is not None
    assert refresh_action.shortcut().toString() == "Ctrl+R"
    assert any(
        action.text().replace("&", "") == "Show Widget Map"
        for action in view_menu.actions()
    )
    settings_action = next(
        (action for action in view_menu.actions() if action.text() == "&Settings..."),
        None,
    )
    assert settings_action is not None
    assert settings_action.shortcut().toString() == "Ctrl+,"

    help_menu = window.menuBar().actions()[3].menu()
    assert help_menu is not None
    help_action = next(
        (action for action in help_menu.actions() if action.text() == "&Help"), None
    )
    assert help_action is not None
    assert help_action.shortcut().toString() == "F1"


def test_hidden_action_updates_model_filter(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="smoke-hidden",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    tab = window.panels_coordinator.active_panel().current_tab()
    assert tab is not None

    window.show_hidden_action.setChecked(False)
    assert not (tab.model.filter() & QDir.Hidden)

    window.show_hidden_action.setChecked(True)
    assert tab.model.filter() & QDir.Hidden


def test_menu_activation_from_view_filter_and_address(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="smoke-menu-activation",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    window.raise_()

    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    tab = panel.current_tab()
    assert tab is not None

    menu_bar = window.menuBar()
    file_action = menu_bar.actions()[0]
    file_menu = menu_bar.actions()[0].menu()
    assert file_menu is not None

    tab.view.setFocus()
    window.menu_focus_shortcut.activated.emit()
    qtbot.waitUntil(
        lambda: file_menu.isVisible() or menu_bar.activeAction() is file_action
    )
    file_menu.close()

    panel.inline_filter_coordinator.show_overlay(seed_text="")
    panel.filter_edit.setFocus()
    window.menu_focus_shortcut.activated.emit()
    qtbot.waitUntil(
        lambda: file_menu.isVisible() or menu_bar.activeAction() is file_action
    )
    file_menu.close()

    panel.address_edit.setFocus()
    window.menu_focus_shortcut.activated.emit()
    qtbot.waitUntil(
        lambda: file_menu.isVisible() or menu_bar.activeAction() is file_action
    )
    file_menu.close()


def test_menu_mouse_click_opens_each_main_menu(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="smoke-menu-click",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    window.raise_()

    menu_bar = window.menuBar()
    for action in [item for item in menu_bar.actions()[:4] if item.isVisible()]:
        menu = action.menu()
        assert menu is not None
        target = menu_bar.actionGeometry(action).center()
        QTest.mouseClick(menu_bar, Qt.LeftButton, Qt.NoModifier, target)
        qtbot.waitUntil(
            lambda m=menu, a=action: m.isVisible() or menu_bar.activeAction() is a
        )
        menu.close()


def test_window_does_not_create_menu_overlap_widgets(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="smoke-menu-no-overlap",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    menu_bar = window.menuBar()
    protected = {window.centralWidget(), window.statusBar(), menu_bar}
    overlap_children = [
        child
        for child in window.findChildren(
            QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
        )
        if child not in protected
        and child.isVisible()
        and type(child) is QWidget
        and child.geometry().intersects(menu_bar.geometry())
    ]
    assert overlap_children == []

    file_action = menu_bar.actions()[0]
    hit = QApplication.widgetAt(
        menu_bar.mapToGlobal(menu_bar.actionGeometry(file_action).center())
    )
    assert hit is menu_bar
