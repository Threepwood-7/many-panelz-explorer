from __future__ import annotations

import os
import re
import shutil
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath

WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_UNC_PATH_RE = re.compile(r"^[\\/]{2}[^\\/]+[\\/][^\\/]+")
WINDOWS_DEVICE_PATH_RE = re.compile(r"^[\\/]{2}[?.][\\/]")


def is_windows() -> bool:
    return os.name == "nt"


def coerce_path(value: Path | str) -> Path:
    if isinstance(value, Path):
        return value.expanduser()
    return Path(normalize_windows_path_text(str(value))).expanduser()


def normalize_windows_path_text(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return text
    if not _looks_like_windows_path(text) and not _has_path_separator(text):
        return text
    return str(PureWindowsPath(text))


def strip_windows_long_path_text(text: str) -> str:
    raw = normalize_windows_path_text(str(text or ""))
    if raw.startswith("\\\\?\\UNC\\"):
        return normalize_windows_path_text(f"\\\\{raw[8:]}")
    if raw.startswith("\\\\?\\"):
        return normalize_windows_path_text(raw[4:])
    return raw


def display_path_text(path: Path | str) -> str:
    raw = str(path)
    if not raw:
        return raw
    if is_windows() or raw.startswith("\\\\?\\") or _looks_like_windows_path(raw):
        return strip_windows_long_path_text(raw)
    return raw


def path_key(path: Path | str) -> str:
    normalized = display_path_text(coerce_path(path))
    if is_windows() or _looks_like_windows_path(normalized):
        return normalize_windows_path_text(normalized).casefold()
    return str(Path(normalized))


def is_drive_root(path: Path | str) -> bool:
    candidate = coerce_path(path)
    if not candidate.drive:
        return False
    return path_key(candidate) == path_key(Path(f"{candidate.drive}{os.sep}"))


def is_path_under_root(path: Path | str, root: Path | str) -> bool:
    candidate_key = path_key(path)
    root_key = path_key(root)
    if candidate_key == root_key:
        return True
    separator = "\\" if _uses_windows_path_semantics(root, path) else os.sep
    prefix = root_key if root_key.endswith(separator) else f"{root_key}{separator}"
    return candidate_key.startswith(prefix)


def display_root(path: Path | str) -> str:
    candidate = coerce_path(path)
    if is_drive_root(candidate):
        return candidate.drive
    return display_path_text(candidate)


def navigation_root_text(path: Path | str) -> str:
    candidate = coerce_path(path)
    if is_drive_root(candidate):
        return candidate.drive
    if is_windows():
        name = candidate.name.strip()
        if name:
            return name
    return display_path_text(candidate)


def dedup_paths(paths: Iterable[Path | str], *, require_existing: bool) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for raw_path in paths:
        candidate = coerce_path(raw_path)
        if require_existing and (not candidate.exists() or not candidate.is_dir()):
            continue
        key = path_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def is_explicit_path_text(raw: str) -> bool:
    text = normalize_windows_path_text(str(raw or "").strip())
    if not text:
        return False
    candidate = Path(text)
    return candidate.is_absolute() or _has_path_separator(text)


def resolve_executable_path(raw: str) -> Path | None:
    text = normalize_windows_path_text(str(raw or "").strip())
    if not text:
        return None
    if is_explicit_path_text(text):
        candidate = Path(text)
        if candidate.exists():
            return candidate
        return None
    which_hit = shutil.which(text)
    if which_hit:
        return Path(which_hit)
    return None


def _looks_like_windows_path(text: str) -> bool:
    return bool(
        WINDOWS_DRIVE_PATH_RE.match(text)
        or WINDOWS_UNC_PATH_RE.match(text)
        or WINDOWS_DEVICE_PATH_RE.match(text)
    )


def _has_path_separator(text: str) -> bool:
    return "\\" in text or "/" in text


def _uses_windows_path_semantics(*paths: Path | str) -> bool:
    if is_windows():
        return True
    return any(_looks_like_windows_path(str(path)) for path in paths)
