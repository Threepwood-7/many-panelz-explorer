from __future__ import annotations

from pathlib import Path

import pytest
from threep_commons.platform.windows.storage import WindowsStorageUsage

from many_panelz_explorer import mounts


def _raw_usage(
    root: Path,
    *,
    total: int,
    used: int,
    label: str = "",
    tokens: set[str] | None = None,
) -> WindowsStorageUsage:
    return WindowsStorageUsage(
        root_path=root,
        volume_identity=f"volume:{str(root).lower()}",
        volume_label=label,
        disk_tokens=tokens or {"disk:0"},
        bytes_used=used,
        bytes_total=total,
    )


@pytest.fixture(autouse=True)
def _clear_roots_cache() -> None:
    mounts.clear_roots_cache()


def test_windows_roots_include_drives_and_directory_mount_points(
    monkeypatch, tmp_path: Path
) -> None:
    drive = tmp_path / "D_drive"
    mount = tmp_path / "mounts" / "vol1"
    current = mount / "nested"
    drive.mkdir(parents=True)
    current.mkdir(parents=True)

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(mounts, "list_windows_storage_roots", lambda: [drive, mount])

    roots = mounts.list_roots_for_navigation(current)

    assert roots == [drive, mount]


def test_windows_roots_do_not_probe_path_existence(monkeypatch) -> None:
    drive = Path("C:\\")
    network = Path("\\\\server\\offline")

    def _boom(_self: Path) -> bool:
        raise AssertionError("exists/is_dir should not be called on Windows roots")

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(mounts, "list_windows_storage_roots", lambda: [drive, network])
    monkeypatch.setattr(mounts.Path, "exists", _boom, raising=False)
    monkeypatch.setattr(mounts.Path, "is_dir", _boom, raising=False)

    roots = mounts.list_roots_for_navigation(None)

    assert roots == [drive, network]


def test_root_dedup_and_order_stability(monkeypatch, tmp_path: Path) -> None:
    drive = tmp_path / "C_drive"
    mount_a = tmp_path / "mount_a"
    mount_b = tmp_path / "mount_b"
    drive.mkdir(parents=True)
    mount_a.mkdir(parents=True)
    mount_b.mkdir(parents=True)

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        mounts,
        "list_windows_storage_roots",
        lambda: [mount_b, drive, drive, mount_a, mount_b],
    )

    roots = mounts.list_roots_for_navigation(None)

    assert roots == [mount_b, drive, mount_a]


def test_windows_roots_use_cache_within_ttl(monkeypatch) -> None:
    counters = {"roots": 0}
    times = iter([10.0, 10.5, 13.0])

    def _roots() -> list[Path]:
        counters["roots"] += 1
        return [Path("C:\\"), Path("D:\\mount")]

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(mounts, "list_windows_storage_roots", _roots)
    monkeypatch.setattr(mounts, "_monotonic_seconds", lambda: next(times))

    first = mounts.list_roots_for_navigation(None)
    second = mounts.list_roots_for_navigation(None)
    third = mounts.list_roots_for_navigation(None)

    assert first == [Path("C:\\"), Path("D:\\mount")]
    assert second == first
    assert third == first
    assert counters == {"roots": 2}


def test_clear_roots_cache_forces_windows_rediscovery(monkeypatch) -> None:
    counters = {"roots": 0}

    def _roots() -> list[Path]:
        counters["roots"] += 1
        return [Path("C:\\"), Path("D:\\mount")]

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(mounts, "list_windows_storage_roots", _roots)
    monkeypatch.setattr(mounts, "_monotonic_seconds", lambda: 100.0)

    mounts.list_roots_for_navigation(None)
    mounts.list_roots_for_navigation(None)
    mounts.clear_roots_cache()
    mounts.list_roots_for_navigation(None)

    assert counters == {"roots": 2}


def test_non_windows_fallback_uses_current_anchor(monkeypatch, tmp_path: Path) -> None:
    current = tmp_path / "nested" / "path"
    current.parent.mkdir(parents=True)

    monkeypatch.setattr(mounts.os, "name", "posix", raising=False)

    roots = mounts.list_roots_for_navigation(current)

    assert roots == [Path(mounts.os.sep)]


def test_storage_usage_entries_include_windows_drive_and_mount_points(
    monkeypatch,
) -> None:
    drive = Path("C:\\")
    mount = Path("C:\\mounts\\media01")

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        mounts,
        "list_windows_storage_usage",
        lambda: [
            _raw_usage(drive, total=1_000, used=600, label="System"),
            _raw_usage(mount, total=2_000, used=1_500, label="Archive"),
        ],
    )

    entries = mounts.list_storage_usage_entries(None)

    assert [entry.root_path for entry in entries] == [drive, mount]
    assert entries[0].display_root == "C:"
    assert entries[0].volume_label == "System"
    assert entries[0].bytes_used == 600
    assert entries[0].bytes_total == 1_000
    assert entries[1].display_root == str(mount)
    assert entries[1].volume_label == "Archive"
    assert entries[1].bytes_used == 1_500
    assert entries[1].bytes_total == 2_000


def test_storage_usage_entries_skip_zero_total(monkeypatch) -> None:
    good = Path("C:\\")
    unavailable = Path("E:\\")

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        mounts,
        "list_windows_storage_usage",
        lambda: [
            _raw_usage(good, total=100, used=60, label="Good"),
            _raw_usage(unavailable, total=0, used=0, label="Unavailable"),
        ],
    )

    entries = mounts.list_storage_usage_entries(None)

    assert [entry.root_path for entry in entries] == [good]


def test_storage_usage_entries_dedup_exact_roots_stable_order(monkeypatch) -> None:
    drive = Path("C:\\")
    mount = Path("C:\\mounts\\vol1")

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        mounts,
        "list_windows_storage_usage",
        lambda: [
            _raw_usage(drive, total=100, used=80, label="Drive"),
            _raw_usage(drive, total=100, used=80, label="Drive"),
            _raw_usage(mount, total=200, used=40, label="Mount"),
            _raw_usage(mount, total=200, used=40, label="Mount"),
        ],
    )

    entries = mounts.list_storage_usage_entries(None)

    assert [entry.root_path for entry in entries] == [drive, mount]


def test_storage_usage_entries_clamp_used_bytes(monkeypatch) -> None:
    drive = Path("C:\\")

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        mounts,
        "list_windows_storage_usage",
        lambda: [_raw_usage(drive, total=200, used=250, label="System")],
    )

    entries = mounts.list_storage_usage_entries(None)

    assert entries == [
        mounts.StorageUsageEntry(
            root_path=drive,
            display_root="C:",
            volume_label="System",
            bytes_used=200,
            bytes_total=200,
            usage_ratio=1.0,
        )
    ]


def test_storage_usage_entries_use_cache_within_ttl(monkeypatch) -> None:
    counters = {"storage": 0}
    times = iter([10.0, 10.5, 13.0])
    drive = Path("C:\\")

    def _storage() -> list[WindowsStorageUsage]:
        counters["storage"] += 1
        return [_raw_usage(drive, total=200, used=50, label="System")]

    monkeypatch.setattr(mounts.os, "name", "nt", raising=False)
    monkeypatch.setattr(mounts, "list_windows_storage_usage", _storage)
    monkeypatch.setattr(mounts, "_monotonic_seconds", lambda: next(times))

    first = mounts.list_storage_usage_entries(None)
    second = mounts.list_storage_usage_entries(None)
    third = mounts.list_storage_usage_entries(None)

    assert [entry.root_path for entry in first] == [drive]
    assert second == first
    assert third == first
    assert counters == {"storage": 2}
