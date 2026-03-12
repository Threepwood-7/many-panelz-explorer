import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer._operations.queue_manager import OperationQueueManager
from many_panelz_explorer._operations.types import OperationExecutionPreferences
from many_panelz_explorer.operation_queue_widgets import (
    OperationQueuePanel,
    OperationQueueTableModel,
)


def _new_panel(qtbot) -> OperationQueuePanel:
    manager = OperationQueueManager(preferences=OperationExecutionPreferences())
    model = OperationQueueTableModel(manager)
    panel = OperationQueuePanel(manager=manager, model=model)
    qtbot.addWidget(panel)
    panel.show()
    return panel


def test_open_script_uses_text_editor_api(qtbot, monkeypatch, tmp_path: Path) -> None:
    panel = _new_panel(qtbot)
    script_path = tmp_path / "run.cmd"
    script_path.write_text("@echo off\n", encoding="utf-8")

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "many_panelz_explorer.operation_queue_widgets.file_ops.open_in_text_editor",
        lambda path, editor_executable="": calls.append((str(path), editor_executable)),
    )
    monkeypatch.setattr(
        "many_panelz_explorer.operation_queue_widgets.file_ops.open_with_default",
        lambda _path: (_ for _ in ()).throw(AssertionError("must not be called")),
    )
    monkeypatch.setattr(
        panel, "_artifact_path", lambda kind: script_path if kind == "script" else None
    )

    panel._open_script()

    assert calls == [(str(script_path), "")]


def test_open_log_and_metadata_use_default_opener(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    panel = _new_panel(qtbot)
    log_path = tmp_path / "output.log"
    metadata_path = tmp_path / "job.json"
    log_path.write_text("ok\n", encoding="utf-8")
    metadata_path.write_text("{}\n", encoding="utf-8")

    opened: list[str] = []
    monkeypatch.setattr(
        "many_panelz_explorer.operation_queue_widgets.file_ops.open_with_default",
        lambda path: opened.append(str(path)),
    )
    monkeypatch.setattr(
        panel,
        "_artifact_path",
        lambda kind: (
            log_path
            if kind == "log"
            else (metadata_path if kind == "metadata" else None)
        ),
    )

    panel._open_log()
    panel._open_metadata()

    assert opened == [str(log_path), str(metadata_path)]


def test_open_script_failure_shows_warning(qtbot, monkeypatch, tmp_path: Path) -> None:
    panel = _new_panel(qtbot)
    script_path = tmp_path / "run.cmd"
    script_path.write_text("@echo off\n", encoding="utf-8")

    monkeypatch.setattr(
        "many_panelz_explorer.operation_queue_widgets.file_ops.open_in_text_editor",
        lambda _path, editor_executable="": (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        panel, "_artifact_path", lambda kind: script_path if kind == "script" else None
    )

    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "many_panelz_explorer.operation_queue_widgets.QMessageBox.warning",
        lambda _parent, title, text: warnings.append((str(title), str(text))),
    )

    panel._open_script()

    assert warnings == [("Open Artifact Failed", "boom")]
