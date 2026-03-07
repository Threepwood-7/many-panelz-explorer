from pathlib import Path

from many_panelz_explorer import mounts


def test_windows_roots_include_drives_and_directory_mount_points(monkeypatch, tmp_path: Path) -> None:
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


def test_root_dedup_and_order_stability(monkeypatch, tmp_path: Path) -> None:
    drive = tmp_path / "C_drive"
    mount_a = tmp_path / "mount_a"
    mount_b = tmp_path / "mount_b"
    drive.mkdir(parents=True)
    mount_a.mkdir(parents=True)
    mount_b.mkdir(parents=True)

    monkeypatch.setattr(mounts, "_is_windows", lambda: True)
    monkeypatch.setattr(mounts, "_windows_drive_roots", lambda: [mount_b, drive, drive])
    monkeypatch.setattr(mounts, "_windows_volume_mount_paths", lambda: [mount_a, mount_b])

    roots = mounts.list_roots_for_navigation(None)
    assert len(roots) == 3
    assert roots == [mount_b, drive, mount_a]


def test_non_windows_fallback_uses_qstorageinfo_mounts(monkeypatch, tmp_path: Path) -> None:
    mount_a = tmp_path / "mnt_a"
    mount_b = tmp_path / "mnt_b"
    current = mount_b / "x"
    mount_a.mkdir(parents=True)
    current.mkdir(parents=True)

    monkeypatch.setattr(mounts, "_is_windows", lambda: False)
    monkeypatch.setattr(mounts, "_qt_mounted_roots", lambda: [mount_a, mount_b])

    roots = mounts.list_roots_for_navigation(current)
    assert roots == [mount_a, mount_b]
