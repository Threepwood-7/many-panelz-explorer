import os
from collections.abc import Callable
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from many_panelz_explorer import mounts
from many_panelz_explorer._operations.queue_manager import OperationQueueManager
from many_panelz_explorer._operations.types import OperationExecutionPreferences
from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer._settings.models import UiPreferences
from many_panelz_explorer.explorer_tab import ExplorerTab
from many_panelz_explorer.operation_queue_widgets import OperationQueueTableModel
from many_panelz_explorer.panel_widget import PanelWidget
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def __init__(self) -> None:
        self.closed_windows: list[ExplorerWindow] = []
        self.broadcast_calls: list[list[object]] = []
        self.minimize_calls = 0
        self.operation_queue_manager = OperationQueueManager(
            preferences=OperationExecutionPreferences()
        )
        self.operation_queue_model = OperationQueueTableModel(
            self.operation_queue_manager
        )

    def close_window(self, _window) -> None:
        self.closed_windows.append(_window)

    def broadcast_column_widths(
        self,
        widths: list[object],
        *,
        source_window: ExplorerWindow | None = None,
        source_panel_id: int | None = None,
        source_tab: ExplorerTab | None = None,
    ) -> None:
        _ = source_window, source_panel_id, source_tab
        self.broadcast_calls.append(list(widths))

    def show_queue_floating_window(self):
        return None

    def minimize_all_windows(self) -> None:
        self.minimize_calls += 1


class _ControllerBroadcastStub(_ControllerStub):
    def __init__(self) -> None:
        super().__init__()
        self.windows: list[ExplorerWindow] = []

    def broadcast_column_widths(
        self,
        widths: list[object],
        *,
        source_window: ExplorerWindow | None = None,
        source_panel_id: int | None = None,
        source_tab: ExplorerTab | None = None,
    ) -> None:
        for window in list(self.windows):
            window.panels_coordinator.column_sync_coordinator.apply_column_widths_all_panels(
                widths,
                source_panel_id=source_panel_id if window is source_window else None,
                source_tab=source_tab if window is source_window else None,
            )


def _test_roots_provider(tmp_path: Path) -> Callable[[Path | None], list[Path]]:
    root = tmp_path / "roots"
    root.mkdir(parents=True, exist_ok=True)
    return lambda _current: [root]


def _visible_storage_labels(window: ExplorerWindow) -> list[object]:
    labels = list(getattr(window, "storage_overview_labels", []))
    return [label for label in labels if label.isVisible()]


def _ordered_panels(window: ExplorerWindow) -> list[PanelWidget]:
    ordered_ids = [panel_id for row in window.layout_rows for panel_id in row]
    return [window.panel_widgets[panel_id] for panel_id in ordered_ids]


def _column_test_root(tmp_path: Path) -> Path:
    root = tmp_path / "column-test-root"
    root.mkdir(exist_ok=True)
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    return root


def _prepare_tabs_for_column_assertions(
    qtbot,
    tabs: list[ExplorerTab],
    *,
    path: Path,
) -> None:
    for tab in tabs:
        tab.navigation.set_path(path)
    qtbot.waitUntil(
        lambda: all(
            tab.navigation.path == path and tab.model.rowCount() >= 1 for tab in tabs
        )
    )


def _select_paths(tab: ExplorerTab, paths: list[Path]) -> None:
    selection_model = tab.view.selectionModel()
    first_flags = (
        QItemSelectionModel.SelectionFlag.ClearAndSelect
        | QItemSelectionModel.SelectionFlag.Rows
    )
    add_flags = (
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows
    )
    for index, path in enumerate(paths):
        model_index = tab.model.index(str(path))
        assert model_index.isValid()
        selection_model.setCurrentIndex(
            model_index,
            first_flags if index == 0 else add_flags,
        )


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
        win = ExplorerWindow(
            controller=self,
            settings=self.settings,
            window_id=window_id or f"clone-{len(self.created_windows) + 1}",
            roots_provider=self.roots_provider,
        )
        if from_window is not None:
            win.default_maximize_on_first_show = False
            geo = from_window.geometry()
            win.resize(geo.width(), geo.height())
            win.move(geo.x() + 30, geo.y() + 30)
        self.created_windows.append(win)
        if show:
            win.show()
        return win


def test_external_file_manager_actions_visibility_tracks_tool_resolution(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.total_commander_executable = str(tmp_path / "missing-totalcmd.exe")
    settings.double_commander_executable = str(tmp_path / "missing-doublecmd.exe")
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="external-manager-visibility",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    window.ui_composer._sync_external_file_manager_actions()
    assert window.explorer_here_source_action.isVisible() is True
    assert window.explorer_here_source_target_action.isVisible() is True
    assert window.total_commander_here_source_action.isVisible() is False
    assert window.double_commander_here_source_action.isVisible() is False

    total_commander_exe = tmp_path / "totalcmd64.exe"
    double_commander_exe = tmp_path / "doublecmd.exe"
    total_commander_exe.write_text("", encoding="utf-8")
    double_commander_exe.write_text("", encoding="utf-8")
    settings.total_commander_executable = str(total_commander_exe)
    settings.double_commander_executable = str(double_commander_exe)
    settings.sync()

    window.ui_composer._sync_external_file_manager_actions()
    assert window.total_commander_here_source_action.isVisible() is True
    assert window.total_commander_here_source_target_action.isVisible() is True
    assert window.double_commander_here_source_action.isVisible() is True
    assert window.double_commander_here_source_target_action.isVisible() is True

    ordered_ids = [panel_id for row in window.layout_rows for panel_id in row]
    window.panels_coordinator.close_panel_by_id(ordered_ids[1])
    window.ui_composer._sync_external_file_manager_actions()
    assert window.explorer_here_source_target_action.isEnabled() is False
    assert window.total_commander_here_source_target_action.isEnabled() is False
    assert window.double_commander_here_source_target_action.isEnabled() is False


def test_external_file_manager_actions_launch_expected_commands(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = SettingsManager()
    system_root = tmp_path / "Windows"
    explorer_exe = system_root / "explorer.exe"
    explorer_exe.parent.mkdir(parents=True, exist_ok=True)
    explorer_exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("SYSTEMROOT", str(system_root))
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="external-manager-launch",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    ordered_ids = [panel_id for row in window.layout_rows for panel_id in row]
    source_panel = window.panel_widgets[ordered_ids[0]]
    target_panel = window.panel_widgets[ordered_ids[1]]
    window.panels_coordinator.set_active_panel(source_panel.panel_id)

    source_root = tmp_path / "source root"
    target_root = tmp_path / "target root"
    source_root.mkdir()
    target_root.mkdir()
    source_file = source_root / "alpha one.txt"
    source_second_file = source_root / "beta two.txt"
    target_file = target_root / "gamma three.txt"
    source_file.write_text("alpha", encoding="utf-8")
    source_second_file.write_text("beta", encoding="utf-8")
    target_file.write_text("gamma", encoding="utf-8")

    source_tab = source_panel.current_tab()
    target_tab = target_panel.current_tab()
    assert source_tab is not None
    assert target_tab is not None
    source_tab.navigation.set_path(source_root)
    target_tab.navigation.set_path(target_root)
    qtbot.waitUntil(lambda: source_tab.model.index(str(source_file)).isValid())
    qtbot.waitUntil(lambda: target_tab.model.index(str(target_file)).isValid())
    _select_paths(source_tab, [source_file])
    _select_paths(target_tab, [target_file])

    total_commander_exe = tmp_path / "totalcmd64.exe"
    double_commander_exe = tmp_path / "doublecmd.exe"
    total_commander_exe.write_text("", encoding="utf-8")
    double_commander_exe.write_text("", encoding="utf-8")
    settings.total_commander_executable = str(total_commander_exe)
    settings.double_commander_executable = str(double_commander_exe)
    settings.sync()

    recorded: list[list[str]] = []

    def _record_popen(args: list[str], **_kwargs: object) -> None:
        recorded.append(list(args))
        return None

    monkeypatch.setattr(
        "many_panelz_explorer.external_file_managers.subprocess.Popen",
        _record_popen,
    )

    window.explorer_here_source_action.trigger()
    assert recorded[-1] == [str(explorer_exe), f"/select,{source_file}"]

    window.explorer_here_source_target_action.trigger()
    assert recorded[-2] == [str(explorer_exe), f"/select,{source_file}"]
    assert recorded[-1] == [str(explorer_exe), f"/select,{target_file}"]

    window.total_commander_here_source_target_action.trigger()
    assert recorded[-1] == [
        str(total_commander_exe),
        "/O",
        "/A",
        f"/L={source_file}",
        f"/R={target_file}",
    ]

    window.double_commander_here_source_action.trigger()
    assert recorded[-1] == [
        str(double_commander_exe),
        "-C",
        "-L",
        str(source_file),
    ]

    _select_paths(source_tab, [source_file, source_second_file])
    window.explorer_here_source_action.trigger()
    assert recorded[-1] == [str(explorer_exe), str(source_root)]


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

    assert len(window.panel_widgets) == 2
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    assert panel.tab_count() == 1

    window.panels_coordinator.new_tab_in_active_panel()
    assert window.panels_coordinator.active_panel().tab_count() == 2

    window.panels_coordinator.close_active_tab()
    assert window.panels_coordinator.active_panel().tab_count() == 1

    window.panels_coordinator.split_active_panel(Qt.Orientation.Horizontal)
    assert len(window.panel_widgets) == 3

    window.panels_coordinator.close_active_panel()
    assert len(window.panel_widgets) == 2


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

    panel = window.panels_coordinator.active_panel()
    tab = panel.current_tab()
    assert tab is not None

    window.show_hidden_action.setChecked(False)
    assert tab.model.filter() & tab.model.filter().NoDotAndDotDot
    assert not (tab.model.filter() & tab.model.filter().Hidden)

    window.show_hidden_action.setChecked(True)
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

    assert all(
        not panel.widget_map_coordinator.enabled()
        for panel in window.panel_widgets.values()
    )

    window.show_widget_map_action.setChecked(True)
    assert all(
        panel.widget_map_coordinator.enabled()
        for panel in window.panel_widgets.values()
    )

    window.new_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 3
    assert all(
        panel.widget_map_coordinator.enabled()
        for panel in window.panel_widgets.values()
    )

    window.show_widget_map_action.setChecked(False)
    assert all(
        not panel.widget_map_coordinator.enabled()
        for panel in window.panel_widgets.values()
    )


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

    window.panels_coordinator.new_tab_in_active_panel()
    source_panel = window.panels_coordinator.active_panel()
    assert source_panel is not None
    source_panel.tabs.setCurrentIndex(0)
    source_tab_count = source_panel.tab_count()
    source_current_index = source_panel.tabs.currentIndex()

    window.clone_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 3
    cloned_panel_vertical = window.panels_coordinator.active_panel()
    assert cloned_panel_vertical is not None
    assert cloned_panel_vertical.tab_count() == source_tab_count
    assert cloned_panel_vertical.tabs.currentIndex() == source_current_index

    window.clone_horizontal_panel_action.trigger()
    assert len(window.panel_widgets) == 6
    cloned_panel_horizontal = window.panels_coordinator.active_panel()
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
    window.on_top_action.toggled.connect(toggled_events.append)

    window.set_on_top(True)

    assert toggled_events == []
    assert window.on_top_action.isChecked() is True


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

    source.panels_coordinator.new_tab_in_active_panel()
    source.clone_vertical_panel_action.trigger()
    source.set_on_top(True)

    source.clone_window_action.trigger()
    assert len(controller.created_windows) == 1

    cloned = controller.created_windows[0]
    qtbot.addWidget(cloned)
    qtbot.waitUntil(cloned.isVisible)

    assert cloned.panel_tree.to_dict() == source.panel_tree.to_dict()
    assert cloned.on_top_action.isChecked() is True
    assert cloned.isMaximized() is False

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

    window.close_window_action.trigger()
    qtbot.waitUntil(lambda: not window.isVisible())

    assert controller.closed_windows
    assert controller.closed_windows[-1] is window


def test_f2_refreshes_all_panels_and_ctrl_r_refreshes_active_panel(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="shortcut-refresh-window",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()
    window.new_vertical_panel_action.trigger()

    ordered_ids = [panel_id for row in window.layout_rows for panel_id in row]
    source_panel = window.panel_widgets[ordered_ids[0]]
    source_panel.current_tab().view.setFocus()
    window.panels_coordinator.set_active_panel(source_panel.panel_id)

    refresh_calls: list[int] = []
    for panel_id, panel in window.panel_widgets.items():
        monkeypatch.setattr(
            panel.navigation_coordinator,
            "refresh_current_path",
            lambda panel_id=panel_id: refresh_calls.append(panel_id),
        )

    window.reread_visible_lists_shortcut.activated.emit()
    qtbot.waitUntil(lambda: len(refresh_calls) == len(window.panel_widgets))
    assert sorted(refresh_calls) == sorted(window.panel_widgets)

    refresh_calls.clear()
    window.refresh_action.trigger()
    qtbot.waitUntil(lambda: refresh_calls == [source_panel.panel_id])


def test_file_shortcuts_use_expected_file_actions(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="shortcut-file-actions",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    root = tmp_path / "files-root"
    root.mkdir()
    file_path = root / "alpha.txt"
    file_path.write_text("alpha", encoding="utf-8")
    directory = root / "folder"
    directory.mkdir()

    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    tab = panel.current_tab()
    assert tab is not None
    tab.navigation.set_path(root)
    qtbot.waitUntil(lambda: tab.model.index(str(file_path)).isValid())
    tab.view.setFocus()

    opened_default: list[Path] = []
    opened_viewer: list[Path] = []
    edited_paths: list[Path] = []
    monkeypatch.setattr(
        "many_panelz_explorer._explorer_tab_actions.file_ops.open_with_default",
        lambda path: opened_default.append(Path(path)),
    )
    monkeypatch.setattr(
        "many_panelz_explorer._explorer_tab_actions.file_ops.open_with_viewer",
        lambda path: opened_viewer.append(Path(path)) or False,
    )
    monkeypatch.setattr(
        "many_panelz_explorer._explorer_tab_actions.file_ops.open_in_text_editor",
        lambda path: edited_paths.append(Path(path)),
    )
    monkeypatch.setattr(
        QInputDialog,
        "getText",
        lambda *_a, **_k: ("fresh.txt", True),
    )

    _select_paths(tab, [file_path])
    QTest.keyClick(tab.view, Qt.Key_F3)
    assert opened_default == [file_path]

    opened_default.clear()
    opened_viewer.clear()
    tab.view.selectionModel().clearSelection()
    tab.view.setCurrentIndex(tab.model.index(str(file_path)))
    QTest.keyClick(tab.view, Qt.Key_F3, Qt.AltModifier)
    qtbot.waitUntil(lambda: opened_viewer == [file_path])
    assert opened_default == [file_path]
    assert window.statusBar().currentMessage() == (
        "No dedicated viewer configured; used default opener."
    )

    _select_paths(tab, [file_path])
    QTest.keyClick(tab.view, Qt.Key_F4)
    assert edited_paths == [file_path]

    QTest.keyClick(tab.view, Qt.Key_F4, Qt.ShiftModifier)
    created = root / "fresh.txt"
    qtbot.waitUntil(created.exists)
    assert edited_paths[-1] == created
    qtbot.waitUntil(
        lambda: Path(tab.model.filePath(tab.view.currentIndex())) == created
    )

    _select_paths(tab, [directory])
    opened_default.clear()
    QTest.keyClick(tab.view, Qt.Key_F3)
    qtbot.waitUntil(lambda: tab.navigation.path == directory)
    assert opened_default == []


def test_file_list_shortcuts_cover_selection_context_and_clipboard(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="shortcut-file-list",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    root = tmp_path / "selection-root"
    root.mkdir()
    first_file = root / "one.txt"
    second_file = root / "two.txt"
    first_file.write_text("one", encoding="utf-8")
    second_file.write_text("two", encoding="utf-8")

    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    tab = panel.current_tab()
    assert tab is not None
    tab.navigation.set_path(root)
    qtbot.waitUntil(lambda: tab.model.index(str(second_file)).isValid())
    tab.view.setFocus()

    _select_paths(tab, [first_file])
    delete_calls: list[str] = []
    monkeypatch.setattr(
        window.operations_coordinator,
        "build_operation_request",
        lambda **_kwargs: delete_calls.append("delete") or None,
    )
    context_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        tab._actions,
        "open_context_menu",
        lambda pos: context_calls.append((pos.x(), pos.y())),
    )
    zip_calls: list[tuple[list[Path], Path]] = []
    monkeypatch.setattr(
        QInputDialog,
        "getText",
        lambda *_a, **_k: ("Created Folder", True),
    )
    monkeypatch.setattr(
        "many_panelz_explorer._explorer_tab_actions.QFileDialog.getSaveFileName",
        lambda *_a, **_k: (str(root / "archive.zip"), "ZIP Files (*.zip)"),
    )
    monkeypatch.setattr(
        "many_panelz_explorer._explorer_tab_actions.file_ops.zip_create",
        lambda sources, archive_path: zip_calls.append(
            ([Path(item) for item in sources], Path(archive_path))
        ),
    )

    QTest.keyClick(tab.view, Qt.Key_A, Qt.ControlModifier)
    selected_after_ctrl_a = {
        Path(tab.model.filePath(index))
        for index in tab.view.selectionModel().selectedRows()
        if not tab.model.is_parent_index(index)
    }
    assert selected_after_ctrl_a == {first_file, second_file}

    _select_paths(tab, [first_file])
    QTest.keyClick(tab.view, Qt.Key_P, Qt.ControlModifier)
    assert QApplication.clipboard().text() == str(first_file)

    tab.view.selectionModel().clearSelection()
    QTest.keyClick(tab.view, Qt.Key_P, Qt.ControlModifier)
    assert QApplication.clipboard().text() == str(root)
    assert window.statusBar().currentMessage() == "Copied panel path to clipboard."

    _select_paths(tab, [first_file, second_file])
    QTest.keyClick(tab.view, Qt.Key_P, Qt.ControlModifier)
    assert QApplication.clipboard().text() == str(root)

    QTest.keyClick(tab.view, Qt.Key_F10, Qt.ShiftModifier)
    assert len(context_calls) == 1

    _select_paths(tab, [first_file])
    QTest.keyClick(tab.view, Qt.Key_Delete)
    window.delete_selection_action.trigger()
    assert delete_calls == ["delete", "delete"]

    QTest.keyClick(tab.view, Qt.Key_F7)
    assert (root / "Created Folder").exists() is True

    qtbot.waitUntil(lambda: tab.model.index(str(first_file)).isValid())
    _select_paths(tab, [first_file])
    QTest.keyClick(tab.view, Qt.Key_F5, Qt.AltModifier)
    assert zip_calls == [([first_file], root / "archive.zip")]


def test_alt_f1_and_shift_esc_use_active_panel_and_window_helpers(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = _ControllerStub()
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="shortcut-root-picker",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()
    window.new_vertical_panel_action.trigger()

    ordered = _ordered_panels(window)
    first_panel = ordered[0]
    active_panel = ordered[-1]
    window.panels_coordinator.set_active_panel(first_panel.panel_id)
    window.panels_coordinator.set_active_panel(active_panel.panel_id)
    active_panel.current_tab().view.setFocus()

    first_calls: list[str] = []
    active_calls: list[str] = []
    monkeypatch.setattr(
        first_panel.navigation_coordinator,
        "show_root_picker_menu",
        lambda: first_calls.append("first"),
    )
    monkeypatch.setattr(
        active_panel.navigation_coordinator,
        "show_root_picker_menu",
        lambda: active_calls.append("active"),
    )

    window.root_picker_shortcut.activated.emit()
    window.minimize_windows_shortcut.activated.emit()

    assert first_calls == []
    assert active_calls == ["active"]
    assert controller.minimize_calls == 1


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
    assert window_on.panels_coordinator.active_panel() is not None
    assert window_on.panels_coordinator.active_panel().root_combo.isVisible() is True
    qtbot.waitUntil(
        lambda: window_on.panels_coordinator.active_panel().root_combo.width() > 0
    )

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
    assert window_off.panels_coordinator.active_panel() is not None
    assert window_off.panels_coordinator.active_panel().root_combo.isVisible() is False


def test_apply_ui_preferences_updates_toolbar_visibility_flags(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="toolbar-flags",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()
    window.new_vertical_panel_action.trigger()

    window.preferences_coordinator.apply_ui_preferences(
        UiPreferences(
            new_context_mode="clone_active_path",
            show_hidden_default=True,
            show_root_dropdown=True,
            column_width_auto_align_mode="current_panel_tabs",
            show_refresh_button=False,
            show_root_buttons=False,
            show_address_bar=False,
            show_navigation_buttons=False,
            app_font_family="",
            app_font_size_pt=11,
            file_list_use_app_font=False,
            file_list_font_family="",
            file_list_font_size_pt=14,
            navigation_use_app_font=False,
            navigation_font_family="",
            navigation_font_size_pt=13,
            active_panel_tint_color_hex="#A8B6C4",
            active_panel_tint_intensity_percent=24,
            target_panel_tint_color_hex="#D2CCAA",
            target_panel_tint_intensity_percent=28,
        )
    )

    for panel in window.panel_widgets.values():
        qtbot.waitUntil(lambda p=panel: p.root_combo.isVisible())
        assert panel.refresh_btn.isVisible() is False
        assert panel.root_buttons_host.isVisible() is False
        assert panel.root_combo.isVisible() is True
        assert panel.address_edit.isVisible() is False
        assert panel.back_btn.isVisible() is False
        assert panel.forward_btn.isVisible() is False
        assert panel.up_btn.isVisible() is False
        assert panel.root_btn.isVisible() is False
        qtbot.waitUntil(lambda p=panel: p.root_combo.width() > 0)
        assert panel.current_tab().view.font().pointSize() == 14
        assert panel.address_edit.font().pointSize() == 13

    source_panel = next(iter(window.panel_widgets.values()))
    new_tab = source_panel.add_tab(source_panel.current_path())
    assert new_tab.view.font().pointSize() == 14


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
    qtbot.waitUntil(source.isMaximized)

    source.panels_coordinator.new_tab_in_active_panel()
    source.panels_coordinator.split_active_panel(Qt.Orientation.Horizontal)
    source.set_on_top(True)
    assert len(source.panel_widgets) == 3

    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("My View", True))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_a, **_k: QMessageBox.StandardButton.Yes,
    )
    source.save_view_action.trigger()

    saved = settings.get_saved_view("My View")
    assert saved is not None
    assert "geometry_b64" in saved
    assert saved["maximized"] is True
    assert saved["on_top"] is True

    source.panels_coordinator.close_active_panel()
    assert len(source.panel_widgets) == 2

    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("My View", True))
    source.replace_view_action.trigger()
    assert len(source.panel_widgets) == 3
    assert source.on_top_action.isChecked() is True
    qtbot.waitUntil(source.isMaximized)

    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("restore should use submenu, not dialog")
        ),
    )
    source.views_coordinator.populate_restore_view_menu(source.restore_view_menu)
    restore_actions = [
        a for a in source.restore_view_menu.actions() if a.text() == "My View"
    ]
    assert restore_actions
    restore_actions[0].trigger()
    assert len(controller.created_windows) == 1
    restored = controller.created_windows[0]
    qtbot.addWidget(restored)
    assert len(restored.panel_widgets) == 3
    assert restored.on_top_action.isChecked() is True
    qtbot.waitUntil(restored.isMaximized)


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

    assert [len(row) for row in window.layout_rows] == [2]

    window.new_vertical_panel_action.trigger()
    assert [len(row) for row in window.layout_rows] == [3]

    window.new_horizontal_panel_action.trigger()
    assert [len(row) for row in window.layout_rows] == [3, 3]

    window.new_vertical_panel_action.trigger()
    assert [len(row) for row in window.layout_rows] == [3, 4]


def test_copy_to_target_uses_last_active_non_source_panel(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    settings.active_panel_tint_color_hex = "#A8B6C4"
    settings.active_panel_tint_intensity_percent = 24
    settings.target_panel_tint_color_hex = "#D2CCAA"
    settings.target_panel_tint_intensity_percent = 28
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="target-resolution",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    window.new_horizontal_panel_action.trigger()
    assert len(window.panel_widgets) == 6

    ordered_ids = [pid for row in window.layout_rows for pid in row]
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

    source_panel.current_tab().navigation.set_path(src_dir)
    target_panel.current_tab().navigation.set_path(dst_dir)

    monkeypatch.setattr(
        source_panel.current_tab(), "selected_paths", lambda: [src_file]
    )
    captured: list[Path] = []
    queue_manager = window.controller.operation_queue_manager
    original_submit = queue_manager.submit

    def _capture_submit(request):
        captured.append(
            Path(request.target_dir) if request.target_dir is not None else Path()
        )
        return original_submit(request)

    monkeypatch.setattr(queue_manager, "submit", _capture_submit)

    window.panels_coordinator.set_active_panel(preferred_target_id)
    window.panels_coordinator.set_active_panel(source_id)
    window.copy_to_target_action.trigger()

    assert captured == [dst_dir]
    assert source_panel.pane_role == "active"
    assert target_panel.pane_role == "target"
    assert "border: none" in source_panel.styleSheet()
    assert "background-color: rgba(168, 182, 196, 61)" in source_panel.styleSheet()
    assert "border: none" in target_panel.styleSheet()
    assert "background-color: rgba(210, 204, 170, 71)" in target_panel.styleSheet()


def test_status_bar_persistent_source_target_paths_update_with_context_changes(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="status-persistent-paths",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window.layout_rows for pid in row]
    assert len(ordered_ids) >= 2
    source_id = ordered_ids[0]
    target_id = ordered_ids[1]
    source_panel = window.panel_widgets[source_id]
    target_panel = window.panel_widgets[target_id]

    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    source_panel.current_tab().navigation.set_path(source_dir)
    target_panel.current_tab().navigation.set_path(target_dir)

    window.panels_coordinator.set_active_panel(target_id)
    window.panels_coordinator.set_active_panel(source_id)

    qtbot.waitUntil(
        lambda: window.source_path_label.text() == f"Source path: {source_dir}"
    )
    assert window.target_path_label.text() == f"Target path: {target_dir}"
    assert window.source_path_label.toolTip() == str(source_dir)
    assert window.target_path_label.toolTip() == str(target_dir)

    window.statusBar().showMessage("Temporary status", 60)
    assert window.source_path_label.text() == f"Source path: {source_dir}"
    assert window.target_path_label.text() == f"Target path: {target_dir}"
    qtbot.wait(90)
    assert window.source_path_label.text() == f"Source path: {source_dir}"
    assert window.target_path_label.text() == f"Target path: {target_dir}"

    nested_source = source_dir / "nested"
    nested_source.mkdir()
    source_panel.current_tab().navigation.set_path(nested_source)
    qtbot.waitUntil(
        lambda: window.source_path_label.text() == f"Source path: {nested_source}"
    )


def test_storage_overview_status_row_visible_and_populated_by_default(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    settings.show_storage_overview_status_row = True
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    entries = [
        mounts.StorageUsageEntry(
            root_path=Path("C:\\"),
            display_root="C:",
            volume_label="System",
            bytes_used=600,
            bytes_total=1_000,
            usage_ratio=0.6,
        ),
        mounts.StorageUsageEntry(
            root_path=Path("C:\\mounts\\media01"),
            display_root="C:\\mounts\\media01",
            volume_label="Media",
            bytes_used=200,
            bytes_total=1_000,
            usage_ratio=0.2,
        ),
    ]
    monkeypatch.setattr(
        "many_panelz_explorer.ui.window.status.mounts.list_storage_usage_entries",
        lambda current_path=None: entries,
    )

    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="status-storage-default",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    qtbot.waitUntil(lambda: window.storage_overview_row.isVisible() is True)
    qtbot.waitUntil(lambda: len(_visible_storage_labels(window)) == len(entries))
    tooltips = [label.toolTip() for label in _visible_storage_labels(window)]
    assert any("C: System" in tooltip for tooltip in tooltips)
    assert any("C:\\mounts\\media01 Media" in tooltip for tooltip in tooltips)


def test_storage_overview_status_row_hides_when_disabled(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    settings.show_storage_overview_status_row = False
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    entries = [
        mounts.StorageUsageEntry(
            root_path=Path("C:\\"),
            display_root="C:",
            volume_label="System",
            bytes_used=600,
            bytes_total=1_000,
            usage_ratio=0.6,
        )
    ]
    monkeypatch.setattr(
        "many_panelz_explorer.ui.window.status.mounts.list_storage_usage_entries",
        lambda current_path=None: entries,
    )

    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="status-storage-disabled",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    assert window.storage_overview_row.isVisible() is False
    assert _visible_storage_labels(window) == []


def test_storage_overview_status_row_hides_when_no_valid_entries(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    settings.show_storage_overview_status_row = True
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    monkeypatch.setattr(
        "many_panelz_explorer.ui.window.status.mounts.list_storage_usage_entries",
        lambda current_path=None: [],
    )

    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="status-storage-empty",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()

    assert window.storage_overview_row.isVisible() is False
    assert _visible_storage_labels(window) == []


def test_storage_overview_status_row_elides_with_full_tooltip(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    settings.show_storage_overview_status_row = True
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    entries = [
        mounts.StorageUsageEntry(
            root_path=Path(f"C:\\mounts\\volume_{index:02d}"),
            display_root=f"C:\\mounts\\volume_{index:02d}",
            volume_label=f"Label_{index:02d}",
            bytes_used=10_000_000 + index,
            bytes_total=20_000_000 + index,
            usage_ratio=0.5,
        )
        for index in range(12)
    ]
    monkeypatch.setattr(
        "many_panelz_explorer.ui.window.status.mounts.list_storage_usage_entries",
        lambda current_path=None: entries,
    )

    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="status-storage-elide",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.resize(380, window.height())
    window.show()
    window.status_coordinator.refresh_storage_overview_status()

    qtbot.waitUntil(lambda: len(_visible_storage_labels(window)) == len(entries))
    assert any(label.toolTip() for label in _visible_storage_labels(window))
    assert any(
        label.text() != label.toolTip()
        and ("\u2026" in label.text() or "..." in label.text())
        for label in _visible_storage_labels(window)
    )


def test_storage_overview_status_row_uses_configured_byte_format(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    settings.show_storage_overview_status_row = True
    settings.byte_thousands_separator = "."
    settings.byte_decimal_separator = ","
    settings.status_bar_byte_format_mode = "always_mib"
    settings.status_bar_storage_label_template = (
        "{disk_root} {disk_label} {used_space}/{total_space} "
        "{usage_percentage:.1f}% {usage_indicator}"
    )
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    entries = [
        mounts.StorageUsageEntry(
            root_path=Path("C:\\"),
            display_root="C:",
            volume_label="System",
            bytes_used=1_500_000,
            bytes_total=3_000_000,
            usage_ratio=0.5,
        )
    ]
    monkeypatch.setattr(
        "many_panelz_explorer.ui.window.status.mounts.list_storage_usage_entries",
        lambda current_path=None: entries,
    )

    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="status-storage-byte-format",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(window)
    window.show()
    window.status_coordinator.refresh_storage_overview_status()

    qtbot.waitUntil(lambda: len(_visible_storage_labels(window)) == len(entries))
    labels = _visible_storage_labels(window)
    label_texts = [label.full_text() for label in labels]
    tooltips = [label.toolTip() for label in labels]
    assert any("C: System 1,43 MiB/2,86 MiB" in text for text in label_texts)
    assert any("50.0%" in text or "50,0%" in text for text in label_texts)
    assert any(
        "\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591" in text
        for text in label_texts
    )
    assert any("MiB" in tooltip for tooltip in tooltips)
    assert any("Usage:" in tooltip and "50.00%" in tooltip for tooltip in tooltips)
    assert any(
        "Usage bar:" in tooltip
        and "\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591" in tooltip
        for tooltip in tooltips
    )
    assert any(
        "Free bar:" in tooltip
        and "\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591" in tooltip
        for tooltip in tooltips
    )


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

    monkeypatch.setattr(
        window.operations_coordinator,
        "prompt_conflict_resolution",
        lambda *_a, **_k: "skip",
    )
    assert (
        window.operations_coordinator.copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "skip"
    )
    assert existing.read_text(encoding="utf-8") == "dst"

    monkeypatch.setattr(
        window.operations_coordinator,
        "prompt_conflict_resolution",
        lambda *_a, **_k: "rename",
    )
    assert (
        window.operations_coordinator.copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "done"
    )
    assert (destination_dir / "source (1).txt").exists()

    monkeypatch.setattr(
        window.operations_coordinator,
        "prompt_conflict_resolution",
        lambda *_a, **_k: "overwrite",
    )
    source.write_text("new", encoding="utf-8")
    assert (
        window.operations_coordinator.copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "done"
    )
    assert existing.read_text(encoding="utf-8") == "new"

    monkeypatch.setattr(
        window.operations_coordinator,
        "prompt_conflict_resolution",
        lambda *_a, **_k: "cancel",
    )
    assert (
        window.operations_coordinator.copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "cancel"
    )


def test_column_width_sync_stays_within_active_pane_tabs(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "current_panel_tabs"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="column-sync-scope",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window.layout_rows for pid in row]
    assert len(ordered_ids) >= 2
    first_panel = window.panel_widgets[ordered_ids[0]]
    second_panel = window.panel_widgets[ordered_ids[1]]

    first_primary = first_panel.current_tab()
    first_secondary = first_panel.add_tab(first_panel.current_path())
    second_tab = second_panel.current_tab()
    assert first_primary is not None
    assert first_secondary is not None
    assert second_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [first_primary, first_secondary, second_tab],
        path=root,
    )
    first_secondary.view.setColumnWidth(0, 100)
    second_tab.view.setColumnWidth(0, 100)
    first_panel.tabs.setCurrentWidget(first_primary)
    first_primary.view.setColumnWidth(0, 360)
    qtbot.waitUntil(lambda: first_secondary.view.columnWidth(0) == 360)
    assert second_tab.view.columnWidth(0) != 360


def test_column_width_auto_align_none_disables_propagation(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "none"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="column-sync-none",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window.layout_rows for pid in row]
    first_panel = window.panel_widgets[ordered_ids[0]]
    second_panel = window.panel_widgets[ordered_ids[1]]

    first_primary = first_panel.current_tab()
    first_secondary = first_panel.add_tab(first_panel.current_path())
    second_tab = second_panel.current_tab()
    assert first_primary is not None
    assert first_secondary is not None
    assert second_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [first_primary, first_secondary, second_tab],
        path=root,
    )
    first_secondary.view.setColumnWidth(0, 100)
    second_tab.view.setColumnWidth(0, 100)
    first_primary.view.setColumnWidth(0, 370)
    qtbot.wait(220)

    assert first_secondary.view.columnWidth(0) != 370
    assert second_tab.view.columnWidth(0) != 370


def test_column_width_auto_align_current_window_syncs_current_window_only(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "current_window_panels_tabs"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerBroadcastStub()

    first = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-sync-global-first",
        roots_provider=roots_provider,
    )
    second = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-sync-global-second",
        roots_provider=roots_provider,
    )
    first.default_maximize_on_first_show = False
    second.default_maximize_on_first_show = False
    controller.windows.extend([first, second])
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()

    source_panel = first.panels_coordinator.active_panel()
    assert source_panel is not None
    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    assert source_primary is not None
    assert source_secondary is not None

    target_panel = second.panels_coordinator.active_panel()
    assert target_panel is not None
    target_tab = target_panel.current_tab()
    assert target_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [source_primary, source_secondary, target_tab],
        path=root,
    )
    source_panel.tabs.setCurrentWidget(source_primary)
    qtbot.waitUntil(lambda: source_panel.current_tab() is source_primary)
    source_primary.view.setColumnWidth(0, 390)
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 390)
    assert target_tab.view.columnWidth(0) != 390


def test_column_width_auto_align_all_windows_syncs_all_open_windows(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "all_windows_panels_tabs"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerBroadcastStub()

    first = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-sync-global-first",
        roots_provider=roots_provider,
    )
    second = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-sync-global-second",
        roots_provider=roots_provider,
    )
    first.default_maximize_on_first_show = False
    second.default_maximize_on_first_show = False
    controller.windows.extend([first, second])
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()

    source_panel = first.panels_coordinator.active_panel()
    assert source_panel is not None
    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    assert source_primary is not None
    assert source_secondary is not None

    target_panel = second.panels_coordinator.active_panel()
    assert target_panel is not None
    target_tab = target_panel.current_tab()
    assert target_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [source_primary, source_secondary, target_tab],
        path=root,
    )
    source_panel.tabs.setCurrentWidget(source_primary)
    qtbot.waitUntil(lambda: source_panel.current_tab() is source_primary)
    source_primary.view.setColumnWidth(0, 390)
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 390)
    qtbot.waitUntil(lambda: target_tab.view.columnWidth(0) == 390)


def test_view_align_columns_current_panel_tabs_is_one_shot(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "none"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="column-align-view-current",
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window.layout_rows for pid in row]
    source_panel = window.panel_widgets[ordered_ids[0]]
    other_panel = window.panel_widgets[ordered_ids[1]]

    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    other_tab = other_panel.current_tab()
    assert source_primary is not None
    assert source_secondary is not None
    assert other_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [source_primary, source_secondary, other_tab],
        path=root,
    )
    source_secondary.view.setColumnWidth(0, 100)
    other_tab.view.setColumnWidth(0, 100)
    source_panel.tabs.setCurrentWidget(source_primary)
    source_primary.view.setColumnWidth(0, 365)
    assert source_secondary.view.columnWidth(0) != 365
    other_original = other_tab.view.columnWidth(0)

    window.panels_coordinator.set_active_panel(source_panel.panel_id)
    window.align_columns_current_panel_tabs_action.trigger()
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 365)
    assert other_tab.view.columnWidth(0) == other_original
    assert settings.column_width_auto_align_mode == "none"


def test_view_align_columns_all_panels_tabs_is_one_shot_within_current_window(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "none"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerBroadcastStub()

    first = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-align-view-all-first",
        roots_provider=roots_provider,
    )
    second = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-align-view-all-second",
        roots_provider=roots_provider,
    )
    first.default_maximize_on_first_show = False
    second.default_maximize_on_first_show = False
    controller.windows.extend([first, second])
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()

    first.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in first.layout_rows for pid in row]
    source_panel = first.panel_widgets[ordered_ids[0]]
    other_panel = first.panel_widgets[ordered_ids[1]]

    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    other_tab = other_panel.current_tab()
    second_panel = second.panels_coordinator.active_panel()
    second_tab = second_panel.current_tab() if second_panel else None
    assert source_primary is not None
    assert source_secondary is not None
    assert other_tab is not None
    assert second_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [source_primary, source_secondary, other_tab, second_tab],
        path=root,
    )
    source_secondary.view.setColumnWidth(0, 100)
    other_tab.view.setColumnWidth(0, 100)
    second_tab.view.setColumnWidth(0, 100)
    source_panel.tabs.setCurrentWidget(source_primary)
    source_primary.view.setColumnWidth(0, 355)
    assert source_secondary.view.columnWidth(0) != 355
    assert other_tab.view.columnWidth(0) != 355
    assert second_tab.view.columnWidth(0) != 355

    first.panels_coordinator.set_active_panel(source_panel.panel_id)
    first.align_columns_all_panels_tabs_action.trigger()
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 355)
    qtbot.waitUntil(lambda: other_tab.view.columnWidth(0) == 355)
    assert second_tab.view.columnWidth(0) != 355
    assert settings.column_width_auto_align_mode == "none"


def test_view_align_columns_all_windows_is_one_shot_across_windows(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "none"
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerBroadcastStub()

    first = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-align-view-all-first",
        roots_provider=roots_provider,
    )
    second = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="column-align-view-all-second",
        roots_provider=roots_provider,
    )
    first.default_maximize_on_first_show = False
    second.default_maximize_on_first_show = False
    controller.windows.extend([first, second])
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()

    first.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in first.layout_rows for pid in row]
    source_panel = first.panel_widgets[ordered_ids[0]]
    other_panel = first.panel_widgets[ordered_ids[1]]

    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    other_tab = other_panel.current_tab()
    second_panel = second.panels_coordinator.active_panel()
    second_tab = second_panel.current_tab() if second_panel else None
    assert source_primary is not None
    assert source_secondary is not None
    assert other_tab is not None
    assert second_tab is not None

    root = _column_test_root(tmp_path)
    _prepare_tabs_for_column_assertions(
        qtbot,
        [source_primary, source_secondary, other_tab, second_tab],
        path=root,
    )
    source_secondary.view.setColumnWidth(0, 100)
    other_tab.view.setColumnWidth(0, 100)
    second_tab.view.setColumnWidth(0, 100)
    source_panel.tabs.setCurrentWidget(source_primary)
    source_primary.view.setColumnWidth(0, 355)
    assert source_secondary.view.columnWidth(0) != 355
    assert other_tab.view.columnWidth(0) != 355
    assert second_tab.view.columnWidth(0) != 355

    first.panels_coordinator.set_active_panel(source_panel.panel_id)
    first.align_columns_all_windows_action.trigger()
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 355)
    qtbot.waitUntil(lambda: other_tab.view.columnWidth(0) == 355)
    qtbot.waitUntil(lambda: second_tab.view.columnWidth(0) == 355)
    assert settings.column_width_auto_align_mode == "none"


def test_view_fit_columns_applies_to_all_tabs_in_current_window(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "fit-columns-root"
    root.mkdir()
    (root / "very_long_filename_for_column_fitting_validation.txt").write_text(
        "x",
        encoding="utf-8",
    )

    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)
    controller = _ControllerStub()
    window = ExplorerWindow(
        controller=controller,
        settings=settings,
        window_id="fit-columns-current-window",
        initial_path=root,
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)

    primary_panel, secondary_panel = _ordered_panels(window)[:2]
    primary_tab = primary_panel.current_tab()
    secondary_tab = secondary_panel.current_tab()
    assert primary_tab is not None
    assert secondary_tab is not None
    extra_tab = primary_panel.add_tab(root)
    tabs = [primary_tab, extra_tab, secondary_tab]
    for tab in tabs:
        tab.navigation.set_path(root)
    window.show()

    qtbot.waitUntil(lambda: all(tab.model.rowCount() >= 1 for tab in tabs))
    for tab in tabs:
        tab.view.setColumnWidth(0, 50)

    window.fit_columns_action.trigger()

    qtbot.waitUntil(lambda: all(tab.view.columnWidth(0) > 50 for tab in tabs))
    assert controller.broadcast_calls == []


def test_autofit_columns_fits_all_tabs_on_first_show(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "autofit-startup-root"
    root.mkdir()
    (root / "very_long_filename_for_autofit_startup.txt").write_text(
        "x",
        encoding="utf-8",
    )

    settings = SettingsManager()
    settings.autofit_columns = True
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="autofit-startup",
        initial_path=root,
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)

    primary_panel, secondary_panel = _ordered_panels(window)[:2]
    primary_tab = primary_panel.current_tab()
    secondary_tab = secondary_panel.current_tab()
    assert primary_tab is not None
    assert secondary_tab is not None
    extra_tab = primary_panel.add_tab(root)
    tabs = [primary_tab, extra_tab, secondary_tab]
    for tab in tabs:
        tab.navigation.set_path(root)
        tab.view.setColumnWidth(0, 50)

    window.show()

    qtbot.waitUntil(lambda: all(tab.model.rowCount() >= 1 for tab in tabs))
    qtbot.waitUntil(lambda: all(tab.view.columnWidth(0) > 50 for tab in tabs))


def test_autofit_columns_resize_is_debounced(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "autofit-resize-root"
    root.mkdir()
    (root / "very_long_filename_for_autofit_resize.txt").write_text(
        "x",
        encoding="utf-8",
    )

    settings = SettingsManager()
    settings.autofit_columns = True
    settings.sync()
    roots_provider = _test_roots_provider(tmp_path)
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="autofit-resize",
        initial_path=root,
        roots_provider=roots_provider,
    )
    window.default_maximize_on_first_show = False
    qtbot.addWidget(window)

    coordinator = window.panels_coordinator.column_sync_coordinator
    fit_calls: list[int] = []
    original_fit = coordinator._fit_columns_all_panels

    def _count_fit_calls() -> bool:
        fit_calls.append(1)
        return original_fit()

    monkeypatch.setattr(coordinator, "_fit_columns_all_panels", _count_fit_calls)

    window.show()
    qtbot.waitUntil(lambda: len(fit_calls) == 1)

    window.resize(880, 620)
    window.resize(900, 620)
    window.resize(920, 620)

    qtbot.wait(80)
    assert len(fit_calls) == 1
    qtbot.waitUntil(lambda: len(fit_calls) == 2)
