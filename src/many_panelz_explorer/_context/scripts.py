from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class RunnableScript:
    label: str
    command: str


def parse_python_runnable_scripts(root: Path) -> list[RunnableScript]:
    scripts: dict[str, RunnableScript] = {}
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.is_file():
        scripts.update(_parse_pyproject_scripts(pyproject_path))
        scripts.update(_parse_hatch_scripts(pyproject_path))
    scripts.update(_parse_python_file_scripts(root))
    return sorted(scripts.values(), key=lambda entry: entry.label.casefold())


def parse_node_runnable_scripts(root: Path, *, runner: str) -> list[RunnableScript]:
    package_json_path = root / "package.json"
    if not package_json_path.is_file():
        return []
    try:
        payload = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    raw_scripts = payload.get("scripts")
    if not isinstance(raw_scripts, dict):
        return []
    entries: list[RunnableScript] = []
    for name in sorted(raw_scripts.keys(), key=str.casefold):
        script_name = str(name).strip()
        if not script_name:
            continue
        command = f"{runner} run {script_name}"
        entries.append(RunnableScript(label=script_name, command=command))
    return entries


def _parse_pyproject_scripts(pyproject_path: Path) -> dict[str, RunnableScript]:
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    project = payload.get("project")
    if not isinstance(project, dict):
        return {}
    raw_scripts = project.get("scripts")
    if not isinstance(raw_scripts, dict):
        return {}
    entries: dict[str, RunnableScript] = {}
    for key in sorted(raw_scripts.keys(), key=str.casefold):
        name = str(key).strip()
        if not name:
            continue
        entries[f"project:{name}"] = RunnableScript(label=name, command=name)
    return entries


def _parse_hatch_scripts(pyproject_path: Path) -> dict[str, RunnableScript]:
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        return {}
    hatch = tool.get("hatch")
    if not isinstance(hatch, dict):
        return {}
    envs = hatch.get("envs")
    if not isinstance(envs, dict):
        return {}
    entries: dict[str, RunnableScript] = {}
    for env_name, env_payload in cast("dict[str, Any]", envs).items():
        env_dict = env_payload if isinstance(env_payload, dict) else None
        if env_dict is None:
            continue
        raw_scripts = env_dict.get("scripts")
        if not isinstance(raw_scripts, dict):
            continue
        for script_name in sorted(raw_scripts.keys(), key=str.casefold):
            name = str(script_name).strip()
            if not name:
                continue
            key = f"hatch:{env_name}:{name}"
            command = f"hatch run {env_name}:{name}"
            entries[key] = RunnableScript(label=f"{name} [{env_name}]", command=command)
    return entries


def _parse_python_file_scripts(root: Path) -> dict[str, RunnableScript]:
    entries: dict[str, RunnableScript] = {}
    candidate_files: list[Path] = []
    candidate_files.extend(
        sorted(root.glob("run_*.py"), key=lambda value: value.name.casefold())
    )
    for name in ["main.py", "__main__.py"]:
        path = root / name
        if path.is_file():
            candidate_files.append(path)

    seen: set[str] = set()
    for path in candidate_files:
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        label = path.name
        command = f'python "{path.name}"'
        entries[f"file:{label}"] = RunnableScript(label=label, command=command)
    return entries
