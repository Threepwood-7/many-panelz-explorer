import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer.widget_map_snapshot import generate_widget_map_image


def test_generate_widget_map_image_writes_png(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")
    output = tmp_path / "widget-map.png"

    generated = generate_widget_map_image(output, source_root=root, size=(900, 560))
    _ = qtbot

    assert generated == output
    assert output.exists()
    assert output.stat().st_size > 0
