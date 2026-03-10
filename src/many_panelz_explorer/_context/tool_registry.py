from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._settings.models import UiPreferences


@dataclass(frozen=True)
class ContextTool:
    key: str
    label: str
    exe_path: str
    args_template: str
    resolved_executable: str | None
    error: str | None

    @property
    def is_available(self) -> bool:
        return bool(self.resolved_executable)


class ContextToolRegistry:
    def __init__(self, preferences: UiPreferences) -> None:
        self._preferences = preferences

    def resolve(self, key: str) -> ContextTool:
        normalized = str(key).strip().lower()
        if normalized == "code_editor":
            label = "Code Editor"
            exe_path = self._preferences.context_tool_code_editor_exe_path
            args_template = self._preferences.context_tool_code_editor_args_template
        elif normalized == "git_gui":
            label = "Git GUI"
            exe_path = self._preferences.context_tool_git_gui_exe_path
            args_template = self._preferences.context_tool_git_gui_args_template
        else:
            return ContextTool(
                key=normalized,
                label=normalized,
                exe_path="",
                args_template="",
                resolved_executable=None,
                error=f"Unknown tool key: {normalized}",
            )
        resolved, error = _resolve_executable_path(exe_path)
        return ContextTool(
            key=normalized,
            label=label,
            exe_path=exe_path,
            args_template=args_template,
            resolved_executable=resolved,
            error=error,
        )


def expand_tool_args(
    args_template: str,
    *,
    folder: Path | None = None,
    file: Path | None = None,
    files: list[Path] | None = None,
    project_root: Path | None = None,
) -> list[str]:
    files_list = [Path(item) for item in (files or [])]
    rendered = str(args_template or "")
    rendered = rendered.replace("{folder}", _quote(folder))
    rendered = rendered.replace("{file}", _quote(file))
    rendered = rendered.replace(
        "{files}", " ".join(_quote(path) for path in files_list if str(path).strip())
    )
    rendered = rendered.replace("{project_root}", _quote(project_root))
    rendered = rendered.strip()
    if not rendered:
        return []
    try:
        return shlex.split(rendered, posix=os.name != "nt")
    except ValueError:
        return [rendered]


def _resolve_executable_path(raw: str) -> tuple[str | None, str | None]:
    value = str(raw or "").strip()
    if not value:
        return None, "Configure this tool path in Settings."
    candidate = Path(value)
    if candidate.is_absolute() or ("\\" in value or "/" in value):
        if candidate.exists():
            return str(candidate), None
        return None, f"Configured executable does not exist: {value}"
    hit = shutil.which(value)
    if hit:
        return str(Path(hit)), None
    return None, f"Configured executable was not found in PATH: {value}"


def _quote(path: Path | None) -> str:
    if path is None:
        return ""
    text = str(path).strip()
    if not text:
        return ""
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'
