from pathlib import Path

import pytest

from many_panelz_explorer import mounts


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
