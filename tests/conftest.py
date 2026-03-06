import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _isolate_runtime_dirs(monkeypatch, tmp_path: Path):
    config_root = tmp_path / "qsettings"
    data_root = tmp_path / "data"
    config_root.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("CONFIG_DIR", str(config_root))
    monkeypatch.setenv("DATA_DIR", str(data_root))

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(config_root))


class _FixtureController:
    def close_window(self, _window) -> None:
        return


@pytest.fixture
def window(qtbot, tmp_path: Path):
    from many_panelz_explorer.settings import SettingsManager
    from many_panelz_explorer.window import ExplorerWindow

    settings = SettingsManager()
    win = ExplorerWindow(controller=_FixtureController(), settings=settings, window_id="test-window")
    qtbot.addWidget(win)
    win.show()
    return win
