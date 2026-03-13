"""Tests for operation artifact path handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from many_panelz_explorer._operations import artifacts

if TYPE_CHECKING:
    from pathlib import Path


def test_ensure_artifacts_root_creates_and_reuses_private_temp_root(
    monkeypatch, tmp_path: Path
) -> None:
    created_roots: list[Path] = []

    def _fake_mkdtemp(*, prefix: str) -> str:
        root = tmp_path / f"{prefix}session"
        root.mkdir(parents=True, exist_ok=True)
        created_roots.append(root)
        return str(root)

    monkeypatch.setattr(artifacts, "_artifacts_root", None)
    monkeypatch.setattr(artifacts.tempfile, "mkdtemp", _fake_mkdtemp)

    first_root = artifacts.ensure_artifacts_root()
    second_root = artifacts.ensure_artifacts_root()

    assert first_root == second_root
    assert first_root.exists()
    assert first_root.name.startswith("many-panelz-explorer-ops-")
    assert created_roots == [first_root]


def test_prepare_artifacts_uses_session_root(monkeypatch, tmp_path: Path) -> None:
    session_root = tmp_path / "many-panelz-explorer-ops-session"
    session_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(artifacts, "_artifacts_root", session_root)

    prepared = artifacts.prepare_artifacts("job-123")

    assert prepared.job_dir == session_root / "job-123"
    assert prepared.job_dir.exists()
    assert prepared.metadata_path == prepared.job_dir / "job.json"
    assert prepared.log_path == prepared.job_dir / "output.log"
    assert prepared.script_path == prepared.job_dir / "run.cmd"
