import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer.operation_queue_widgets import OperationQueueTableModel
from many_panelz_explorer.operations import (
    OperationExecutionPreferences,
    OperationQueueManager,
)
from many_panelz_explorer.settings import SettingsManager
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def __init__(self) -> None:
        self.operation_queue_manager = OperationQueueManager(
            preferences=OperationExecutionPreferences()
        )
        self.operation_queue_model = OperationQueueTableModel(self.operation_queue_manager)

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

    source.new_tab_in_active_panel()
    source.split_active_panel(1)
    source.set_on_top(True)
    source.save_to_settings()

    restored_settings = SettingsManager()
    restored = ExplorerWindow(
        controller=_ControllerStub(),
        settings=restored_settings,
        window_id="w1",
        roots_provider=roots_provider,
    )
    qtbot.addWidget(restored)
    restored.restore_from_settings()

    assert len(restored.panel_widgets) == 2
    assert restored._on_top_action.isChecked() is True

    tab_counts = sorted(panel.tab_count() for panel in restored.panel_widgets.values())
    assert tab_counts == [1, 2]
