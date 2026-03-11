from pathlib import Path

import pytest

from many_panelz_explorer import mounts


class _FakeStorageInfo:
    def __init__(
        self,
        *,
        valid: bool = True,
        total: int = 0,
        available: int = 0,
        display_name: str = "",
        name: str = "",
    ) -> None:
        self._valid = valid
        self._total = total
        self._available = available
        self._display_name = display_name
        self._name = name

    def isValid(self) -> bool:
        return self._valid

    def bytesTotal(self) -> int:
        return self._total

    def bytesAvailable(self) -> int:
        return self._available

    def displayName(self) -> str:
        return self._display_name

    def name(self) -> str:
        return self._name


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

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_windows_drive_roots", lambda: [drive])
    monkeypatch.setattr(mounts, "_windows_volume_mount_paths", lambda: [mount])

    roots = mounts.list_roots_for_navigation(current)
    assert roots == [drive, mount]


def test_windows_roots_do_not_probe_path_existence(monkeypatch) -> None:
    drive = Path("C:\\")
    network = Path("\\\\server\\offline")

    def _boom(_self: Path) -> bool:
        raise AssertionError("exists/is_dir should not be called on Windows roots")

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_windows_drive_roots", lambda: [drive])
    monkeypatch.setattr(mounts, "_windows_volume_mount_paths", lambda: [network])
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

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_windows_drive_roots", lambda: [mount_b, drive, drive])
    monkeypatch.setattr(
        mounts, "_windows_volume_mount_paths", lambda: [mount_a, mount_b]
    )

    roots = mounts.list_roots_for_navigation(None)
    assert len(roots) == 3
    assert roots == [mount_b, drive, mount_a]


def test_windows_roots_use_cache_within_ttl(monkeypatch) -> None:
    counters = {"drives": 0, "mounts": 0}
    times = iter([10.0, 10.5, 13.0])

    def _drives() -> list[Path]:
        counters["drives"] += 1
        return [Path("C:\\")]

    def _mounts() -> list[Path]:
        counters["mounts"] += 1
        return [Path("D:\\mount")]

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_windows_drive_roots", _drives)
    monkeypatch.setattr(mounts, "_windows_volume_mount_paths", _mounts)
    monkeypatch.setattr(mounts, "_monotonic_seconds", lambda: next(times))

    first = mounts.list_roots_for_navigation(None)
    second = mounts.list_roots_for_navigation(None)
    third = mounts.list_roots_for_navigation(None)

    assert first == [Path("C:\\"), Path("D:\\mount")]
    assert second == first
    assert third == first
    assert counters == {"drives": 2, "mounts": 2}


def test_clear_roots_cache_forces_windows_rediscovery(monkeypatch) -> None:
    counters = {"drives": 0, "mounts": 0}

    def _drives() -> list[Path]:
        counters["drives"] += 1
        return [Path("C:\\")]

    def _mounts() -> list[Path]:
        counters["mounts"] += 1
        return [Path("D:\\mount")]

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_windows_drive_roots", _drives)
    monkeypatch.setattr(mounts, "_windows_volume_mount_paths", _mounts)
    monkeypatch.setattr(mounts, "_monotonic_seconds", lambda: 100.0)

    mounts.list_roots_for_navigation(None)
    mounts.list_roots_for_navigation(None)
    mounts.clear_roots_cache()
    mounts.list_roots_for_navigation(None)

    assert counters == {"drives": 2, "mounts": 2}


def test_non_windows_fallback_uses_qstorageinfo_mounts(
    monkeypatch, tmp_path: Path
) -> None:
    mount_a = tmp_path / "mnt_a"
    mount_b = tmp_path / "mnt_b"
    current = mount_b / "x"
    mount_a.mkdir(parents=True)
    current.mkdir(parents=True)

    monkeypatch.setattr(mounts, "_is_windows", lambda: False)
    monkeypatch.setattr(mounts, "_qt_mounted_roots", lambda: [mount_a, mount_b])

    roots = mounts.list_roots_for_navigation(current)
    assert roots == [mount_a, mount_b]


def test_storage_usage_entries_include_windows_drive_and_mount_points(
    monkeypatch,
) -> None:
    drive = Path("C:\\")
    mount = Path("C:\\mounts\\media01")
    storage_map = {
        drive: _FakeStorageInfo(
            valid=True,
            total=1_000,
            available=400,
            display_name="System",
            name="SYS",
        ),
        mount: _FakeStorageInfo(
            valid=True,
            total=2_000,
            available=500,
            display_name="Archive",
            name="ARCH",
        ),
    }

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_list_windows_roots_cached", lambda: [drive, mount])
    monkeypatch.setattr(
        mounts,
        "_storage_info_for_path",
        lambda path: storage_map[path],
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


def test_storage_usage_entries_skip_invalid_or_unavailable(monkeypatch) -> None:
    good = Path("C:\\")
    invalid = Path("D:\\")
    unavailable = Path("E:\\")
    storage_map = {
        good: _FakeStorageInfo(
            valid=True,
            total=100,
            available=40,
            display_name="Good",
            name="GOOD",
        ),
        invalid: _FakeStorageInfo(valid=False, total=300, available=50),
        unavailable: _FakeStorageInfo(valid=True, total=0, available=0),
    }

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(
        mounts,
        "_list_windows_roots_cached",
        lambda: [good, invalid, unavailable],
    )
    monkeypatch.setattr(
        mounts,
        "_storage_info_for_path",
        lambda path: storage_map[path],
    )

    entries = mounts.list_storage_usage_entries(None)
    assert [entry.root_path for entry in entries] == [good]


def test_storage_usage_entries_dedup_exact_roots_stable_order(monkeypatch) -> None:
    drive = Path("C:\\")
    mount = Path("C:\\mounts\\vol1")

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(
        mounts,
        "_list_windows_roots_cached",
        lambda: [drive, drive, mount, mount],
    )
    monkeypatch.setattr(
        mounts,
        "_storage_info_for_path",
        lambda path: _FakeStorageInfo(
            valid=True,
            total=100,
            available=20,
            display_name=str(path),
            name="",
        ),
    )

    entries = mounts.list_storage_usage_entries(None)
    assert [entry.root_path for entry in entries] == [drive, mount]


def test_storage_usage_entries_use_cache_within_ttl(monkeypatch) -> None:
    counters = {"roots": 0, "storage": 0}
    times = iter([10.0, 10.5, 13.0])
    drive = Path("C:\\")

    def _roots() -> list[Path]:
        counters["roots"] += 1
        return [drive]

    def _storage(_path: Path) -> _FakeStorageInfo:
        counters["storage"] += 1
        return _FakeStorageInfo(
            valid=True,
            total=200,
            available=150,
            display_name="System",
            name="",
        )

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_list_windows_roots_cached", _roots)
    monkeypatch.setattr(mounts, "_storage_info_for_path", _storage)
    monkeypatch.setattr(mounts, "_monotonic_seconds", lambda: next(times))

    first = mounts.list_storage_usage_entries(None)
    second = mounts.list_storage_usage_entries(None)
    third = mounts.list_storage_usage_entries(None)

    assert [entry.root_path for entry in first] == [drive]
    assert second == first
    assert third == first
    assert counters == {"roots": 2, "storage": 2}
