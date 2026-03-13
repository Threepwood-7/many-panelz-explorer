"""Resolve companion backend executables and core Windows command paths."""

from __future__ import annotations

import os
import shutil
from dataclasses import replace
from pathlib import Path

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
    DEFAULT_RIMRAF_EXE,
    DEFAULT_SYSTEM_CMD_FALLBACK,
    DEFAULT_SYSTEM_ROBOCOPY_FALLBACK,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_EXE,
    OperationExecutionPreferences,
)


def common_tool_search_dirs() -> list[Path]:
    """Return the common Windows directories searched for companion tools."""
    dirs: list[Path] = [Path(r"C:\bin")]
    env_vars = [
        "ProgramFiles",
        "ProgramFiles(x86)",
        "LOCALAPPDATA",
        "APPDATA",
    ]
    for env_name in env_vars:
        raw = os.environ.get(env_name, "").strip()
        if not raw:
            continue
        base = Path(raw)
        dirs.append(base)
        dirs.append(base / "Programs")
        dirs.append(base / "Tools")
        dirs.append(base / "Utilities")
        dirs.append(base / "npm")
    return dirs


def candidate_executable_paths(executable_name: str) -> list[Path]:
    """Return likely filesystem candidates for the given executable name."""
    exe = str(executable_name or "").strip().strip('"')
    if not exe:
        return []
    candidates: list[Path] = []
    which_hit = shutil.which(exe)
    if which_hit:
        candidates.append(Path(which_hit))
    raw_path = Path(exe)
    if raw_path.is_absolute():
        candidates.append(raw_path)
    for directory in common_tool_search_dirs():
        # Typical Windows companion install subdirectories.
        roots = [
            directory,
            directory / "TeraCopy",
            directory / "Roadkil's Unstoppable Copier",
            directory / "nodejs",
        ]
        for root in roots:
            candidates.append(root / exe)
    # Common Windows command wrappers for bare command names.
    if raw_path.suffix.lower() != ".cmd":
        for directory in common_tool_search_dirs():
            roots = [
                directory,
                directory / "TeraCopy",
                directory / "Roadkil's Unstoppable Copier",
                directory / "nodejs",
            ]
            for root in roots:
                candidates.append(root / f"{exe}.cmd")
                candidates.append(root / f"{exe}.exe")
    return candidates


def resolve_if_missing(configured: str, default_name: str) -> str:
    """Resolve a configured tool path when it is unset or still defaulted."""
    configured_text = str(configured or "").strip()
    if configured_text == COMPANION_TOOL_NOT_FOUND:
        return COMPANION_TOOL_NOT_FOUND
    if configured_text and Path(configured_text).is_absolute():
        return configured_text

    # Only auto-discover when unset or using simple default command name.
    if configured_text and configured_text not in {
        default_name,
        Path(default_name).name,
    }:
        return configured_text

    for candidate in candidate_executable_paths(default_name):
        if candidate.exists():
            return str(candidate)
    for candidate in candidate_executable_paths(configured_text or default_name):
        if candidate.exists():
            return str(candidate)
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
    comspec_raw = str(os.environ.get("COMSPEC", "")).strip()
    windir_raw = str(os.environ.get("WINDIR", r"C:\Windows")).strip() or r"C:\Windows"
    cmd_candidates: list[Path] = []
    robocopy_candidates: list[Path] = []
    if comspec_raw:
        cmd_candidates.append(Path(comspec_raw))
    cmd_candidates.append(Path(windir_raw) / "System32" / "cmd.exe")
    cmd_candidates.append(Path(DEFAULT_SYSTEM_CMD_FALLBACK))
    robocopy_candidates.append(Path(windir_raw) / "System32" / "robocopy.exe")
    robocopy_candidates.append(Path(DEFAULT_SYSTEM_ROBOCOPY_FALLBACK))

    resolved_cmd = next(
        (str(candidate) for candidate in cmd_candidates if candidate.exists()),
        str(cmd_candidates[0]),
    )
    resolved_robocopy = next(
        (str(candidate) for candidate in robocopy_candidates if candidate.exists()),
        str(robocopy_candidates[0]),
    )
    return resolved_cmd, resolved_robocopy


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
