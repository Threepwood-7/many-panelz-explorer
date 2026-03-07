import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QDir

from many_panelz_explorer.settings import SettingsManager
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def close_window(self, _window) -> None:
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

    panel = window.active_panel()
    assert panel is not None
    assert panel.tab_count() == 1

    window._new_tab_action.trigger()
    assert window.active_panel().tab_count() == 2

    assert window._new_tab_action.shortcut().toString() == "Ctrl+T"
    window._new_tab_action.trigger()
    assert window.active_panel().tab_count() == 3

    window._new_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 2

    assert window._new_horizontal_panel_action.shortcut().toString() == "Ctrl+H"
    window._new_horizontal_panel_action.trigger()
    assert len(window.panel_widgets) == 3

    assert window._close_window_action.shortcut().toString() == "Alt+W"
    exit_shortcuts = {seq.toString() for seq in window._exit_action.shortcuts()}
    assert {"Ctrl+Q", "Alt+X"} <= exit_shortcuts

    menu_titles = [
        action.text().replace("&", "") for action in window.menuBar().actions()
    ]
    assert menu_titles[:3] == ["File", "View", "Help"]

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
    assert refresh_action.shortcut().toString() == "F5"

    help_menu = window.menuBar().actions()[2].menu()
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

    tab = window.active_panel().current_tab()
    assert tab is not None

    window._show_hidden_action.setChecked(False)
    assert not (tab.model.filter() & QDir.Hidden)

    window._show_hidden_action.setChecked(True)
    assert tab.model.filter() & QDir.Hidden
