"""Resolve companion backend executables and core Windows command paths."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from ..external_file_managers import (
    DOUBLE_COMMANDER_DISCOVERY_CANDIDATES,
    TOTAL_COMMANDER_DISCOVERY_CANDIDATES,
)
from ..windows_system_paths import (
    get_comspec_path,
    get_system_root_path,
    get_windows_env_path,
)
from .types import (
    BACKEND_CMD_DELETE,
    BACKEND_EXPLORER,
    BACKEND_EXTERNAL_COPYMOVE,
    BACKEND_EXTERNAL_DELETE,
    BACKEND_POWERSHELL_DELETE,
    BACKEND_RIMRAF,
    BACKEND_ROBOCOPY,
    BACKEND_TERACOPY,
    BACKEND_UNSTOPPABLE,
    COMPANION_TOOL_NOT_FOUND,
    DEFAULT_COMSPEC_TERMINAL_EXECUTABLE,
    DEFAULT_RIMRAF_EXE,
    DEFAULT_SYSTEM_POWERSHELL5_FALLBACK,
    DEFAULT_SYSTEM_PWSH_FALLBACK,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_EXE,
    TERMINAL_LAUNCHER_COMSPEC,
    TERMINAL_LAUNCHER_POWERSHELL5,
    TERMINAL_LAUNCHER_PWSH,
    OperationExecutionPreferences,
    TerminalLauncherId,
)


def common_tool_search_dirs() -> list[Path]:
    """Return the common Windows directories searched for companion tools."""
    dirs: list[Path] = []
    env_vars = [
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramData",
        "LOCALAPPDATA",
    ]
    for env_name in env_vars:
        base = get_windows_env_path(env_name)
        if base is None:
            continue
        if base not in dirs:
            dirs.append(base)
    return dirs


def _candidate_install_roots(directory: Path, executable_name: str) -> list[Path]:
    """Return env-root-relative install directories for one executable name."""

    return [
        directory,
        directory / "TeraCopy",
        directory / "Roadkil's Unstoppable Copier",
        directory / "nodejs",
        *tool_specific_search_roots(directory, executable_name),
    ]


def candidate_executable_paths(executable_name: str) -> list[Path]:
    """Return likely filesystem candidates for the given executable name."""
    exe = str(executable_name or "").strip().strip('"')
    if not exe:
        return []
    exe_key = exe.lower()
    candidates: list[Path] = []
    which_hit = shutil.which(exe)
    if which_hit:
        candidates.append(Path(which_hit))
    raw_path = Path(exe)
    if raw_path.is_absolute():
        candidates.append(raw_path)
    for directory in common_tool_search_dirs():
        roots = _candidate_install_roots(directory, exe_key)
        for root in roots:
            candidates.append(root / exe)
    # Common Windows command wrappers for bare command names.
    if raw_path.suffix.lower() != ".cmd":
        for directory in common_tool_search_dirs():
            roots = _candidate_install_roots(directory, exe_key)
            for root in roots:
                candidates.append(root / f"{exe}.cmd")
                candidates.append(root / f"{exe}.exe")
    return candidates


def tool_specific_search_roots(directory: Path, executable_name: str) -> list[Path]:
    """Return tool-specific installation roots for one executable name."""

    exe_key = str(executable_name or "").strip().lower()
    if exe_key in {"totalcmd64.exe", "totalcmd.exe"}:
        return [
            directory / "Total Commander",
            directory / "totalcmd",
        ]
    if exe_key == "doublecmd.exe":
        return [
            directory / "Double Commander",
            directory / "doublecmd",
        ]
    return []


def resolve_if_missing(configured: str, default_name: str) -> str:
    """Resolve a configured tool path when it is unset or still defaulted."""
    configured_text = str(configured or "").strip()
    default_keys = {str(default_name).casefold(), Path(default_name).name.casefold()}
    if configured_text == COMPANION_TOOL_NOT_FOUND:
        return COMPANION_TOOL_NOT_FOUND
    if configured_text and Path(configured_text).is_absolute():
        return configured_text

    # Only auto-discover when unset or using simple default command name.
    if configured_text and configured_text.casefold() not in default_keys:
        return configured_text

    for candidate in candidate_executable_paths(default_name):
        if candidate.exists():
            return str(candidate)
    for candidate in candidate_executable_paths(configured_text or default_name):
        if candidate.exists():
            return str(candidate)
    return COMPANION_TOOL_NOT_FOUND


def resolve_if_missing_any(
    configured: str,
    default_names: tuple[str, ...],
) -> str:
    """Resolve the first available tool path from a preferred name list."""

    configured_text = str(configured or "").strip()
    default_keys = {str(name).casefold() for name in default_names}
    if configured_text == COMPANION_TOOL_NOT_FOUND:
        return COMPANION_TOOL_NOT_FOUND
    if configured_text and Path(configured_text).is_absolute():
        return configured_text
    if configured_text and configured_text.casefold() not in default_keys:
        return configured_text
    for default_name in default_names:
        resolved = resolve_if_missing(configured_text, default_name)
        if resolved != COMPANION_TOOL_NOT_FOUND:
            return resolved
    return COMPANION_TOOL_NOT_FOUND


def is_scripted_backend(backend_id: str) -> bool:
    """Return whether the backend launches through a companion command path."""
    return str(backend_id).strip().lower() in {
        BACKEND_EXPLORER,
        BACKEND_ROBOCOPY,
        BACKEND_TERACOPY,
        BACKEND_UNSTOPPABLE,
        BACKEND_EXTERNAL_COPYMOVE,
        BACKEND_CMD_DELETE,
        BACKEND_POWERSHELL_DELETE,
        BACKEND_RIMRAF,
        BACKEND_EXTERNAL_DELETE,
    }


def resolve_system_command_paths() -> tuple[str, str]:
    """Resolve the current system `cmd.exe` and `robocopy.exe` paths."""
    comspec_path = get_comspec_path()
    robocopy_path = get_system_root_path("System32", "robocopy.exe")
    resolved_cmd = str(comspec_path) if comspec_path is not None else ""
    resolved_robocopy = str(robocopy_path) if robocopy_path is not None else ""
    return resolved_cmd, resolved_robocopy


def resolve_terminal_launcher_path(
    *,
    launcher_id: TerminalLauncherId,
    configured_executable: str,
) -> str:
    """Resolve one terminal launcher executable path."""

    configured = str(configured_executable or "").strip().strip('"')
    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return _resolve_comspec_terminal_path(configured)
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return _resolve_terminal_candidate(
            configured,
            default_names=("pwsh.exe", "pwsh"),
            fallback="",
        )
    return _resolve_powershell5_terminal_path(configured)


def resolve_terminal_launcher_paths(
    *,
    comspec_executable: str,
    pwsh_executable: str,
    powershell5_executable: str,
) -> tuple[str, str, str]:
    """Resolve all terminal launcher executable paths."""

    return (
        resolve_terminal_launcher_path(
            launcher_id=TERMINAL_LAUNCHER_COMSPEC,
            configured_executable=comspec_executable,
        ),
        resolve_terminal_launcher_path(
            launcher_id=TERMINAL_LAUNCHER_PWSH,
            configured_executable=pwsh_executable,
        ),
        resolve_terminal_launcher_path(
            launcher_id=TERMINAL_LAUNCHER_POWERSHELL5,
            configured_executable=powershell5_executable,
        ),
    )


def resolve_powershell_command_paths() -> tuple[str, str]:
    """Resolve current PowerShell 7 and Windows PowerShell 5.1 paths."""

    resolved_pwsh = resolve_terminal_launcher_path(
        launcher_id=TERMINAL_LAUNCHER_PWSH,
        configured_executable="pwsh.exe",
    )
    resolved_powershell5 = resolve_terminal_launcher_path(
        launcher_id=TERMINAL_LAUNCHER_POWERSHELL5,
        configured_executable="powershell.exe",
    )
    return (
        resolved_pwsh or DEFAULT_SYSTEM_PWSH_FALLBACK,
        resolved_powershell5 or DEFAULT_SYSTEM_POWERSHELL5_FALLBACK,
    )


def resolve_companion_tool_paths(
    preferences: OperationExecutionPreferences,
) -> OperationExecutionPreferences:
    """Resolve configured companion tool paths inside execution preferences."""
    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    return replace(
        preferences,
        teracopy_executable=resolve_if_missing(
            preferences.teracopy_executable,
            DEFAULT_TERA_COPY_EXE,
        ),
        unstoppable_executable=resolve_if_missing(
            preferences.unstoppable_executable,
            DEFAULT_UNSTOPPABLE_EXE,
        ),
        rimraf_executable=resolve_if_missing(
            preferences.rimraf_executable,
            DEFAULT_RIMRAF_EXE,
        ),
        resolved_cmd_path=resolved_cmd,
        resolved_robocopy_path=resolved_robocopy,
    )


def discover_single_companion_tool(
    *,
    configured: str,
    default_executable: str,
) -> str:
    """Resolve one configured companion tool path by itself."""
    return resolve_if_missing(configured, default_executable)


def discover_preferred_companion_tool(
    *,
    configured: str,
    default_executables: tuple[str, ...],
) -> str:
    """Resolve the first available executable from a preferred candidate list."""

    return resolve_if_missing_any(configured, default_executables)


def resolve_external_file_manager_paths(
    *,
    total_commander_executable: str,
    double_commander_executable: str,
) -> tuple[str, str]:
    """Resolve Total Commander and Double Commander tool paths."""

    return (
        resolve_if_missing_any(
            total_commander_executable,
            TOTAL_COMMANDER_DISCOVERY_CANDIDATES,
        ),
        resolve_if_missing_any(
            double_commander_executable,
            DOUBLE_COMMANDER_DISCOVERY_CANDIDATES,
        ),
    )


def _resolve_comspec_terminal_path(configured_executable: str) -> str:
    """Resolve `%ComSpec%` first, then fall back to `cmd.exe` discovery."""

    configured = str(configured_executable or "").strip()
    if Path(configured).is_absolute():
        candidate = Path(configured)
        return str(candidate) if candidate.exists() else ""
    if configured.casefold() not in {
        "",
        DEFAULT_COMSPEC_TERMINAL_EXECUTABLE.casefold(),
        "cmd.exe",
        "cmd",
    }:
        return _resolve_terminal_candidate(configured, default_names=(), fallback="")
    comspec_path = get_comspec_path()
    if comspec_path is not None and comspec_path.exists():
        return str(comspec_path)
    return _resolve_terminal_candidate("cmd.exe", default_names=(), fallback="")


def _resolve_powershell5_terminal_path(configured_executable: str) -> str:
    """Resolve Windows PowerShell 5.1 using system paths and PATH lookup."""

    configured = str(configured_executable or "").strip()
    system_path = get_system_root_path(
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    default_names = ("powershell.exe", "powershell")
    default_name_set = {name.casefold() for name in default_names}
    if (
        (not configured or configured.casefold() in default_name_set)
        and system_path is not None
        and system_path.exists()
    ):
        return str(system_path)
    return _resolve_terminal_candidate(
        configured,
        default_names=default_names,
        fallback="",
    )


def _resolve_terminal_candidate(
    configured_executable: str,
    *,
    default_names: tuple[str, ...],
    fallback: str,
) -> str:
    """Resolve one terminal executable path from explicit or default names."""

    configured = str(configured_executable or "").strip().strip('"')
    if Path(configured).is_absolute():
        candidate = Path(configured)
        return str(candidate) if candidate.exists() else fallback
    names = (configured,) if configured else ()
    names = names + tuple(
        name for name in default_names if name.casefold() != configured.casefold()
    )
    for name in names:
        resolved = _first_existing_candidate(name)
        if resolved:
            return resolved
    return fallback


def _first_existing_candidate(executable_name: str) -> str:
    """Return the first existing candidate path for one executable name."""

    for candidate in candidate_executable_paths(executable_name):
        if candidate.exists():
            return str(candidate)
    return ""
