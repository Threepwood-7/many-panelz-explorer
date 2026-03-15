"""Windows environment path helpers for system-owned executables."""

from __future__ import annotations

import os
from pathlib import Path


def get_windows_env_text(name: str) -> str:
    """Return one Windows environment variable with case-insensitive lookup."""

    wanted = str(name or "").strip().casefold()
    if not wanted:
        return ""
    for env_name, value in os.environ.items():
        if env_name.casefold() == wanted:
            return str(value or "").strip()
    return ""


def get_windows_env_path(name: str) -> Path | None:
    """Return one Windows environment path when it is configured."""

    raw = get_windows_env_text(name)
    if not raw:
        return None
    return Path(raw)


def get_system_root_path(*parts: str) -> Path | None:
    """Return one path beneath `%SYSTEMROOT%` when that root exists."""

    system_root = get_windows_env_path("SYSTEMROOT")
    if system_root is None:
        return None
    candidate = system_root.joinpath(*parts)
    if candidate.exists():
        return candidate
    return None


def get_comspec_path() -> Path | None:
    """Return `%ComSpec%` when it is configured."""

    return get_windows_env_path("ComSpec")
