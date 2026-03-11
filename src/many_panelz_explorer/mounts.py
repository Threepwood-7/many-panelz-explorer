from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStorageInfo

MAX_VOLUME_NAME_CHARS = 1024
ERROR_NO_MORE_FILES = 18
WINDOWS_ROOTS_CACHE_TTL_SECONDS = 2.0

_windows_roots_cache: tuple[float, list[Path]] | None = None
_storage_usage_cache: tuple[float, list["StorageUsageEntry"]] | None = None


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


def _windows_drive_roots() -> list[Path]:
    try:
        import ctypes
    except Exception:
        return []

    try:
        mask = ctypes.windll.kernel32.GetLogicalDrives()
    except Exception:
        return []

    roots: list[Path] = []
    for index in range(26):
        if not (mask & (1 << index)):
            continue
        letter = chr(ord("A") + index)
        root = Path(f"{letter}:\\")
        roots.append(root)
    return roots


def _windows_volume_mount_paths() -> list[Path]:
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return []

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    find_first = kernel32.FindFirstVolumeW
    find_next = kernel32.FindNextVolumeW
    find_close = kernel32.FindVolumeClose
    get_paths = kernel32.GetVolumePathNamesForVolumeNameW

    find_first.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
    find_first.restype = wintypes.HANDLE
    find_next.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD]
    find_next.restype = wintypes.BOOL
    find_close.argtypes = [wintypes.HANDLE]
    find_close.restype = wintypes.BOOL
    get_paths.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_paths.restype = wintypes.BOOL

    volume_name_buffer = ctypes.create_unicode_buffer(MAX_VOLUME_NAME_CHARS)

    handle = find_first(volume_name_buffer, MAX_VOLUME_NAME_CHARS)
    invalid_handle = wintypes.HANDLE(-1).value
    if handle == invalid_handle:
        return []

    mount_paths: list[Path] = []

    try:
        while True:
            volume_name = volume_name_buffer.value
            required = wintypes.DWORD(0)
            get_paths(volume_name, None, 0, ctypes.byref(required))

            if required.value > 0:
                path_buffer = ctypes.create_unicode_buffer(required.value)
                if get_paths(
                    volume_name, path_buffer, required.value, ctypes.byref(required)
                ):
                    raw = "".join(path_buffer[: required.value])
                    for item in raw.split("\x00"):
                        if item:
                            mount_paths.append(Path(item))

            if not find_next(handle, volume_name_buffer, MAX_VOLUME_NAME_CHARS):
                if ctypes.get_last_error() == ERROR_NO_MORE_FILES:
                    break
                break
    finally:
        find_close(handle)

    return mount_paths


def _qt_mounted_roots() -> list[Path]:
    roots: list[Path] = []
    for volume in QStorageInfo.mountedVolumes():
        if not volume.isValid():
            continue
        mount = volume.rootPath()
        if mount:
            roots.append(Path(mount))
    return roots


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


def _dedup_exact_roots(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        normalized = os.path.normcase(os.path.normpath(str(path)))
        if normalized in seen:
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


def _storage_info_for_path(path: Path) -> QStorageInfo:
    return QStorageInfo(str(path))


def _storage_usage_for_root(root: Path) -> StorageUsageEntry | None:
    storage = _storage_info_for_path(root)
    if not storage.isValid():
        return None

    total = int(storage.bytesTotal())
    available = int(storage.bytesAvailable())
    if total <= 0 or available < 0:
        return None

    available_clamped = min(available, total)
    used = max(0, total - available_clamped)
    ratio = float(used / total) if total else 0.0
    volume_label = str(storage.displayName() or storage.name() or "").strip()
    return StorageUsageEntry(
        root_path=root,
        display_root=_display_root(root),
        volume_label=volume_label,
        bytes_used=used,
        bytes_total=total,
        usage_ratio=ratio,
    )


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

    candidates: list[Path] = []
    candidates.extend(_windows_drive_roots())
    candidates.extend(_windows_volume_mount_paths())
    roots = _dedup_roots(candidates, require_existing=False)

    _windows_roots_cache = (now, roots)
    return list(roots)


def list_roots_for_navigation(current_path: Path | None = None) -> list[Path]:
    _ = current_path
    if _is_windows():
        return _list_windows_roots_cached()

    # Keep discovery/provider order stable; dedup/filter only.
    return _dedup_roots(_qt_mounted_roots(), require_existing=True)


def list_storage_usage_entries(
    current_path: Path | None = None,
) -> list[StorageUsageEntry]:
    _ = current_path
    global _storage_usage_cache

    now = _monotonic_seconds()
    if _storage_usage_cache is not None:
        cached_at, cached_entries = _storage_usage_cache
        if now - cached_at < WINDOWS_ROOTS_CACHE_TTL_SECONDS:
            return list(cached_entries)

    roots = _dedup_exact_roots(list_roots_for_navigation(current_path))
    entries: list[StorageUsageEntry] = []
    for root in roots:
        entry = _storage_usage_for_root(root)
        if entry is None:
            continue
        entries.append(entry)

    _storage_usage_cache = (now, entries)
    return list(entries)
