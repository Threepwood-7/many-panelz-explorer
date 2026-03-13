"""Tests for centralized runtime text output helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from many_panelz_explorer import runtime_text

if TYPE_CHECKING:
    from pathlib import Path


def test_write_runtime_lines_uses_centralized_linesep_for_cmd(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runtime_text.os, "linesep", "\n\n")
    path = tmp_path / "run.cmd"

    runtime_text.write_runtime_lines(path, ["@echo off", "echo hello"])

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") is False
    assert raw.decode("utf-8") == "@echo off\n\necho hello"


def test_write_runtime_text_normalizes_mixed_newlines_for_txt(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runtime_text.os, "linesep", "<NL>")
    path = tmp_path / "sample.txt"

    runtime_text.write_runtime_text(path, "alpha\r\nbeta\ngamma\r")

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") is False
    assert raw.decode("utf-8") == "alpha<NL>beta<NL>gamma<NL>"


def test_write_runtime_lines_keeps_utf16_for_ucb(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runtime_text.os, "linesep", "<ROW>")
    path = tmp_path / "job.ucb"

    runtime_text.write_runtime_lines(path, ["one", "two"], trailing_newline=True)

    raw = path.read_bytes()
    assert raw.startswith(b"\xff\xfe")
    assert raw.decode("utf-16") == "one<ROW>two<ROW>"
