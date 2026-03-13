import os
from collections.abc import Callable
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox

from many_panelz_explorer import mounts
from many_panelz_explorer._operations.queue_manager import OperationQueueManager
from many_panelz_explorer._operations.types import OperationExecutionPreferences
from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer._settings.models import UiPreferences
from many_panelz_explorer.operation_queue_widgets import OperationQueueTableModel
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def __init__(self) -> None:
        self.closed_windows: list[ExplorerWindow] = []
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
        source_tab: object | None = None,
    ) -> None:
        _ = widths, source_window, source_panel_id, source_tab

    def show_queue_floating_window(self):
        return None


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
        source_tab: object | None = None,
    ) -> None:
        for window in list(self.windows):
            window.apply_column_widths_all_panels(
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
        not panel.widget_map_enabled() for panel in window.panel_widgets.values()
    )

    window.show_widget_map_action.setChecked(True)
    assert all(panel.widget_map_enabled() for panel in window.panel_widgets.values())

    window.new_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 2
    assert all(panel.widget_map_enabled() for panel in window.panel_widgets.values())

    window.show_widget_map_action.setChecked(False)
    assert all(
        not panel.widget_map_enabled() for panel in window.panel_widgets.values()
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

    window.new_tab_in_active_panel()
    source_panel = window.active_panel()
    assert source_panel is not None
    source_panel.tabs.setCurrentIndex(0)
    source_tab_count = source_panel.tab_count()
    source_current_index = source_panel.tabs.currentIndex()

    window.clone_vertical_panel_action.trigger()
    assert len(window.panel_widgets) == 2
    cloned_panel_vertical = window.active_panel()
    assert cloned_panel_vertical is not None
    assert cloned_panel_vertical.tab_count() == source_tab_count
    assert cloned_panel_vertical.tabs.currentIndex() == source_current_index

    window.clone_horizontal_panel_action.trigger()
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

    source.new_tab_in_active_panel()
    source.clone_vertical_panel_action.trigger()
    source.set_on_top(True)

    source.clone_window_action.trigger()
    assert len(controller.created_windows) == 1

    cloned = controller.created_windows[0]
    qtbot.addWidget(cloned)

    assert cloned.panel_tree.to_dict() == source.panel_tree.to_dict()
    assert cloned.on_top_action.isChecked() is True

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
    qtbot.waitUntil(lambda: window_on.active_panel().root_combo.width() > 0)

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

    window.apply_ui_preferences(
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
    source.save_view_action.trigger()

    saved = settings.get_saved_view("My View")
    assert saved is not None
    assert "geometry_b64" in saved
    assert saved["on_top"] is True

    source.close_active_panel()
    assert len(source.panel_widgets) == 1

    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("My View", True))
    source.replace_view_action.trigger()
    assert len(source.panel_widgets) == 2
    assert source.on_top_action.isChecked() is True

    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("restore should use submenu, not dialog")
        ),
    )
    source.populate_restore_view_menu()
    restore_actions = [
        a for a in source.restore_view_menu.actions() if a.text() == "My View"
    ]
    assert restore_actions
    restore_actions[0].trigger()
    assert len(controller.created_windows) == 1
    restored = controller.created_windows[0]
    qtbot.addWidget(restored)
    assert len(restored.panel_widgets) == 2
    assert restored.on_top_action.isChecked() is True


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

    window.new_vertical_panel_action.trigger()
    assert [len(row) for row in window._layout_rows] == [2]

    window.new_horizontal_panel_action.trigger()
    assert [len(row) for row in window._layout_rows] == [2, 2]

    window.new_vertical_panel_action.trigger()
    assert [len(row) for row in window._layout_rows] == [2, 3]


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

    window._set_active_panel(preferred_target_id)
    window._set_active_panel(source_id)
    window.copy_to_target_action.trigger()

    assert captured == [dst_dir]
    assert source_panel._pane_role == "active"
    assert target_panel._pane_role == "target"
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
    ordered_ids = [pid for row in window._layout_rows for pid in row]
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

    window._set_active_panel(target_id)
    window._set_active_panel(source_id)

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
    window._status_coordinator.refresh_storage_overview_status()

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
    window._status_coordinator.refresh_storage_overview_status()

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

    monkeypatch.setattr(window, "prompt_conflict_resolution", lambda *_a, **_k: "skip")
    assert (
        window._copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "skip"
    )
    assert existing.read_text(encoding="utf-8") == "dst"

    monkeypatch.setattr(
        window, "prompt_conflict_resolution", lambda *_a, **_k: "rename"
    )
    assert (
        window._copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "done"
    )
    assert (destination_dir / "source (1).txt").exists()

    monkeypatch.setattr(
        window, "prompt_conflict_resolution", lambda *_a, **_k: "overwrite"
    )
    source.write_text("new", encoding="utf-8")
    assert (
        window._copy_or_move_one(
            source=source, destination_dir=destination_dir, move=False
        )
        == "done"
    )
    assert existing.read_text(encoding="utf-8") == "new"

    monkeypatch.setattr(
        window, "prompt_conflict_resolution", lambda *_a, **_k: "cancel"
    )
    assert (
        window._copy_or_move_one(
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
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
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
    first_panel.tabs.setCurrentWidget(first_primary)
    first_primary.view.setColumnWidth(0, 360)
    qtbot.waitUntil(lambda: first_secondary.view.columnWidth(0) == 360)
    assert second_tab.view.columnWidth(0) == second_original


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
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window._layout_rows for pid in row]
    first_panel = window.panel_widgets[ordered_ids[0]]
    second_panel = window.panel_widgets[ordered_ids[1]]

    first_primary = first_panel.current_tab()
    first_secondary = first_panel.add_tab(first_panel.current_path())
    second_tab = second_panel.current_tab()
    assert first_primary is not None
    assert first_secondary is not None
    assert second_tab is not None

    first_secondary_original = first_secondary.view.columnWidth(0)
    second_original = second_tab.view.columnWidth(0)
    first_primary.view.setColumnWidth(0, 370)
    qtbot.wait(220)

    assert first_secondary.view.columnWidth(0) == first_secondary_original
    assert second_tab.view.columnWidth(0) == second_original


def test_column_width_auto_align_all_panels_tabs_syncs_all_open_windows(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    settings.column_width_auto_align_mode = "all_panels_tabs"
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
    controller.windows.extend([first, second])
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()

    source_panel = first.active_panel()
    assert source_panel is not None
    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    assert source_primary is not None
    assert source_secondary is not None

    target_panel = second.active_panel()
    assert target_panel is not None
    target_tab = target_panel.current_tab()
    assert target_tab is not None

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
    qtbot.addWidget(window)
    window.show()

    window.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in window._layout_rows for pid in row]
    source_panel = window.panel_widgets[ordered_ids[0]]
    other_panel = window.panel_widgets[ordered_ids[1]]

    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    other_tab = other_panel.current_tab()
    assert source_primary is not None
    assert source_secondary is not None
    assert other_tab is not None

    source_panel.tabs.setCurrentWidget(source_primary)
    source_primary.view.setColumnWidth(0, 365)
    qtbot.wait(220)
    assert source_secondary.view.columnWidth(0) != 365
    other_original = other_tab.view.columnWidth(0)

    window._set_active_panel(source_panel.panel_id)
    window.align_columns_current_panel_tabs_action.trigger()
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 365)
    assert other_tab.view.columnWidth(0) == other_original
    assert settings.column_width_auto_align_mode == "none"


def test_view_align_columns_all_panels_tabs_is_one_shot_across_windows(
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
    controller.windows.extend([first, second])
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()

    first.new_vertical_panel_action.trigger()
    ordered_ids = [pid for row in first._layout_rows for pid in row]
    source_panel = first.panel_widgets[ordered_ids[0]]
    other_panel = first.panel_widgets[ordered_ids[1]]

    source_primary = source_panel.current_tab()
    source_secondary = source_panel.add_tab(source_panel.current_path())
    other_tab = other_panel.current_tab()
    second_tab = second.active_panel().current_tab() if second.active_panel() else None
    assert source_primary is not None
    assert source_secondary is not None
    assert other_tab is not None
    assert second_tab is not None

    source_panel.tabs.setCurrentWidget(source_primary)
    source_primary.view.setColumnWidth(0, 355)
    qtbot.wait(220)
    assert source_secondary.view.columnWidth(0) != 355
    assert other_tab.view.columnWidth(0) != 355
    assert second_tab.view.columnWidth(0) != 355

    first._set_active_panel(source_panel.panel_id)
    first.align_columns_all_panels_tabs_action.trigger()
    qtbot.waitUntil(lambda: source_secondary.view.columnWidth(0) == 355)
    qtbot.waitUntil(lambda: other_tab.view.columnWidth(0) == 355)
    qtbot.waitUntil(lambda: second_tab.view.columnWidth(0) == 355)
    assert settings.column_width_auto_align_mode == "none"
