import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QLabel

from many_panelz_explorer.dialogs.properties_dialog import PropertiesDialog
from many_panelz_explorer.explorer_tab import ExplorerTab


def test_properties_dialog_uses_custom_size_formatter(
    qtbot, tmp_path: Path
) -> None:
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"x" * 3_500)

    dialog = PropertiesDialog(
        sample,
        size_formatter=lambda value: f"{value} B ({value / 1024:.2f} KiB)",
    )
    qtbot.addWidget(dialog)
    dialog.show()

    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert "3500 B (3.42 KiB)" in texts
    assert "Size (bytes)" not in texts


def test_explorer_tab_passes_properties_formatter_to_dialog(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"x" * 123)
    captured: dict[str, object] = {}

    class _FakePropertiesDialog:
        def __init__(self, path, parent=None, *, size_formatter=None):
            captured["path"] = path
            captured["formatter"] = size_formatter

        def exec(self) -> int:
            captured["exec_called"] = True
            return 0

    monkeypatch.setattr(
        "many_panelz_explorer._explorer_tab_actions.PropertiesDialog",
        _FakePropertiesDialog,
    )

    tab = ExplorerTab(
        initial_path=tmp_path,
        properties_size_formatter=lambda value: f"custom-{value}",
    )
    qtbot.addWidget(tab)
    tab.show()
    monkeypatch.setattr(tab, "selected_paths", lambda: [sample])
    tab._actions._show_properties()

    assert captured["path"] == sample
    formatter = captured["formatter"]
    assert callable(formatter)
    assert formatter(123) == "custom-123"
    assert captured["exec_called"] is True
