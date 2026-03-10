from __future__ import annotations

from typing import TYPE_CHECKING

from many_panelz_explorer._context.detector import ContextDetector

if TYPE_CHECKING:
    from pathlib import Path


def _write_git_marker(root: Path, *, branch: str, remote_url: str) -> None:
    git_dir = root / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")
    (git_dir / "config").write_text(
        "[core]\n"
        "\trepositoryformatversion = 0\n"
        "[remote \"origin\"]\n"
        f"\turl = {remote_url}\n",
        encoding="utf-8",
    )


def test_detects_python_git_node_in_current_and_children(tmp_path: Path) -> None:
    current = tmp_path / "workspace"
    current.mkdir()
    (current / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    git_child = current / "repo-git"
    git_child.mkdir()
    _write_git_marker(
        git_child,
        branch="main",
        remote_url="git@github.com:acme/repo-git.git",
    )

    node_child = current / "repo-node"
    node_child.mkdir()
    (node_child / "package.json").write_text(
        '{"name":"repo-node","scripts":{"dev":"vite"}}',
        encoding="utf-8",
    )

    result = ContextDetector(immediate_child_scan_cap=33).detect(current)

    assert [item.root_path for item in result.python_roots] == [current]
    assert [item.root_path for item in result.git_roots] == [git_child]
    assert [item.root_path for item in result.node_roots] == [node_child]


def test_immediate_child_scan_cap_limits_detection(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    for idx in range(5):
        child = root / f"child-{idx:02d}"
        child.mkdir()
        (child / "package.json").write_text(
            '{"name":"x","scripts":{"build":"echo ok"}}',
            encoding="utf-8",
        )

    result = ContextDetector(immediate_child_scan_cap=2).detect(root)

    assert len(result.node_roots) <= 2


def test_node_runner_prefers_package_manager_then_lockfile(tmp_path: Path) -> None:
    root = tmp_path / "node-project"
    root.mkdir()
    (root / "package.json").write_text(
        '{"name":"node-project","packageManager":"pnpm@9.0.0","scripts":{"dev":"vite"}}',
        encoding="utf-8",
    )
    detected = ContextDetector().detect(root)
    assert len(detected.node_roots) == 1
    assert detected.node_roots[0].runner == "pnpm"

    (root / "package.json").write_text(
        '{"name":"node-project","scripts":{"dev":"vite"}}',
        encoding="utf-8",
    )
    (root / "bun.lockb").write_text("", encoding="utf-8")
    detected_lock = ContextDetector().detect(root)
    assert len(detected_lock.node_roots) == 1
    assert detected_lock.node_roots[0].runner == "bun"


def test_git_remote_web_url_allowlist(tmp_path: Path) -> None:
    allowed = tmp_path / "git-allowed"
    allowed.mkdir()
    _write_git_marker(
        allowed,
        branch="feature/demo",
        remote_url="git@github.com:acme/allowed.git",
    )
    allowed_detected = ContextDetector().detect(allowed)
    assert len(allowed_detected.git_roots) == 1
    assert allowed_detected.git_roots[0].remote_origin_web_url == "https://github.com/acme/allowed"

    blocked = tmp_path / "git-blocked"
    blocked.mkdir()
    _write_git_marker(
        blocked,
        branch="main",
        remote_url="git@example.com:acme/blocked.git",
    )
    blocked_detected = ContextDetector().detect(blocked)
    assert len(blocked_detected.git_roots) == 1
    assert blocked_detected.git_roots[0].remote_origin_web_url is None
