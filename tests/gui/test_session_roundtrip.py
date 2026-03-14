import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

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


def test_session_roundtrip(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)

    source = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="w1",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(source)
    source.show()
    qtbot.waitUntil(source.isMaximized)

    source.panels_coordinator.new_tab_in_active_panel()
    source.panels_coordinator.split_active_panel(1)
    source.set_on_top(True)
    source.persistence_coordinator.save_to_settings()

    restored_settings = SettingsManager()
    restored = ExplorerWindow(
        controller=_ControllerStub(),
        settings=restored_settings,
        window_id="w1",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(restored)
    restored.persistence_coordinator.restore_from_settings()
    restored.show()

    assert len(restored.panel_widgets) == 4
    assert restored.on_top_action.isChecked() is True
    qtbot.waitUntil(restored.isMaximized)

    tab_counts = sorted(panel.tab_count() for panel in restored.panel_widgets.values())
    assert tab_counts == [1, 1, 1, 2]


def test_session_restore_normal_geometry_overrides_default_maximized(
    qtbot, tmp_path: Path
) -> None:
    settings = SettingsManager()
    roots_provider = _test_roots_provider(tmp_path)

    source = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="w-normal",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(source)
    source.show()
    qtbot.waitUntil(source.isMaximized)
    source.showNormal()
    qtbot.waitUntil(lambda: not source.isMaximized())
    source.resize(910, 620)
    source.persistence_coordinator.save_to_settings()

    restored_settings = SettingsManager()
    restored = ExplorerWindow(
        controller=_ControllerStub(),
        settings=restored_settings,
        window_id="w-normal",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(restored)
    restored.persistence_coordinator.restore_from_settings()
    restored.show()

    qtbot.waitUntil(lambda: restored.isVisible() and not restored.isMaximized())
