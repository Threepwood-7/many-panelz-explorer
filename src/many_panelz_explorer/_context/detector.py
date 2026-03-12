from __future__ import annotations

import configparser
import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

_PYTHON_MARKER_FILES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "uv.lock",
    "hatch.toml",
    ".python-version",
}
_PYTHON_MARKER_DIRS = {".venv"}
_NODE_MARKER_FILES = {"package.json", "bun.lockb", "pnpm-lock.yaml", "yarn.lock"}
_NODE_MARKER_DIRS = {"node_modules"}
_GIT_ALLOWED_REMOTE_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}
_GIT_SSH_URL_RE = re.compile(r"^[^@]+@(?P<host>[^:]+):(?P<path>.+)$")


def _string_object_mapping(value: object) -> dict[str, object] | None:
    """Normalize decoded config payloads into string-key object mappings."""

    if not isinstance(value, dict):
        return None
    return {
        str(key): item
        for key, item in cast("dict[object, object]", value).items()
    }


@dataclass(frozen=True)
class PythonContextRoot:
    root_path: Path
    pyproject_path: Path | None
    python_version: str | None


@dataclass(frozen=True)
class GitContextRoot:
    root_path: Path
    git_dir: Path
    branch: str | None
    remote_origin_url: str | None
    remote_origin_web_url: str | None


@dataclass(frozen=True)
class NodeContextRoot:
    root_path: Path
    package_json_path: Path | None
    runner: str


@dataclass(frozen=True)
class ContextDetectionResult:
    python_roots: list[PythonContextRoot]
    git_roots: list[GitContextRoot]
    node_roots: list[NodeContextRoot]

    @property
    def has_any(self) -> bool:
        return bool(self.python_roots or self.git_roots or self.node_roots)


class ContextDetector:
    def __init__(self, *, immediate_child_scan_cap: int = 33) -> None:
        self._immediate_child_scan_cap = max(1, int(immediate_child_scan_cap))

    def detect(self, active_path: Path) -> ContextDetectionResult:
        target = Path(active_path).expanduser()
        if not target.exists() or not target.is_dir():
            return ContextDetectionResult([], [], [])

        candidate_roots = [target, *self._child_roots(target)]
        python_roots: list[PythonContextRoot] = []
        git_roots: list[GitContextRoot] = []
        node_roots: list[NodeContextRoot] = []
        for root in candidate_roots:
            python = self._detect_python_root(root)
            if python is not None:
                python_roots.append(python)
            git = self._detect_git_root(root)
            if git is not None:
                git_roots.append(git)
            node = self._detect_node_root(root)
            if node is not None:
                node_roots.append(node)

        def _sort_key(
            value: PythonContextRoot | GitContextRoot | NodeContextRoot,
        ) -> str:
            return str(value.root_path).casefold()

        python_roots.sort(key=_sort_key)
        git_roots.sort(key=_sort_key)
        node_roots.sort(key=_sort_key)
        return ContextDetectionResult(
            python_roots=python_roots,
            git_roots=git_roots,
            node_roots=node_roots,
        )

    def _child_roots(self, parent: Path) -> list[Path]:
        roots: list[Path] = []
        scanned = 0
        try:
            with os.scandir(parent) as iterator:
                for entry in iterator:
                    if scanned >= self._immediate_child_scan_cap:
                        break
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    scanned += 1
                    roots.append(Path(entry.path))
        except OSError:
            return []
        return roots

    def _detect_python_root(self, root: Path) -> PythonContextRoot | None:
        has_marker = any(
            (root / marker).exists() for marker in _PYTHON_MARKER_FILES
        ) or any((root / marker).is_dir() for marker in _PYTHON_MARKER_DIRS)
        if not has_marker:
            return None
        pyproject = root / "pyproject.toml"
        pyproject_path = pyproject if pyproject.is_file() else None
        return PythonContextRoot(
            root_path=root,
            pyproject_path=pyproject_path,
            python_version=self._detect_python_version(root, pyproject_path),
        )

    def _detect_python_version(
        self, root: Path, pyproject_path: Path | None
    ) -> str | None:
        pyver_file = root / ".python-version"
        if pyver_file.is_file():
            try:
                value = pyver_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                value = []
            if value:
                first = str(value[0]).strip()
                if first:
                    return first
        if pyproject_path is None:
            return None
        try:
            payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return None
        payload_map = _string_object_mapping(payload)
        if payload_map is None:
            return None
        project = _string_object_mapping(payload_map.get("project"))
        if project is None:
            return None
        requires = str(project.get("requires-python", "")).strip()
        return requires or None

    def _detect_git_root(self, root: Path) -> GitContextRoot | None:
        git_dir = self._resolve_git_dir(root)
        if git_dir is None:
            return None
        remote_url = self._read_git_remote_origin(git_dir)
        return GitContextRoot(
            root_path=root,
            git_dir=git_dir,
            branch=self._read_git_branch(git_dir),
            remote_origin_url=remote_url,
            remote_origin_web_url=self._convert_remote_to_web_url(remote_url),
        )

    def _resolve_git_dir(self, root: Path) -> Path | None:
        candidate = root / ".git"
        if candidate.is_dir():
            return candidate
        if not candidate.is_file():
            return None
        try:
            line = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not line.lower().startswith("gitdir:"):
            return None
        raw_path = line.split(":", 1)[1].strip()
        if not raw_path:
            return None
        git_dir = Path(raw_path)
        if not git_dir.is_absolute():
            git_dir = (root / git_dir).resolve()
        return git_dir if git_dir.is_dir() else None

    def _read_git_branch(self, git_dir: Path) -> str | None:
        head_path = git_dir / "HEAD"
        if not head_path.is_file():
            return None
        try:
            head = head_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if head.startswith("ref:"):
            ref = head.split(":", 1)[1].strip()
            return Path(ref).name or ref
        if head:
            return f"detached@{head[:7]}"
        return None

    def _read_git_remote_origin(self, git_dir: Path) -> str | None:
        config_path = git_dir / "config"
        if not config_path.is_file():
            return None
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config_path, encoding="utf-8")
        except (OSError, configparser.Error):
            return None
        if not parser.has_section('remote "origin"'):
            return None
        value = parser.get('remote "origin"', "url", fallback="").strip()
        return value or None

    def _convert_remote_to_web_url(self, remote: str | None) -> str | None:
        value = str(remote or "").strip()
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            host = parsed.netloc.lower()
            if host not in _GIT_ALLOWED_REMOTE_HOSTS:
                return None
            path = parsed.path.removesuffix(".git")
            return f"https://{host}{path}"
        if parsed.scheme == "ssh" and parsed.hostname and parsed.path:
            host = str(parsed.hostname).lower()
            if host not in _GIT_ALLOWED_REMOTE_HOSTS:
                return None
            path = parsed.path.removeprefix("/").removesuffix(".git")
            return f"https://{host}/{path}"
        match = _GIT_SSH_URL_RE.match(value)
        if match is None:
            return None
        host = match.group("host").lower()
        if host not in _GIT_ALLOWED_REMOTE_HOSTS:
            return None
        path = match.group("path").removesuffix(".git")
        return f"https://{host}/{path}"

    def _detect_node_root(self, root: Path) -> NodeContextRoot | None:
        has_marker = any(
            (root / marker).exists() for marker in _NODE_MARKER_FILES
        ) or any((root / marker).is_dir() for marker in _NODE_MARKER_DIRS)
        if not has_marker:
            return None
        package_json = root / "package.json"
        package_json_path = package_json if package_json.is_file() else None
        return NodeContextRoot(
            root_path=root,
            package_json_path=package_json_path,
            runner=self._detect_node_runner(root, package_json_path),
        )

    def _detect_node_runner(self, root: Path, package_json_path: Path | None) -> str:
        if package_json_path is not None:
            try:
                payload = json.loads(package_json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            payload_map = _string_object_mapping(cast("object", payload))
            if payload_map is not None:
                package_manager = str(
                    payload_map.get("packageManager", "")
                ).strip().lower()
                manager = package_manager.split("@", 1)[0]
                if manager in {"npm", "pnpm", "yarn", "bun"}:
                    return manager
        if (root / "bun.lockb").is_file():
            return "bun"
        if (root / "pnpm-lock.yaml").is_file():
            return "pnpm"
        if (root / "yarn.lock").is_file():
            return "yarn"
        return "npm"
