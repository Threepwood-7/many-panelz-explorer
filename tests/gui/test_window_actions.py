import os
from collections.abc import Callable
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox

from many_panelz_explorer.settings import SettingsManager
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def __init__(self) -> None:
        self.closed_windows: list[ExplorerWindow] = []

    def close_window(self, _window) -> None:
        self.closed_windows.append(_window)


def _test_roots_provider(tmp_path: Path) -> Callable[[Path | None], list[Path]]:
    root = tmp_path / "roots"
    root.mkdir(parents=True, exist_ok=True)
    return lambda _current: [root]


class _ControllerCloneStub(_ControllerStub):
    def __init__(
        self,
        settings: SettingsManager,
        roots_provider: Callable[[Path | None], list[Path]] | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.roots_provider = roots_provider
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
            roots_provider=self.roots_provider,
        )
        self.created_windows.append(win)
        if show:
            win.show()
        return win


def test_split_tab_close_actions(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="test-window",
        roots_provider=roots_provider,
    )
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
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="hidden-window",
        roots_provider=roots_provider,
    )
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


def test_show_widget_map_toggle_updates_existing_and_new_panels(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="widget-map-toggle-window",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    assert all(not panel.widget_map_enabled() for panel in window.panel_widgets.values())

    window._show_widget_map_action.setChecked(True)
    assert all(panel.widget_map_enabled() for panel in window.panel_widgets.values())

    window._new_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 2
    assert all(panel.widget_map_enabled() for panel in window.panel_widgets.values())

    window._show_widget_map_action.setChecked(False)
    assert all(not panel.widget_map_enabled() for panel in window.panel_widgets.values())


def test_clone_current_panel_vertical_and_horizontal(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="clone-panel-window",
        roots_provider=roots_provider,
    )
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
    assert len(window.panel_widgets) == 4
    cloned_panel_horizontal = window.active_panel()
    assert cloned_panel_horizontal is not None
    assert cloned_panel_horizontal.tab_count() == source_tab_count
    assert cloned_panel_horizontal.tabs.currentIndex() == source_current_index


def test_set_on_top_direct_call_does_not_emit_toggled(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="on-top-signal",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    toggled_events: list[bool] = []
    window._on_top_action.toggled.connect(toggled_events.append)

    window.set_on_top(True)

    assert toggled_events == []
    assert window._on_top_action.isChecked() is True


def test_clone_current_window_action(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerCloneStub(
        settings=settings,
        roots_provider=roots_provider,
    )
    source = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="source-window",
        roots_provider=roots_provider,
    )
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


def test_close_window_action_closes_and_notifies_controller(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerStub()
    window = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="close-window",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()

    window._close_window_action.trigger()
    qtbot.waitUntil(lambda: not window.isVisible())

    assert controller.closed_windows
    assert controller.closed_windows[-1] is window


def test_root_dropdown_ini_setting_controls_panel_dropdown(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    settings.show_root_dropdown = True
    settings.sync()

    window_on = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="dropdown-on",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window_on)
    window_on.show()
    assert window_on.active_panel() is not None
    assert window_on.active_panel().root_combo.isVisible() is True

    settings_off = SettingsManager()
    settings_off.show_root_dropdown = False
    settings_off.sync()

    window_off = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings_off,
        window_id="dropdown-off",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window_off)
    window_off.show()
    assert window_off.active_panel() is not None
    assert window_off.active_panel().root_combo.isVisible() is False


def test_save_restore_replace_view_actions(qtbot, tmp_path: Path, monkeypatch) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerCloneStub(
        settings=settings,
        roots_provider=roots_provider,
    )
    source = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="view-source",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(source)
    source.show()
    source.resize(777, 555)
    source.move(120, 130)

    source.new_tab_in_active_panel()
    source.split_active_panel(Qt.Orientation.Horizontal)
    source.set_on_top(True)
    assert len(source.panel_widgets) == 2

    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("My View", True))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_a, **_k: QMessageBox.StandardButton.Yes,
    )
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
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("restore should use submenu, not dialog")
        ),
    )
    source._populate_restore_view_menu()
    restore_actions = [
        a for a in source._restore_view_menu.actions() if a.text() == "My View"
    ]
    assert restore_actions
    restore_actions[0].trigger()
    assert len(controller.created_windows) == 1
    restored = controller.created_windows[0]
    qtbot.addWidget(restored)
    assert len(restored.panel_widgets) == 2
    assert restored._on_top_action.isChecked() is True


def test_split_behaviour_uses_full_width_rows(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="rows-contract",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    assert [len(row) for row in window._layout_rows] == [1]

    window._new_vertical_panel_action.trigger()
    assert [len(row) for row in window._layout_rows] == [2]

    window._new_horizontal_panel_action.trigger()
    assert [len(row) for row in window._layout_rows] == [2, 2]

    window._new_vertical_panel_action.trigger()
    assert [len(row) for row in window._layout_rows] == [2, 3]


def test_copy_to_target_uses_last_active_non_source_panel(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="target-resolution",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    window._new_vertical_panel_action.trigger()
    window._new_horizontal_panel_action.trigger()
    assert len(window.panel_widgets) == 4

    ordered_ids = [pid for row in window._layout_rows for pid in row]
    source_id = ordered_ids[0]
    preferred_target_id = ordered_ids[-1]
    source_panel = window.panel_widgets[source_id]
    target_panel = window.panel_widgets[preferred_target_id]

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    src_file = src_dir / "a.txt"
    src_file.write_text("a", encoding="utf-8")
    dst_dir = tmp_path / "dst"
    dst_dir.mkdir()

    source_panel.current_tab().set_path(src_dir)
    target_panel.current_tab().set_path(dst_dir)

    monkeypatch.setattr(
        source_panel.current_tab(), "selected_paths", lambda: [src_file]
    )
    captured: list[Path] = []
    monkeypatch.setattr(
        window,
        "_copy_or_move_one",
        lambda **kwargs: captured.append(Path(kwargs["destination_dir"])) or "done",
    )

    window._set_active_panel(preferred_target_id)
    window._set_active_panel(source_id)
    window._copy_to_target_action.trigger()

    assert captured == [dst_dir]
    assert source_panel._pane_role == "active"
    assert target_panel._pane_role == "target"


def test_copy_or_move_conflict_choices(qtbot, tmp_path: Path, monkeypatch) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="conflict-policy",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    source = tmp_path / "source.txt"
    source.write_text("src", encoding="utf-8")
    destination_dir = tmp_path / "dest"
    destination_dir.mkdir()
    existing = destination_dir / "source.txt"
    existing.write_text("dst", encoding="utf-8")

    monkeypatch.setattr(window, "_prompt_conflict_resolution", lambda *_a, **_k: "skip")
    assert window._copy_or_move_one(
        source=source, destination_dir=destination_dir, move=False
    ) == "skip"
    assert existing.read_text(encoding="utf-8") == "dst"

    monkeypatch.setattr(window, "_prompt_conflict_resolution", lambda *_a, **_k: "rename")
    assert window._copy_or_move_one(
        source=source, destination_dir=destination_dir, move=False
    ) == "done"
    assert (destination_dir / "source (1).txt").exists()

    monkeypatch.setattr(
        window, "_prompt_conflict_resolution", lambda *_a, **_k: "overwrite"
    )
    source.write_text("new", encoding="utf-8")
    assert window._copy_or_move_one(
        source=source, destination_dir=destination_dir, move=False
    ) == "done"
    assert existing.read_text(encoding="utf-8") == "new"

    monkeypatch.setattr(window, "_prompt_conflict_resolution", lambda *_a, **_k: "cancel")
    assert window._copy_or_move_one(
        source=source, destination_dir=destination_dir, move=False
    ) == "cancel"


def test_column_width_sync_stays_within_active_pane_tabs(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="column-sync-scope",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    window._new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window._layout_rows for pid in row]
    assert len(ordered_ids) >= 2
    first_panel = window.panel_widgets[ordered_ids[0]]
    second_panel = window.panel_widgets[ordered_ids[1]]

    first_primary = first_panel.current_tab()
    first_secondary = first_panel.add_tab(first_panel.current_path())
    second_tab = second_panel.current_tab()
    assert first_primary is not None
    assert first_secondary is not None
    assert second_tab is not None

    second_original = second_tab.view.columnWidth(0)
    first_primary.view.setColumnWidth(0, 360)
    qtbot.waitUntil(lambda: first_secondary.view.columnWidth(0) == 360)
    assert second_tab.view.columnWidth(0) == second_original
