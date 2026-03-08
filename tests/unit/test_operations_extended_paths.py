from __future__ import annotations

import subprocess
from pathlib import Path

from many_panelz_explorer.operations import (
    OperationArtifacts,
    _expand_template,
    _run_script,
    _write_script,
    to_windows_arg_path,
)


def test_to_windows_arg_path_switches_extended_prefix(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "alpha.txt"
    source.write_text("x", encoding="utf-8")
    monkeypatch.setattr("many_panelz_explorer.operations.os.name", "nt", raising=False)

    plain = to_windows_arg_path(source, use_extended_paths=False)
    extended = to_windows_arg_path(source, use_extended_paths=True)

    assert plain.startswith("\\\\?\\") is False
    assert extended.startswith("\\\\?\\")


def test_expand_template_uses_configured_path_mode(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.txt"
    target = tmp_path / "target"
    source.write_text("x", encoding="utf-8")
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("many_panelz_explorer.operations.os.name", "nt", raising=False)

    plain = _expand_template(
        "{sources} {target}",
        kind="copy",
        sources=[source],
        target_dir=target,
        use_extended_paths=False,
    )
    extended = _expand_template(
        "{sources} {target}",
        kind="copy",
        sources=[source],
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
    script_path = _write_script(artifacts, ["echo hello"])
    raw = script_path.read_bytes()

    assert raw.startswith(b"\xef\xbb\xbf") is False
    lines = script_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "@echo off"
    assert lines[1].lower() == "chcp 65001 >nul"


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

    monkeypatch.setattr("many_panelz_explorer.operations.subprocess.Popen", _fake_popen)
    result = _run_script(
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
    assert ">>" not in args[3]
    assert kwargs.get("creationflags", 0) == int(
        getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    )
    assert "not redirected" in log_path.read_text(encoding="utf-8")
