from __future__ import annotations

import subprocess
from os import linesep
from typing import TYPE_CHECKING

from many_panelz_explorer._operations.artifacts import (
    expand_template,
    run_script,
    write_script,
    write_unstoppable_job_file,
)
from many_panelz_explorer._operations.path_helpers import (
    display_path,
    to_windows_arg_path,
)
from many_panelz_explorer._operations.types import (
    OperationArtifacts,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_to_windows_arg_path_switches_extended_prefix(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "alpha.txt"
    source.write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "nt", raising=False
    )

    plain = to_windows_arg_path(source, use_extended_paths=False)
    extended = to_windows_arg_path(source, use_extended_paths=True)

    assert plain.startswith("\\\\?\\") is False
    assert extended.startswith("\\\\?\\")


def test_to_windows_arg_path_normalizes_forward_slashes(monkeypatch) -> None:
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "nt", raising=False
    )
    plain = to_windows_arg_path(
        r"C:/tmp/multi-panelz/source.txt",
        use_extended_paths=False,
    )
    extended = to_windows_arg_path(
        r"C:/tmp/multi-panelz/source.txt",
        use_extended_paths=True,
    )
    assert "/" not in plain
    assert "/" not in extended
    assert "\\" in plain
    assert extended.startswith("\\\\?\\")


def test_display_path_normalizes_forward_slashes(monkeypatch) -> None:
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "nt", raising=False
    )
    assert (
        display_path(r"\\?\C:/tmp/multi-panelz/source.txt")
        == r"C:\tmp\multi-panelz\source.txt"
    )
    assert display_path(r"\\?\UNC\server/share/path") == r"\\server\share\path"


def test_windows_path_normalization_is_platform_specific(monkeypatch) -> None:
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "posix", raising=False
    )
    assert (
        to_windows_arg_path("C:/tmp/multi-panelz/source.txt", use_extended_paths=False)
        == "C:/tmp/multi-panelz/source.txt"
    )
    assert (
        display_path(r"\\?\C:/tmp/multi-panelz/source.txt")
        == r"\\?\C:/tmp/multi-panelz/source.txt"
    )


def test_expand_template_uses_configured_path_mode(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    target = tmp_path / "target"
    source.write_text("x", encoding="utf-8")
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "nt", raising=False
    )

    plain = expand_template(
        "{sources} {target}",
        kind="copy",
        sources=(source,),
        target_dir=target,
        use_extended_paths=False,
    )
    extended = expand_template(
        "{sources} {target}",
        kind="copy",
        sources=(source,),
        target_dir=target,
        use_extended_paths=True,
    )

    assert "\\\\?\\" not in plain
    assert "\\\\?\\" in extended


def test_write_script_uses_utf8_without_bom_and_sets_chcp_first(tmp_path: Path) -> None:
    artifacts = OperationArtifacts(
        job_dir=tmp_path,
        metadata_path=tmp_path / "job.json",
        log_path=tmp_path / "output.log",
    )
    script_path = write_script(artifacts, ["echo hello"])
    raw = script_path.read_bytes()

    assert raw.startswith(b"\xef\xbb\xbf") is False
    assert raw.decode("utf-8") == linesep.join(
        [
            "@echo off",
            "chcp 65001 >nul",
            "setlocal enableextensions",
            "echo hello",
            "exit /b %ERRORLEVEL%",
        ]
    )
    lines = script_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "@echo off"
    assert lines[1].lower() == "chcp 65001 >nul"


def test_write_unstoppable_job_file_uses_utf16le_bom_and_source_target_lines(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "nt", raising=False
    )
    source_a = tmp_path / "source-a.txt"
    source_b = tmp_path / "source-b.txt"
    target = tmp_path / "target"
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")
    target.mkdir(parents=True, exist_ok=True)
    artifacts = OperationArtifacts(
        job_dir=tmp_path,
        metadata_path=tmp_path / "job.json",
        log_path=tmp_path / "output.log",
    )

    job_path = write_unstoppable_job_file(
        artifacts,
        sources=(source_a, source_b),
        target_dir=target,
        use_extended_paths=False,
    )

    raw = job_path.read_bytes()
    assert raw.startswith(b"\xff\xfe")
    assert raw.decode("utf-16") == linesep.join(
        [
            f"{source_a}|{target}",
            f"{source_b}|{target}",
            "",
        ]
    )


def test_write_unstoppable_job_file_uses_extended_paths_when_enabled(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "many_panelz_explorer._operations.path_helpers.os.name", "nt", raising=False
    )
    source = tmp_path / "source.txt"
    target = tmp_path / "target"
    source.write_text("x", encoding="utf-8")
    target.mkdir(parents=True, exist_ok=True)
    artifacts = OperationArtifacts(
        job_dir=tmp_path,
        metadata_path=tmp_path / "job.json",
        log_path=tmp_path / "output.log",
    )

    job_path = write_unstoppable_job_file(
        artifacts,
        sources=(source,),
        target_dir=target,
        use_extended_paths=True,
    )

    text = job_path.read_bytes().decode("utf-16")
    assert text.startswith("\\\\?\\")
    assert "|" in text


def test_run_script_does_not_redirect_companion_output(
    monkeypatch, tmp_path: Path
) -> None:
    cmd_exe = tmp_path / "cmd.exe"
    cmd_exe.write_text("", encoding="utf-8")
    script_path = tmp_path / "run.cmd"
    script_path.write_text("@echo off\nexit /b 0\n", encoding="utf-8")
    log_path = tmp_path / "output.log"
    captured: dict[str, object] = {}

    class _FakeProcess:
        pid = 4242

        def wait(self) -> int:
            return 0

    def _fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr(
        "many_panelz_explorer._operations.artifacts.subprocess.Popen", _fake_popen
    )
    result = run_script(
        script_path,
        log_path,
        cmd_path=str(cmd_exe),
        wait=True,
    )

    args = captured["args"]
    kwargs = captured["kwargs"]
    assert result.status == "succeeded"
    assert args[0] == str(cmd_exe)
    assert args[1] == "/d"
    assert args[2] == "/c"
    assert args[3] == str(script_path)
    assert ">>" not in args[3]
    assert kwargs.get("creationflags", 0) == int(
        getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    )
    assert "not redirected" in log_path.read_text(encoding="utf-8")
