from __future__ import annotations

from pathlib import Path

from threep_commons import fs_paths as _paths


def test_path_key_normalizes_windows_case_and_slashes(monkeypatch) -> None:
    monkeypatch.setattr(_paths.os, "name", "nt", raising=False)

    assert _paths.path_key(r"C:\Temp\Alpha") == _paths.path_key(r"c:/temp/alpha")


def test_strip_windows_long_path_text_normalizes_prefixes() -> None:
    assert _paths.strip_windows_long_path_text(r"\\?\C:/tmp/demo") == r"C:\tmp\demo"
    assert (
        _paths.strip_windows_long_path_text(r"\\?\UNC\server/share/path")
        == r"\\server\share\path"
    )


def test_drive_root_and_display_root_use_drive_label(monkeypatch) -> None:
    monkeypatch.setattr(_paths.os, "name", "nt", raising=False)

    drive = Path(r"C:\\")

    assert _paths.is_drive_root(drive) is True
    assert _paths.display_root(drive) == "C:"


def test_is_path_under_root_matches_exact_and_children(monkeypatch) -> None:
    monkeypatch.setattr(_paths.os, "name", "nt", raising=False)

    root = Path(r"C:\root")

    assert _paths.is_path_under_root(root, root) is True
    assert _paths.is_path_under_root(Path(r"C:\root\child"), root) is True
    assert _paths.is_path_under_root(Path(r"C:\root-two"), root) is False


def test_dedup_paths_is_stable_and_can_require_existing(tmp_path: Path) -> None:
    a = tmp_path / "A"
    b = tmp_path / "B"
    missing = tmp_path / "missing"
    a.mkdir()
    b.mkdir()

    assert _paths.dedup_paths([a, a, b], require_existing=False) == [a, b]
    assert _paths.dedup_paths([a, missing, b], require_existing=True) == [a, b]
