from __future__ import annotations

import os
import shutil
from pathlib import Path

from .types import OperationRequest


def normalize_path(path: Path | str) -> Path:
    return Path(path).expanduser()


def _windows_native_separators(raw: str) -> str:
    if os.name != "nt":
        return raw
    return str(raw).replace("/", "\\")


def to_windows_long_path(path: Path | str) -> str:
    raw = _windows_native_separators(str(normalize_path(path)))
    if os.name != "nt":
        return raw
    if raw.startswith("\\\\?\\"):
        return _windows_native_separators(raw)
    absolute = os.path.abspath(raw)
    absolute = _windows_native_separators(absolute)
    if absolute.startswith("\\\\"):
        return f"\\\\?\\UNC\\{absolute[2:]}"
    return f"\\\\?\\{absolute}"


def to_windows_arg_path(path: Path | str, *, use_extended_paths: bool) -> str:
    raw = _windows_native_separators(str(normalize_path(path)))
    if os.name != "nt":
        return raw
    if use_extended_paths:
        return to_windows_long_path(raw)
    if raw.startswith("\\\\?\\"):
        return _windows_native_separators(display_path(raw))
    return _windows_native_separators(os.path.abspath(raw))


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
    raw = _windows_native_separators(raw)
    if raw.startswith("\\\\?\\UNC\\"):
        return _windows_native_separators(f"\\\\{raw[8:]}")
    if raw.startswith("\\\\?\\"):
        return _windows_native_separators(raw[4:])
    return _windows_native_separators(raw)


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
