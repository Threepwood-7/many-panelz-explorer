import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer.settings import SettingsManager
from many_panelz_explorer.window import ExplorerWindow


class _ControllerStub:
    def close_window(self, _window) -> None:
        return


def test_session_roundtrip(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()

    source = ExplorerWindow(
        controller=_ControllerStub(), settings=settings, window_id="w1"
    )
    qtbot.addWidget(source)
    source.show()

    source.new_tab_in_active_panel()
    source.split_active_panel(1)
    source.set_on_top(True)
    source.save_to_settings()

    restored_settings = SettingsManager()
    restored = ExplorerWindow(
        controller=_ControllerStub(), settings=restored_settings, window_id="w1"
    )
    qtbot.addWidget(restored)
    restored.restore_from_settings()

    assert len(restored.panel_widgets) == 2
    assert restored._on_top_action.isChecked() is True

    tab_counts = sorted(panel.tab_count() for panel in restored.panel_widgets.values())
    assert tab_counts == [1, 2]
