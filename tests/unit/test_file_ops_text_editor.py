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
    system_root = tmp_path / "Windows"
    notepad = system_root / "System32" / "notepad.exe"
    notepad.parent.mkdir(parents=True, exist_ok=True)
    notepad.write_text("", encoding="utf-8")

    monkeypatch.setattr(file_ops.os, "name", "nt", raising=False)
    monkeypatch.setenv("SYSTEMROOT", str(system_root))
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
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "missing"))

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


def test_open_with_viewer_uses_dedicated_viewer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    viewer = tmp_path / "viewer.exe"
    viewer.write_text("", encoding="utf-8")
    sample = tmp_path / "sample.txt"
    sample.write_text("demo", encoding="utf-8")
    file_ops.configure_open_routing(
        default_editor_executable="",
        default_viewer_executable=str(viewer),
        overrides_json="{}",
    )
    launched: list[list[str]] = []
    monkeypatch.setattr(
        file_ops.subprocess, "Popen", lambda args: launched.append(list(args))
    )

    used_viewer = file_ops.open_with_viewer(sample)

    assert used_viewer is True
    assert launched == [[str(viewer), str(sample)]]


def test_create_text_file_creates_requested_file(tmp_path: Path) -> None:
    created = file_ops.create_text_file(tmp_path, "notes.txt")

    assert created == tmp_path / "notes.txt"
    assert created.exists() is True
    assert created.read_text(encoding="utf-8") == ""


def test_create_text_file_raises_on_existing_file(tmp_path: Path) -> None:
    existing = tmp_path / "notes.txt"
    existing.write_text("present", encoding="utf-8")

    with pytest.raises(FileExistsError):
        file_ops.create_text_file(tmp_path, "notes.txt")
