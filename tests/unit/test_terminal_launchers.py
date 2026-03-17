from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from many_panelz_explorer import file_ops
from many_panelz_explorer.terminal_launchers import (
    TerminalLauncherSettings,
    build_windows_terminal_launch_argv,
    configure_terminal_launchers,
    current_terminal_launcher_settings,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def restore_terminal_settings() -> None:
    original = current_terminal_launcher_settings()
    try:
        yield
    finally:
        configure_terminal_launchers(original)


def test_build_windows_terminal_launch_argv_opens_comspec_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cmd_path = tmp_path / "cmd.exe"
    cmd_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("ComSpec", str(cmd_path))

    argv = build_windows_terminal_launch_argv(
        target_folder=tmp_path,
        launcher_id="comspec",
    )

    assert argv == [str(cmd_path), "/K", "cd", "/d", f'"{tmp_path}"']


def test_build_windows_terminal_launch_argv_runs_pwsh_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pwsh_path = tmp_path / "pwsh.exe"
    pwsh_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path))

    argv = build_windows_terminal_launch_argv(
        target_folder=tmp_path,
        launcher_id="pwsh",
        command="pytest -q",
    )

    assert argv == [
        str(pwsh_path),
        "-NoExit",
        "-Command",
        f"Set-Location -LiteralPath '{tmp_path}'; pytest -q",
    ]


def test_build_windows_terminal_launch_argv_activates_python_project_for_powershell5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    powershell5_path = (
        tmp_path
        / "Windows"
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    activate_path = tmp_path / ".venv" / "Scripts" / "Activate.ps1"
    powershell5_path.parent.mkdir(parents=True, exist_ok=True)
    activate_path.parent.mkdir(parents=True, exist_ok=True)
    powershell5_path.write_text("", encoding="utf-8")
    activate_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "Windows"))

    argv = build_windows_terminal_launch_argv(
        target_folder=tmp_path,
        launcher_id="powershell5",
        command="python -m many_panelz_explorer",
        python_project=True,
    )

    assert argv == [
        str(powershell5_path),
        "-NoExit",
        "-Command",
        (
            f"Set-Location -LiteralPath '{tmp_path}'; "
            f". '{activate_path}'; python -m many_panelz_explorer"
        ),
    ]


def test_open_terminal_here_uses_configured_default_launcher(
    monkeypatch: pytest.MonkeyPatch,
    restore_terminal_settings: None,
    tmp_path: Path,
) -> None:
    powershell5_path = (
        tmp_path
        / "Windows"
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    powershell5_path.parent.mkdir(parents=True, exist_ok=True)
    powershell5_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "Windows"))
    recorded: list[list[str]] = []
    monkeypatch.setattr(
        "many_panelz_explorer.terminal_launchers.subprocess.Popen",
        lambda args: recorded.append(list(args)),
    )
    configure_terminal_launchers(
        TerminalLauncherSettings(default_terminal_launcher="powershell5")
    )

    file_ops.open_terminal_here(tmp_path)

    assert recorded == [
        [
            str(powershell5_path),
            "-NoExit",
            "-Command",
            "Set-Location",
            "-LiteralPath",
            f"'{tmp_path}'",
        ]
    ]
