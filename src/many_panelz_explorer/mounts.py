from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QStorageInfo


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

    max_volume_name = 1024
    volume_name_buffer = ctypes.create_unicode_buffer(max_volume_name)

    handle = find_first(volume_name_buffer, max_volume_name)
    invalid_handle = wintypes.HANDLE(-1).value
    if handle == invalid_handle:
        return []

    error_no_more_files = 18
    mount_paths: list[Path] = []

    try:
        while True:
            volume_name = volume_name_buffer.value
            required = wintypes.DWORD(0)
            get_paths(volume_name, None, 0, ctypes.byref(required))

            if required.value > 0:
                path_buffer = ctypes.create_unicode_buffer(required.value)
                if get_paths(volume_name, path_buffer, required.value, ctypes.byref(required)):
                    raw = "".join(path_buffer[: required.value])
                    for item in raw.split("\x00"):
                        if item:
                            mount_paths.append(Path(item))

            if not find_next(handle, volume_name_buffer, max_volume_name):
                if ctypes.get_last_error() == error_no_more_files:
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


def _dedup_existing_roots(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()

    for path in paths:
        normalized = os.path.normcase(os.path.normpath(str(path)))
        if normalized in seen:
            continue
        if not path.exists() or not path.is_dir():
            continue
        seen.add(normalized)
        deduped.append(path)

    return deduped


def list_roots_for_navigation(current_path: Path | None = None) -> list[Path]:
    _ = current_path
    candidates: list[Path] = []
    if _is_windows():
        candidates.extend(_windows_drive_roots())
        candidates.extend(_windows_volume_mount_paths())
    else:
        candidates.extend(_qt_mounted_roots())

    # Keep discovery/provider order stable; dedup/filter only.
    return _dedup_existing_roots(candidates)
