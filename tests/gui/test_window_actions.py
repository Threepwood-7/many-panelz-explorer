import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog

from many_panelz_explorer.settings import SettingsManager
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def __init__(self) -> None:
        self.closed_windows: list[ExplorerWindow] = []

    def close_window(self, _window) -> None:
        self.closed_windows.append(_window)


class _ControllerCloneStub(_ControllerStub):
    def __init__(self, settings: SettingsManager) -> None:
        super().__init__()
        self.settings = settings
        self.created_windows: list[ExplorerWindow] = []

    def new_window(
        self,
        from_window: ExplorerWindow | None = None,
        *,
        window_id: str | None = None,
        show: bool = True,
    ) -> ExplorerWindow:
        _ = from_window
        win = ExplorerWindow(
            controller=self,
            settings=self.settings,
            window_id=window_id or f"clone-{len(self.created_windows) + 1}",
        )
        self.created_windows.append(win)
        if show:
            win.show()
        return win


def test_split_tab_close_actions(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    window = ExplorerWindow(controller=_ControllerStub(), settings=settings, window_id="test-window")
    qtbot.addWidget(window)
    window.show()

    assert len(window.panel_widgets) == 1
    panel = window.active_panel()
    assert panel is not None
    assert panel.tab_count() == 1

    window.new_tab_in_active_panel()
    assert window.active_panel().tab_count() == 2

    window.close_active_tab()
    assert window.active_panel().tab_count() == 1

    window.split_active_panel(Qt.Orientation.Horizontal)
    assert len(window.panel_widgets) == 2

    window.close_active_panel()
    assert len(window.panel_widgets) == 1


def test_show_hidden_toggle_updates_tabs(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    window = ExplorerWindow(controller=_ControllerStub(), settings=settings, window_id="hidden-window")
    qtbot.addWidget(window)
    window.show()

    panel = window.active_panel()
    tab = panel.current_tab()
    assert tab is not None

    window._show_hidden_action.setChecked(False)
    assert tab.model.filter() & tab.model.filter().NoDotAndDotDot
    assert not (tab.model.filter() & tab.model.filter().Hidden)

    window._show_hidden_action.setChecked(True)
    assert tab.model.filter() & tab.model.filter().Hidden


def test_clone_current_panel_vertical_and_horizontal(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    window = ExplorerWindow(controller=_ControllerStub(), settings=settings, window_id="clone-panel-window")
    qtbot.addWidget(window)
    window.show()

    window.new_tab_in_active_panel()
    source_panel = window.active_panel()
    assert source_panel is not None
    source_panel.tabs.setCurrentIndex(0)
    source_tab_count = source_panel.tab_count()
    source_current_index = source_panel.tabs.currentIndex()

    window._clone_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 2
    cloned_panel_vertical = window.active_panel()
    assert cloned_panel_vertical is not None
    assert cloned_panel_vertical.tab_count() == source_tab_count
    assert cloned_panel_vertical.tabs.currentIndex() == source_current_index

    window._clone_horizontal_panel_action.trigger()
    assert len(window.panel_widgets) == 3
    cloned_panel_horizontal = window.active_panel()
    assert cloned_panel_horizontal is not None
    assert cloned_panel_horizontal.tab_count() == source_tab_count
    assert cloned_panel_horizontal.tabs.currentIndex() == source_current_index


def test_clone_current_window_action(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    controller = _ControllerCloneStub(settings=settings)
    source = ExplorerWindow(controller=controller, settings=settings, window_id="source-window")
    qtbot.addWidget(source)
    source.show()

    source.new_tab_in_active_panel()
    source._clone_vertical_panel_action.trigger()
    source.set_on_top(True)

    source._clone_window_action.trigger()
    assert len(controller.created_windows) == 1

    cloned = controller.created_windows[0]
    qtbot.addWidget(cloned)

    assert cloned.panel_tree.to_dict() == source.panel_tree.to_dict()
    assert cloned._on_top_action.isChecked() is True

    source_counts = sorted(panel.tab_count() for panel in source.panel_widgets.values())
    cloned_counts = sorted(panel.tab_count() for panel in cloned.panel_widgets.values())
    assert cloned_counts == source_counts


def test_close_window_action_closes_and_notifies_controller(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    controller = _ControllerStub()
    window = ExplorerWindow(controller=controller, settings=settings, window_id="close-window")
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()

    window._close_window_action.trigger()
    qtbot.waitUntil(lambda: not window.isVisible())

    assert controller.closed_windows
    assert controller.closed_windows[-1] is window


def test_root_dropdown_ini_setting_controls_panel_dropdown(qtbot, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.ini"
    settings = SettingsManager(settings_path=settings_path)
    settings.show_root_dropdown = True
    settings.sync()

    window_on = ExplorerWindow(controller=_ControllerStub(), settings=settings, window_id="dropdown-on")
    qtbot.addWidget(window_on)
    window_on.show()
    assert window_on.active_panel() is not None
    assert window_on.active_panel().root_combo.isVisible() is True

    settings_off = SettingsManager(settings_path=settings_path)
    settings_off.show_root_dropdown = False
    settings_off.sync()

    window_off = ExplorerWindow(
        controller=_ControllerStub(), settings=settings_off, window_id="dropdown-off"
    )
    qtbot.addWidget(window_off)
    window_off.show()
    assert window_off.active_panel() is not None
    assert window_off.active_panel().root_combo.isVisible() is False


def test_save_restore_replace_view_actions(qtbot, tmp_path: Path, monkeypatch) -> None:
    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    controller = _ControllerCloneStub(settings=settings)
    source = ExplorerWindow(controller=controller, settings=settings, window_id="view-source")
    qtbot.addWidget(source)
    source.show()
    source.resize(777, 555)
    source.move(120, 130)

    source.new_tab_in_active_panel()
    source.split_active_panel(Qt.Orientation.Horizontal)
    source.set_on_top(True)
    assert len(source.panel_widgets) == 2

    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("My View", True))
    source._save_view_action.trigger()

    saved = settings.get_saved_view("My View")
    assert saved is not None
    assert "geometry_b64" in saved
    assert saved["on_top"] is True

    source.close_active_panel()
    assert len(source.panel_widgets) == 1

    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("My View", True))
    source._replace_view_action.trigger()
    assert len(source.panel_widgets) == 2
    assert source._on_top_action.isChecked() is True

    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("restore should use submenu, not dialog")),
    )
    source._populate_restore_view_menu()
    restore_actions = [a for a in source._restore_view_menu.actions() if a.text() == "My View"]
    assert restore_actions
    restore_actions[0].trigger()
    assert len(controller.created_windows) == 1
    restored = controller.created_windows[0]
    qtbot.addWidget(restored)
    assert len(restored.panel_widgets) == 2
    assert restored._on_top_action.isChecked() is True
