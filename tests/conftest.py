import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _FixtureController:
    def close_window(self, _window) -> None:
        return


@pytest.fixture
def window(qtbot, tmp_path: Path):
    from many_panelz_explorer.settings import SettingsManager
    from many_panelz_explorer.window import ExplorerWindow

    settings = SettingsManager(settings_path=tmp_path / "settings.ini")
    win = ExplorerWindow(controller=_FixtureController(), settings=settings, window_id="test-window")
    qtbot.addWidget(win)
    win.show()
    return win
