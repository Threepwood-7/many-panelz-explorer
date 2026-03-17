"""Shared terminal launcher configuration and runtime helpers."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ._operations.discovery import resolve_terminal_launcher_path
from ._operations.types import (
    DEFAULT_COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE,
    DEFAULT_COMSPEC_TERMINAL_EXECUTABLE,
    DEFAULT_COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE,
    DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE,
    DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE,
    DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE,
    DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE,
    DEFAULT_PWSH_TERMINAL_EXECUTABLE,
    DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE,
    DEFAULT_TERMINAL_LAUNCHER,
    TERMINAL_LAUNCHER_COMSPEC,
    TERMINAL_LAUNCHER_POWERSHELL5,
    TERMINAL_LAUNCHER_PWSH,
    TerminalLauncherId,
)


def terminal_launcher_label(launcher_id: TerminalLauncherId) -> str:
    """Return the user-facing label for one terminal launcher."""

    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return "Command Prompt (%ComSpec%)"
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return "PowerShell 7"
    return "Windows PowerShell 5.1"


@dataclass(frozen=True)
class TerminalLauncherSettings:
    """Persisted launcher preferences used by terminal entry points."""

    default_terminal_launcher: TerminalLauncherId = DEFAULT_TERMINAL_LAUNCHER
    comspec_terminal_executable: str = DEFAULT_COMSPEC_TERMINAL_EXECUTABLE
    comspec_terminal_open_args_template: str = (
        DEFAULT_COMSPEC_TERMINAL_OPEN_ARGS_TEMPLATE
    )
    comspec_terminal_command_args_template: str = (
        DEFAULT_COMSPEC_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    pwsh_terminal_executable: str = DEFAULT_PWSH_TERMINAL_EXECUTABLE
    pwsh_terminal_open_args_template: str = DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE
    pwsh_terminal_command_args_template: str = (
        DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    powershell5_terminal_executable: str = DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE
    powershell5_terminal_open_args_template: str = (
        DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE
    )
    powershell5_terminal_command_args_template: str = (
        DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE
    )


@dataclass(frozen=True)
class TerminalLauncherAvailability:
    """Describe whether a launcher can be used right now."""

    launcher_id: TerminalLauncherId
    label: str
    configured_executable: str
    resolved_executable: str
    error: str

    @property
    def is_available(self) -> bool:
        """Return whether the launcher resolved to a usable executable."""

        return bool(self.resolved_executable)


_terminal_launcher_settings = TerminalLauncherSettings()


def configure_terminal_launchers(settings: TerminalLauncherSettings) -> None:
    """Replace the active shared terminal-launcher settings."""

    global _terminal_launcher_settings
    _terminal_launcher_settings = settings


def current_terminal_launcher_settings() -> TerminalLauncherSettings:
    """Return the active shared terminal-launcher settings."""

    return _terminal_launcher_settings


def terminal_launcher_availability(
    launcher_id: TerminalLauncherId,
    *,
    settings: TerminalLauncherSettings | None = None,
) -> TerminalLauncherAvailability:
    """Resolve one launcher against the current machine state."""

    active_settings = settings or _terminal_launcher_settings
    configured_executable = _configured_executable(active_settings, launcher_id)
    resolved = resolve_terminal_launcher_path(
        launcher_id=launcher_id,
        configured_executable=configured_executable,
    )
    label = terminal_launcher_label(launcher_id)
    if resolved:
        return TerminalLauncherAvailability(
            launcher_id=launcher_id,
            label=label,
            configured_executable=configured_executable,
            resolved_executable=resolved,
            error="",
        )
    requested = configured_executable or _default_executable(launcher_id)
    return TerminalLauncherAvailability(
        launcher_id=launcher_id,
        label=label,
        configured_executable=configured_executable,
        resolved_executable="",
        error=f"Configured executable is unavailable: {requested}",
    )


def available_terminal_launchers(
    *,
    settings: TerminalLauncherSettings | None = None,
) -> list[TerminalLauncherAvailability]:
    """Resolve all supported launchers for menu and diagnostics use."""

    active_settings = settings or _terminal_launcher_settings
    return [
        terminal_launcher_availability(
            TERMINAL_LAUNCHER_COMSPEC,
            settings=active_settings,
        ),
        terminal_launcher_availability(
            TERMINAL_LAUNCHER_PWSH,
            settings=active_settings,
        ),
        terminal_launcher_availability(
            TERMINAL_LAUNCHER_POWERSHELL5,
            settings=active_settings,
        ),
    ]


def open_terminal(
    target_folder: Path,
    *,
    launcher_id: TerminalLauncherId | None = None,
    command: str | None = None,
    python_project: bool = False,
    settings: TerminalLauncherSettings | None = None,
) -> None:
    """Open a terminal at one folder using the configured shared launcher."""

    folder = Path(target_folder)
    if os.name != "nt":
        _open_posix_terminal(folder, command=command)
        return
    argv = build_windows_terminal_launch_argv(
        target_folder=folder,
        launcher_id=launcher_id,
        command=command,
        python_project=python_project,
        settings=settings,
    )
    subprocess.Popen(argv)


def build_windows_terminal_launch_argv(
    *,
    target_folder: Path,
    launcher_id: TerminalLauncherId | None = None,
    command: str | None = None,
    python_project: bool = False,
    settings: TerminalLauncherSettings | None = None,
) -> list[str]:
    """Build the Windows process argv for a terminal launch request."""

    active_settings = settings or _terminal_launcher_settings
    resolved_launcher = launcher_id or active_settings.default_terminal_launcher
    availability = terminal_launcher_availability(
        resolved_launcher,
        settings=active_settings,
    )
    if not availability.is_available:
        raise RuntimeError(f"{availability.label} is unavailable. {availability.error}")
    folder = Path(target_folder)
    if command:
        shell_command = build_terminal_shell_command(
            launcher_id=resolved_launcher,
            target_folder=folder,
            command=command,
            python_project=python_project,
        )
        template = _command_args_template(active_settings, resolved_launcher)
    else:
        shell_command = ""
        template = _open_args_template(active_settings, resolved_launcher)
    rendered_args = _render_windows_args_template(
        template=template,
        launcher_id=resolved_launcher,
        target_folder=folder,
        shell_command=shell_command,
    )
    return [availability.resolved_executable, *rendered_args]


def build_terminal_shell_command(
    *,
    launcher_id: TerminalLauncherId,
    target_folder: Path,
    command: str,
    python_project: bool = False,
) -> str:
    """Build the shell command that changes folders and runs one command."""

    folder = Path(target_folder)
    command_text = str(command or "").strip()
    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        parts = [f"cd /d {_quote_cmd_path(folder)}"]
        if python_project:
            activate_path = folder / ".venv" / "Scripts" / "activate.bat"
            if activate_path.is_file():
                parts.append(f"call {_quote_cmd_path(activate_path)}")
        if command_text:
            parts.append(command_text)
        return " && ".join(parts)

    parts = [f"Set-Location -LiteralPath {_quote_powershell_path(folder)}"]
    if python_project:
        activate_path = folder / ".venv" / "Scripts" / "Activate.ps1"
        if activate_path.is_file():
            parts.append(f". {_quote_powershell_path(activate_path)}")
    if command_text:
        parts.append(command_text)
    return "; ".join(parts)


def _render_windows_args_template(
    *,
    template: str,
    launcher_id: TerminalLauncherId,
    target_folder: Path,
    shell_command: str,
) -> list[str]:
    """Render one persisted Windows args template into an argv suffix."""

    tokens = _split_windows_args_template(template)
    folder_token = _folder_token(launcher_id, Path(target_folder))
    rendered: list[str] = []
    for token in tokens:
        value = token.replace("{folder}", folder_token).replace(
            "{shell_command}", shell_command
        )
        if value:
            rendered.append(value)
    return rendered


def _split_windows_args_template(template: str) -> list[str]:
    """Split a stored Windows args template into shell-style tokens."""

    text = str(template or "").strip()
    if not text:
        return []
    try:
        return shlex.split(text, posix=False)
    except ValueError:
        return [text]


def _folder_token(launcher_id: TerminalLauncherId, target_folder: Path) -> str:
    """Return the template token replacement for one folder path."""

    folder = Path(target_folder)
    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return _quote_cmd_path(folder)
    return _quote_powershell_path(folder)


def _configured_executable(
    settings: TerminalLauncherSettings,
    launcher_id: TerminalLauncherId,
) -> str:
    """Return the configured executable text for one launcher."""

    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return settings.comspec_terminal_executable
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return settings.pwsh_terminal_executable
    return settings.powershell5_terminal_executable


def _open_args_template(
    settings: TerminalLauncherSettings,
    launcher_id: TerminalLauncherId,
) -> str:
    """Return the open-template args string for one launcher."""

    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return settings.comspec_terminal_open_args_template
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return settings.pwsh_terminal_open_args_template
    return settings.powershell5_terminal_open_args_template


def _command_args_template(
    settings: TerminalLauncherSettings,
    launcher_id: TerminalLauncherId,
) -> str:
    """Return the command-template args string for one launcher."""

    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return settings.comspec_terminal_command_args_template
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return settings.pwsh_terminal_command_args_template
    return settings.powershell5_terminal_command_args_template


def _default_executable(launcher_id: TerminalLauncherId) -> str:
    """Return the built-in default executable text for one launcher."""

    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return DEFAULT_COMSPEC_TERMINAL_EXECUTABLE
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return DEFAULT_PWSH_TERMINAL_EXECUTABLE
    return DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE


def _quote_cmd_path(path: Path) -> str:
    """Quote a filesystem path for use in `cmd.exe` commands."""

    escaped = str(path).replace('"', '""')
    return f'"{escaped}"'


def _quote_powershell_path(path: Path) -> str:
    """Quote a filesystem path for use in PowerShell commands."""

    escaped = str(path).replace("'", "''")
    return f"'{escaped}'"


def _open_posix_terminal(target_folder: Path, command: str | None = None) -> None:
    """Keep the existing POSIX launcher fallback behavior unchanged."""

    folder = Path(target_folder)
    if command:
        if shutil.which("x-terminal-emulator"):
            subprocess.Popen(
                [
                    "x-terminal-emulator",
                    "--working-directory",
                    str(folder),
                    "-e",
                    "sh",
                    "-lc",
                    f"{command}; exec sh",
                ]
            )
            return
        subprocess.Popen(["sh", "-lc", command], cwd=folder)
        return
    if shutil.which("x-terminal-emulator"):
        subprocess.Popen(["x-terminal-emulator", "--working-directory", str(folder)])
        return
    raise RuntimeError("No terminal launcher configured for this platform")
