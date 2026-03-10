from __future__ import annotations

from pathlib import Path

from many_panelz_explorer._context.tool_registry import (
    ContextToolRegistry,
    expand_tool_args,
)
from many_panelz_explorer._settings.models import UiPreferences


def test_empty_tool_path_is_unavailable() -> None:
    preferences = UiPreferences(
        context_tool_code_editor_exe_path="",
        context_tool_code_editor_args_template="{folder}",
    )
    tool = ContextToolRegistry(preferences).resolve("code_editor")
    assert tool.is_available is False
    assert tool.error is not None


def test_expand_tool_args_replaces_placeholders() -> None:
    folder = Path(r"C:\work\proj")
    file_path = Path(r"C:\work\proj\pyproject.toml")
    args = expand_tool_args(
        "--folder {folder} --file {file} --root {project_root}",
        folder=folder,
        file=file_path,
        project_root=folder,
    )
    assert "--folder" in args
    assert f'"{folder}"' in args
    assert f'"{file_path}"' in args
