"""External file-manager launch helpers for source and target pane actions."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from PySide6.QtWidgets import QMessageBox
from threep_commons.executables import resolve_executable_path
from threep_commons.subprocess_helpers import (
    merge_subprocess_kwargs,
    windows_no_window_popen_kwargs,
)

if TYPE_CHECKING:
    from pathlib import Path

    from .panel_widget import PanelWidget
    from .window import ExplorerWindow


DEFAULT_TOTAL_COMMANDER_EXECUTABLE = "TOTALCMD64.EXE"
TOTAL_COMMANDER_DISCOVERY_CANDIDATES = (
    DEFAULT_TOTAL_COMMANDER_EXECUTABLE,
    "TOTALCMD.EXE",
)
DEFAULT_TOTAL_COMMANDER_SOURCE_ARGS_TEMPLATE = "/O /A /L={source}"
DEFAULT_TOTAL_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE = "/O /A /L={source} /R={target}"

DEFAULT_DOUBLE_COMMANDER_EXECUTABLE = "doublecmd.exe"
DOUBLE_COMMANDER_DISCOVERY_CANDIDATES = (DEFAULT_DOUBLE_COMMANDER_EXECUTABLE,)
DEFAULT_DOUBLE_COMMANDER_SOURCE_ARGS_TEMPLATE = "-C -L {source}"
DEFAULT_DOUBLE_COMMANDER_SOURCE_TARGET_ARGS_TEMPLATE = "-C -L {source} -R {target}"

type LaunchTargetKind = Literal["directory", "file"]


@dataclass(frozen=True)
class FileManagerLaunchTarget:
    """Describe the effective path target used for one launcher invocation."""

    path: Path
    kind: LaunchTargetKind


class ExternalFileManagerLauncher:
    """Launch Explorer, Total Commander, and Double Commander for window panes."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Store the owning window for pane and settings lookups."""

        self._window = window

    def total_commander_available(self) -> bool:
        """Return whether Total Commander currently resolves to an executable."""

        return self._resolved_total_commander_executable() is not None

    def double_commander_available(self) -> bool:
        """Return whether Double Commander currently resolves to an executable."""

        return self._resolved_double_commander_executable() is not None

    def has_target_panel(self) -> bool:
        """Return whether the current window has a resolved target pane."""

        return self._target_panel() is not None

    def launch_explorer_source(self) -> None:
        """Launch Windows Explorer for the active source pane."""

        source_target = self._source_target()
        if source_target is None:
            return
        self._launch_explorer_target(source_target)

    def launch_explorer_source_target(self) -> None:
        """Launch Windows Explorer for source and target panes."""

        pane_targets = self._source_and_target_targets()
        if pane_targets is None:
            return
        source_target, target_target = pane_targets
        self._launch_explorer_target(source_target)
        self._launch_explorer_target(target_target)

    def launch_total_commander_source(self) -> None:
        """Launch Total Commander for the active source pane."""

        source_target = self._source_target()
        if source_target is None:
            return
        self._launch_external_manager(
            executable=self._resolved_total_commander_executable(),
            template=self._window.settings.total_commander_source_args_template,
            source=source_target,
            target=None,
            tool_name="Total Commander",
        )

    def launch_total_commander_source_target(self) -> None:
        """Launch Total Commander for source and target panes."""

        pane_targets = self._source_and_target_targets()
        if pane_targets is None:
            return
        source_target, target_target = pane_targets
        self._launch_external_manager(
            executable=self._resolved_total_commander_executable(),
            template=self._window.settings.total_commander_source_target_args_template,
            source=source_target,
            target=target_target,
            tool_name="Total Commander",
        )

    def launch_double_commander_source(self) -> None:
        """Launch Double Commander for the active source pane."""

        source_target = self._source_target()
        if source_target is None:
            return
        self._launch_external_manager(
            executable=self._resolved_double_commander_executable(),
            template=self._window.settings.double_commander_source_args_template,
            source=source_target,
            target=None,
            tool_name="Double Commander",
        )

    def launch_double_commander_source_target(self) -> None:
        """Launch Double Commander for source and target panes."""

        pane_targets = self._source_and_target_targets()
        if pane_targets is None:
            return
        source_target, target_target = pane_targets
        self._launch_external_manager(
            executable=self._resolved_double_commander_executable(),
            template=self._window.settings.double_commander_source_target_args_template,
            source=source_target,
            target=target_target,
            tool_name="Double Commander",
        )

    def effective_panel_target(
        self,
        panel: PanelWidget,
    ) -> FileManagerLaunchTarget:
        """Resolve the effective launch target for one pane."""

        tab = panel.current_tab()
        if tab is None:
            return FileManagerLaunchTarget(panel.current_path(), "directory")
        selected_paths = tab.selected_paths()
        if len(selected_paths) != 1:
            return FileManagerLaunchTarget(panel.current_path(), "directory")
        selected_path = selected_paths[0]
        if selected_path.is_dir():
            return FileManagerLaunchTarget(selected_path, "directory")
        if selected_path.exists():
            return FileManagerLaunchTarget(selected_path, "file")
        return FileManagerLaunchTarget(panel.current_path(), "directory")

    def _source_target(self) -> FileManagerLaunchTarget | None:
        """Return the active source-pane launch target, if available."""

        source_panel = self._window.panels_coordinator.active_panel()
        if source_panel is None:
            return None
        return self.effective_panel_target(source_panel)

    def _source_and_target_targets(
        self,
    ) -> tuple[FileManagerLaunchTarget, FileManagerLaunchTarget] | None:
        """Return source and target launch targets when both panes exist."""

        source_panel = self._window.panels_coordinator.active_panel()
        target_panel = self._target_panel()
        if source_panel is None or target_panel is None:
            return None
        return (
            self.effective_panel_target(source_panel),
            self.effective_panel_target(target_panel),
        )

    def _target_panel(self) -> PanelWidget | None:
        """Return the resolved target panel for the active source panel."""

        from .ui.window.panels import resolve_window_target_panel_id

        source_panel_id = self._window.active_panel_id
        if source_panel_id is None:
            return None
        target_panel_id = resolve_window_target_panel_id(self._window, source_panel_id)
        if target_panel_id is None:
            return None
        return self._window.panel_widgets.get(target_panel_id)

    def _launch_explorer_target(self, target: FileManagerLaunchTarget) -> None:
        """Launch Windows Explorer for one target path."""

        if target.kind == "file":
            args = ["explorer.exe", f"/select,{target.path}"]
        else:
            args = ["explorer.exe", str(target.path)]
        self._launch_process(args, tool_name="Explorer")

    def _launch_external_manager(
        self,
        *,
        executable: Path | None,
        template: str,
        source: FileManagerLaunchTarget,
        target: FileManagerLaunchTarget | None,
        tool_name: str,
    ) -> None:
        """Launch one external file manager from the configured template."""

        if executable is None:
            QMessageBox.warning(
                self._window,
                tool_name,
                f"{tool_name} is not configured or could not be found in PATH.",
            )
            return
        args = expand_external_manager_args(
            template,
            source=source.path,
            target=target.path if target is not None else None,
        )
        self._launch_process([str(executable), *args], tool_name=tool_name)

    def _launch_process(self, args: list[str], *, tool_name: str) -> None:
        """Launch one detached external process or show an error dialog."""

        try:
            subprocess.Popen(
                args,
                **merge_subprocess_kwargs(windows_no_window_popen_kwargs()),
            )
        except OSError as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(
                self._window,
                f"{tool_name} Launch Failed",
                str(exc),
            )

    def _resolved_total_commander_executable(self) -> Path | None:
        """Resolve the current Total Commander executable path."""

        return resolve_executable_path(self._window.settings.total_commander_executable)

    def _resolved_double_commander_executable(self) -> Path | None:
        """Resolve the current Double Commander executable path."""

        return resolve_executable_path(
            self._window.settings.double_commander_executable
        )


def expand_external_manager_args(
    template: str,
    *,
    source: Path,
    target: Path | None,
) -> list[str]:
    """Expand a file-manager args template into subprocess argv tokens."""

    tokens = shlex.split(str(template or "").strip(), posix=False)
    replacements = {
        "{source}": str(source),
        "{target}": str(target) if target is not None else "",
    }
    expanded: list[str] = []
    for token in tokens:
        rendered = token
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)
        if rendered:
            expanded.append(rendered)
    return expanded
