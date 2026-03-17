from __future__ import annotations

from typing import TYPE_CHECKING

from many_panelz_explorer._operations.discovery import (
    common_tool_search_dirs,
    resolve_companion_tool_paths,
    resolve_external_file_manager_paths,
    resolve_powershell_command_paths,
    resolve_system_command_paths,
    resolve_terminal_launcher_paths,
)
from many_panelz_explorer._operations.types import (
    COMPANION_TOOL_NOT_FOUND,
    DEFAULT_RIMRAF_EXE,
    DEFAULT_SYSTEM_CMD_FALLBACK,
    DEFAULT_SYSTEM_POWERSHELL5_FALLBACK,
    DEFAULT_SYSTEM_PWSH_FALLBACK,
    DEFAULT_SYSTEM_ROBOCOPY_FALLBACK,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_EXE,
    OperationExecutionPreferences,
)
from many_panelz_explorer.external_file_managers import (
    DEFAULT_DOUBLE_COMMANDER_EXECUTABLE,
    TOTAL_COMMANDER_DISCOVERY_CANDIDATES,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_companion_resolution_uses_common_locations(
    monkeypatch, tmp_path: Path
) -> None:
    program_files = tmp_path / "ProgramFiles"
    teracopy_path = program_files / "TeraCopy" / DEFAULT_TERA_COPY_EXE
    unstoppable_path = (
        program_files / "Roadkil's Unstoppable Copier" / DEFAULT_UNSTOPPABLE_EXE
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
    monkeypatch.setenv("ProgramData", "")
    monkeypatch.setenv("LOCALAPPDATA", "")
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
    monkeypatch.setenv("ProgramData", "")
    monkeypatch.setenv("LOCALAPPDATA", "")
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


def test_resolve_system_command_paths_uses_comspec_and_systemroot(
    monkeypatch, tmp_path: Path
) -> None:
    cmd_path = tmp_path / "cmd.exe"
    system_root = tmp_path / "Windows"
    robocopy_path = system_root / "System32" / "robocopy.exe"
    cmd_path.write_text("", encoding="utf-8")
    robocopy_path.parent.mkdir(parents=True, exist_ok=True)
    robocopy_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("ComSpec", str(cmd_path))
    monkeypatch.setenv("SYSTEMROOT", str(system_root))

    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    assert resolved_cmd == str(cmd_path)
    assert resolved_robocopy == str(robocopy_path)


def test_resolve_system_command_paths_returns_empty_when_env_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ComSpec", "")
    monkeypatch.setenv("SYSTEMROOT", "")
    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    assert resolved_cmd == DEFAULT_SYSTEM_CMD_FALLBACK
    assert resolved_robocopy == DEFAULT_SYSTEM_ROBOCOPY_FALLBACK


def test_resolve_terminal_launcher_paths_uses_comspec_env_and_pwsh_path(
    monkeypatch, tmp_path: Path
) -> None:
    cmd_path = tmp_path / "cmd.exe"
    pwsh_path = tmp_path / "pwsh.exe"
    powershell5_path = (
        tmp_path
        / "Windows"
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    cmd_path.write_text("", encoding="utf-8")
    pwsh_path.write_text("", encoding="utf-8")
    powershell5_path.parent.mkdir(parents=True, exist_ok=True)
    powershell5_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("ComSpec", str(cmd_path))
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "Windows"))
    monkeypatch.setenv("PATH", str(tmp_path))

    resolved_comspec, resolved_pwsh, resolved_powershell5 = (
        resolve_terminal_launcher_paths(
            comspec_executable="%ComSpec%",
            pwsh_executable="pwsh.exe",
            powershell5_executable="powershell.exe",
        )
    )

    assert resolved_comspec == str(cmd_path)
    assert resolved_pwsh == str(pwsh_path)
    assert resolved_powershell5 == str(powershell5_path)


def test_resolve_powershell_command_paths_returns_empty_when_missing(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SYSTEMROOT", "")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(
        "many_panelz_explorer._operations.discovery.common_tool_search_dirs",
        lambda: [],
    )

    resolved_pwsh, resolved_powershell5 = resolve_powershell_command_paths()

    assert resolved_pwsh == DEFAULT_SYSTEM_PWSH_FALLBACK
    assert resolved_powershell5 == DEFAULT_SYSTEM_POWERSHELL5_FALLBACK


def test_common_tool_search_dirs_uses_only_allowed_env_roots(
    monkeypatch, tmp_path: Path
) -> None:
    program_files = tmp_path / "ProgramFiles"
    program_files_x86 = tmp_path / "ProgramFilesX86"
    program_data = tmp_path / "ProgramData"
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.setenv("ProgramFiles(x86)", str(program_files_x86))
    monkeypatch.setenv("ProgramData", str(program_data))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    dirs = common_tool_search_dirs()

    assert dirs == [
        program_files,
        program_files_x86,
        program_data,
        local_app_data,
    ]


def test_external_file_manager_resolution_uses_common_locations(
    monkeypatch, tmp_path: Path
) -> None:
    program_files = tmp_path / "ProgramFiles"
    total_commander_path = (
        program_files / "totalcmd" / TOTAL_COMMANDER_DISCOVERY_CANDIDATES[0]
    )
    double_commander_path = (
        program_files / "Double Commander" / DEFAULT_DOUBLE_COMMANDER_EXECUTABLE
    )
    total_commander_path.parent.mkdir(parents=True, exist_ok=True)
    double_commander_path.parent.mkdir(parents=True, exist_ok=True)
    total_commander_path.write_text("", encoding="utf-8")
    double_commander_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.setenv("ProgramFiles(x86)", "")
    monkeypatch.setenv("ProgramData", "")
    monkeypatch.setenv("LOCALAPPDATA", "")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(
        "many_panelz_explorer._operations.discovery.common_tool_search_dirs",
        lambda: [program_files],
    )

    resolved_total_commander, resolved_double_commander = (
        resolve_external_file_manager_paths(
            total_commander_executable=TOTAL_COMMANDER_DISCOVERY_CANDIDATES[0],
            double_commander_executable=DEFAULT_DOUBLE_COMMANDER_EXECUTABLE,
        )
    )
    assert resolved_total_commander == str(total_commander_path)
    assert resolved_double_commander == str(double_commander_path)
