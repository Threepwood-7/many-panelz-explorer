from __future__ import annotations

from pathlib import Path

from many_panelz_explorer._operations.discovery import (
    common_tool_search_dirs,
    resolve_companion_tool_paths,
    resolve_system_command_paths,
)
from many_panelz_explorer._operations.types import (
    COMPANION_TOOL_NOT_FOUND,
    DEFAULT_SYSTEM_CMD_FALLBACK,
    DEFAULT_SYSTEM_ROBOCOPY_FALLBACK,
    DEFAULT_RIMRAF_EXE,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_EXE,
    OperationExecutionPreferences,
)


def test_companion_resolution_uses_common_locations(monkeypatch, tmp_path: Path) -> None:
    program_files = tmp_path / "ProgramFiles"
    teracopy_path = program_files / "TeraCopy" / DEFAULT_TERA_COPY_EXE
    unstoppable_path = (
        program_files
        / "Roadkil's Unstoppable Copier"
        / DEFAULT_UNSTOPPABLE_EXE
    )
    rimraf_path = program_files / "nodejs" / f"{DEFAULT_RIMRAF_EXE}.cmd"
    teracopy_path.parent.mkdir(parents=True, exist_ok=True)
    unstoppable_path.parent.mkdir(parents=True, exist_ok=True)
    rimraf_path.parent.mkdir(parents=True, exist_ok=True)
    teracopy_path.write_text("", encoding="utf-8")
    unstoppable_path.write_text("", encoding="utf-8")
    rimraf_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.setenv("ProgramFiles(x86)", "")
    monkeypatch.setenv("LOCALAPPDATA", "")
    monkeypatch.setenv("APPDATA", "")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(
        "many_panelz_explorer._operations.discovery.common_tool_search_dirs",
        lambda: [program_files],
    )

    resolved = resolve_companion_tool_paths(OperationExecutionPreferences())
    assert resolved.teracopy_executable == str(teracopy_path)
    assert resolved.unstoppable_executable == str(unstoppable_path)
    assert resolved.rimraf_executable == str(rimraf_path)


def test_companion_resolution_sets_placeholder_when_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "missing"))
    monkeypatch.setenv("ProgramFiles(x86)", "")
    monkeypatch.setenv("LOCALAPPDATA", "")
    monkeypatch.setenv("APPDATA", "")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(
        "many_panelz_explorer._operations.discovery.common_tool_search_dirs",
        lambda: [tmp_path / "missing"],
    )

    resolved = resolve_companion_tool_paths(OperationExecutionPreferences())
    assert resolved.teracopy_executable == COMPANION_TOOL_NOT_FOUND
    assert resolved.unstoppable_executable == COMPANION_TOOL_NOT_FOUND
    assert resolved.rimraf_executable == COMPANION_TOOL_NOT_FOUND


def test_companion_resolution_keeps_user_defined_custom_path() -> None:
    resolved = resolve_companion_tool_paths(
        OperationExecutionPreferences(
            teracopy_executable=r"D:\tools\my-teracopy.exe",
            unstoppable_executable=r"D:\tools\my-unstoppable.exe",
            rimraf_executable=r"D:\tools\rimraf.cmd",
        )
    )
    assert resolved.teracopy_executable == r"D:\tools\my-teracopy.exe"
    assert resolved.unstoppable_executable == r"D:\tools\my-unstoppable.exe"
    assert resolved.rimraf_executable == r"D:\tools\rimraf.cmd"


def test_resolve_system_command_paths_uses_comspec_and_windir(
    monkeypatch, tmp_path: Path
) -> None:
    cmd_path = tmp_path / "cmd.exe"
    windir = tmp_path / "Windows"
    robocopy_path = windir / "System32" / "robocopy.exe"
    cmd_path.write_text("", encoding="utf-8")
    robocopy_path.parent.mkdir(parents=True, exist_ok=True)
    robocopy_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("ComSpec", str(cmd_path))
    monkeypatch.setenv("WINDIR", str(windir))

    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    assert resolved_cmd == str(cmd_path)
    assert resolved_robocopy == str(robocopy_path)


def test_resolve_system_command_paths_has_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("ComSpec", "")
    monkeypatch.setenv("WINDIR", "")
    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    assert resolved_cmd == DEFAULT_SYSTEM_CMD_FALLBACK
    assert resolved_robocopy == DEFAULT_SYSTEM_ROBOCOPY_FALLBACK


def test_common_tool_search_dirs_starts_with_windows_bin() -> None:
    dirs = common_tool_search_dirs()

    assert dirs[0] == Path(r"C:\bin")
