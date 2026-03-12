from __future__ import annotations

import os
import shutil
from pathlib import Path

from threep_commons.fs_paths import (
    coerce_path,
    normalize_windows_path_text,
    strip_windows_long_path_text,
)
from .types import OperationRequest


def normalize_path(path: Path | str) -> Path:
    if os.name != "nt":
        return Path(path).expanduser()
    return coerce_path(path)


def to_windows_long_path(path: Path | str) -> str:
    raw = str(normalize_path(path))
    if os.name != "nt":
        return raw
    raw = normalize_windows_path_text(raw)
    if raw.startswith("\\\\?\\"):
        return normalize_windows_path_text(raw)
    absolute = os.path.abspath(raw)
    absolute = normalize_windows_path_text(absolute)
    if absolute.startswith("\\\\"):
        return f"\\\\?\\UNC\\{absolute[2:]}"
    return f"\\\\?\\{absolute}"


def to_windows_arg_path(path: Path | str, *, use_extended_paths: bool) -> str:
    raw = str(normalize_path(path))
    if os.name != "nt":
        return raw
    raw = normalize_windows_path_text(raw)
    if use_extended_paths:
        return to_windows_long_path(raw)
    if raw.startswith("\\\\?\\"):
        return normalize_windows_path_text(display_path(raw))
    return normalize_windows_path_text(os.path.abspath(raw))


def resolve_use_extended_paths(
    request: OperationRequest,
    *,
    default: bool,
) -> bool:
    _ = request
    return bool(default)


def display_path(path: Path | str) -> str:
    raw = str(path)
    if os.name != "nt":
        return raw
    return strip_windows_long_path_text(raw)


def quoted(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def split_args(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(" ") if part.strip()]


def is_success_robocopy_exit_code(code: int) -> bool:
    return int(code) <= 7


def safe_target(destination: Path, source_name: str) -> Path:
    candidate = destination / source_name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        next_candidate = destination / f"{stem} ({index}){suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def remove_existing(path: Path) -> None:
    long_raw = to_windows_long_path(path)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(long_raw)
        return
    Path(long_raw).unlink(missing_ok=False)
