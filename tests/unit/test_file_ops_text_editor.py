from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from many_panelz_explorer import file_ops

if TYPE_CHECKING:
    from pathlib import Path


def test_open_in_text_editor_uses_configured_editor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file_ops.configure_open_routing(
        default_editor_executable="",
        default_viewer_executable="",
        overrides_json="{}",
    )
    editor = tmp_path / "editor.exe"
    script = tmp_path / "run.cmd"
    editor.write_text("", encoding="utf-8")
    script.write_text("@echo off\n", encoding="utf-8")

    launched: list[list[str]] = []
    monkeypatch.setattr(
        file_ops.subprocess, "Popen", lambda args: launched.append(list(args))
    )

    file_ops.open_in_text_editor(script, editor_executable=str(editor))

    assert launched == [[str(editor), str(script)]]


def test_open_in_text_editor_falls_back_to_notepad_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file_ops.configure_open_routing(
        default_editor_executable="",
        default_viewer_executable="",
        overrides_json="{}",
    )
    script = tmp_path / "run.cmd"
    script.write_text("@echo off\n", encoding="utf-8")
    windir = tmp_path / "Windows"
    notepad = windir / "System32" / "notepad.exe"
    notepad.parent.mkdir(parents=True, exist_ok=True)
    notepad.write_text("", encoding="utf-8")

    monkeypatch.setattr(file_ops.os, "name", "nt", raising=False)
    monkeypatch.setenv("WINDIR", str(windir))
    launched: list[list[str]] = []
    monkeypatch.setattr(
        file_ops.subprocess, "Popen", lambda args: launched.append(list(args))
    )

    file_ops.open_in_text_editor(script, editor_executable="")

    assert launched == [[str(notepad), str(script)]]


def test_open_in_text_editor_raises_when_editor_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file_ops.configure_open_routing(
        default_editor_executable="",
        default_viewer_executable="",
        overrides_json="{}",
    )
    script = tmp_path / "run.cmd"
    script.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(file_ops.os, "name", "nt", raising=False)
    monkeypatch.setenv("WINDIR", str(tmp_path / "missing"))
    monkeypatch.setattr(file_ops.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="No text editor available"):
        file_ops.open_in_text_editor(script, editor_executable="")


def test_resolve_open_executable_view_falls_back_to_editor(tmp_path: Path) -> None:
    editor = tmp_path / "editor.exe"
    editor.write_text("", encoding="utf-8")
    file_ops.configure_open_routing(
        default_editor_executable=str(editor),
        default_viewer_executable="",
        overrides_json="{}",
    )
    resolved = file_ops.resolve_open_executable(tmp_path / "sample.log", "view")
    assert resolved == str(editor)


def test_resolve_open_executable_uses_extension_override(tmp_path: Path) -> None:
    editor = tmp_path / "editor.exe"
    viewer = tmp_path / "viewer.exe"
    editor.write_text("", encoding="utf-8")
    viewer.write_text("", encoding="utf-8")
    file_ops.configure_open_routing(
        default_editor_executable=str(editor),
        default_viewer_executable=str(viewer),
        overrides_json="{}",
    )
    special = tmp_path / "special_editor.exe"
    special.write_text("", encoding="utf-8")
    payload = {".cmd": {"editor": str(special), "viewer": ""}}
    file_ops.configure_open_routing(
        default_editor_executable=str(editor),
        default_viewer_executable=str(viewer),
        overrides_json=json.dumps(payload),
    )
    resolved = file_ops.resolve_open_executable(tmp_path / "run.cmd", "edit")
    assert resolved == str(special)
