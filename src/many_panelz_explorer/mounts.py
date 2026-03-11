from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from threep_commons.platform.windows.storage import (
    WindowsStorageUsage,
    list_windows_storage_roots,
    list_windows_storage_usage,
)

WINDOWS_ROOTS_CACHE_TTL_SECONDS = 2.0

_windows_roots_cache: tuple[float, list[Path]] | None = None
_storage_usage_cache: tuple[float, list[StorageUsageEntry]] | None = None


@dataclass(frozen=True)
class StorageUsageEntry:
    root_path: Path
    display_root: str
    volume_label: str
    bytes_used: int
    bytes_total: int
    usage_ratio: float


def _is_windows() -> bool:
    return os.name == "nt"


def _dedup_roots(paths: list[Path], *, require_existing: bool) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()

    for path in paths:
        normalized = os.path.normcase(os.path.normpath(str(path)))
        if normalized in seen:
            continue
        if require_existing and (not path.exists() or not path.is_dir()):
            continue
        seen.add(normalized)
        deduped.append(path)

    return deduped


def _strip_windows_long_path(path: str) -> str:
    return path[4:] if path.startswith("\\\\?\\") else path


def _display_root(path: Path) -> str:
    normalized = os.path.normcase(os.path.normpath(str(path)))
    drive = path.drive
    if drive:
        drive_root = os.path.normcase(os.path.normpath(f"{drive}{os.sep}"))
        if normalized == drive_root:
            return drive
    return _strip_windows_long_path(str(path))


def _monotonic_seconds() -> float:
    return time.monotonic()


def clear_roots_cache() -> None:
    global _windows_roots_cache
    global _storage_usage_cache
    _windows_roots_cache = None
    _storage_usage_cache = None


def _list_windows_roots_cached() -> list[Path]:
    global _windows_roots_cache

    now = _monotonic_seconds()
    if _windows_roots_cache is not None:
        cached_at, cached_roots = _windows_roots_cache
        if now - cached_at < WINDOWS_ROOTS_CACHE_TTL_SECONDS:
            return list(cached_roots)

    roots = _dedup_roots(list_windows_storage_roots(), require_existing=False)
    _windows_roots_cache = (now, roots)
    return list(roots)


def _list_non_windows_roots(current_path: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if current_path is not None:
        anchor = Path(current_path).anchor
        if anchor:
            candidates.append(Path(anchor))
    if not candidates:
        candidates.append(Path(os.sep))
    return _dedup_roots(candidates, require_existing=True)


def list_roots_for_navigation(current_path: Path | None = None) -> list[Path]:
    if _is_windows():
        return _list_windows_roots_cached()
    return _list_non_windows_roots(current_path)


def _storage_usage_entry_from_raw(raw: WindowsStorageUsage) -> StorageUsageEntry | None:
    total = max(0, int(raw.bytes_total))
    if total <= 0:
        return None
    used = max(0, min(int(raw.bytes_used), total))
    ratio = float(used / total) if total else 0.0
    return StorageUsageEntry(
        root_path=Path(raw.root_path),
        display_root=_display_root(Path(raw.root_path)),
        volume_label=str(raw.volume_label or "").strip(),
        bytes_used=used,
        bytes_total=total,
        usage_ratio=ratio,
    )


def list_storage_usage_entries(
    current_path: Path | None = None,
) -> list[StorageUsageEntry]:
    _ = current_path
    global _storage_usage_cache

    if not _is_windows():
        return []

    now = _monotonic_seconds()
    if _storage_usage_cache is not None:
        cached_at, cached_entries = _storage_usage_cache
        if now - cached_at < WINDOWS_ROOTS_CACHE_TTL_SECONDS:
            return list(cached_entries)

    raw_entries = list_windows_storage_usage()
    entries: list[StorageUsageEntry] = []
    seen: set[str] = set()
    for raw in raw_entries:
        entry = _storage_usage_entry_from_raw(raw)
        if entry is None:
            continue
        key = os.path.normcase(os.path.normpath(str(entry.root_path)))
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)

    _storage_usage_cache = (now, entries)
    return list(entries)
