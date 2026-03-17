"""Shared terminal launcher configuration and runtime helpers."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
import time
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
    DEFAULT_TERMINAL_STARTUP_POSITION,
    TERMINAL_LAUNCHER_COMSPEC,
    TERMINAL_LAUNCHER_POWERSHELL5,
    TERMINAL_LAUNCHER_PWSH,
    TerminalLauncherId,
    TerminalStartupPosition,
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
    comspec_terminal_startup_position: TerminalStartupPosition = (
        DEFAULT_TERMINAL_STARTUP_POSITION
    )
    pwsh_terminal_executable: str = DEFAULT_PWSH_TERMINAL_EXECUTABLE
    pwsh_terminal_open_args_template: str = DEFAULT_PWSH_TERMINAL_OPEN_ARGS_TEMPLATE
    pwsh_terminal_command_args_template: str = (
        DEFAULT_PWSH_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    pwsh_terminal_startup_position: TerminalStartupPosition = (
        DEFAULT_TERMINAL_STARTUP_POSITION
    )
    powershell5_terminal_executable: str = DEFAULT_POWERSHELL5_TERMINAL_EXECUTABLE
    powershell5_terminal_open_args_template: str = (
        DEFAULT_POWERSHELL5_TERMINAL_OPEN_ARGS_TEMPLATE
    )
    powershell5_terminal_command_args_template: str = (
        DEFAULT_POWERSHELL5_TERMINAL_COMMAND_ARGS_TEMPLATE
    )
    powershell5_terminal_startup_position: TerminalStartupPosition = (
        DEFAULT_TERMINAL_STARTUP_POSITION
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
    active_settings = settings or _terminal_launcher_settings
    if os.name != "nt":
        _open_posix_terminal(folder, command=command)
        return
    launch_spec = build_windows_terminal_launch_spec(
        target_folder=folder,
        launcher_id=launcher_id,
        command=command,
        python_project=python_project,
        settings=active_settings,
    )
    resolved_launcher = launcher_id or active_settings.default_terminal_launcher
    startup_position = _startup_position(active_settings, resolved_launcher)
    startupinfo = _windows_startupinfo(startup_position)
    if startupinfo is None:
        process = subprocess.Popen(launch_spec)
    else:
        process = subprocess.Popen(launch_spec, startupinfo=startupinfo)
    _apply_windows_terminal_startup_position_async(process, startup_position)


def build_windows_terminal_launch_spec(
    *,
    target_folder: Path,
    launcher_id: TerminalLauncherId | None = None,
    command: str | None = None,
    python_project: bool = False,
    settings: TerminalLauncherSettings | None = None,
) -> str | list[str]:
    """Build the Windows `subprocess.Popen` launch value for one terminal request."""

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
    if resolved_launcher == TERMINAL_LAUNCHER_COMSPEC:
        return _build_comspec_command_line(
            executable=availability.resolved_executable,
            template=template,
            target_folder=folder,
            shell_command=shell_command,
        )
    rendered_args = _render_windows_args_template(
        template=template,
        launcher_id=resolved_launcher,
        target_folder=folder,
        shell_command=shell_command,
    )
    return [availability.resolved_executable, *rendered_args]


def build_windows_terminal_launch_argv(
    *,
    target_folder: Path,
    launcher_id: TerminalLauncherId | None = None,
    command: str | None = None,
    python_project: bool = False,
    settings: TerminalLauncherSettings | None = None,
) -> list[str]:
    """Build the Windows process argv for a terminal launch request."""

    launch_spec = build_windows_terminal_launch_spec(
        target_folder=target_folder,
        launcher_id=launcher_id,
        command=command,
        python_project=python_project,
        settings=settings,
    )
    if isinstance(launch_spec, str):
        raise RuntimeError(
            "Command Prompt launches require an exact command line. "
            "Use build_windows_terminal_launch_spec()."
        )
    return launch_spec


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


def _build_comspec_command_line(
    *,
    executable: str,
    template: str,
    target_folder: Path,
    shell_command: str,
) -> str:
    """Build the exact `cmd.exe` command line required by `%ComSpec%` launches."""

    rendered_args = _render_windows_template_text(
        template=template,
        launcher_id=TERMINAL_LAUNCHER_COMSPEC,
        target_folder=target_folder,
        shell_command=shell_command,
    )
    command_parts = [subprocess.list2cmdline([executable])]
    if rendered_args:
        command_parts.append(rendered_args)
    return " ".join(command_parts)


def _render_windows_template_text(
    *,
    template: str,
    launcher_id: TerminalLauncherId,
    target_folder: Path,
    shell_command: str,
) -> str:
    """Render one persisted Windows template into plain command-line text."""

    return (
        str(template)
        .replace("{folder}", _folder_token(launcher_id, Path(target_folder)))
        .replace("{shell_command}", shell_command)
        .strip()
    )


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


def _startup_position(
    settings: TerminalLauncherSettings,
    launcher_id: TerminalLauncherId,
) -> TerminalStartupPosition:
    """Return the configured startup position for one launcher."""

    if launcher_id == TERMINAL_LAUNCHER_COMSPEC:
        return settings.comspec_terminal_startup_position
    if launcher_id == TERMINAL_LAUNCHER_PWSH:
        return settings.pwsh_terminal_startup_position
    return settings.powershell5_terminal_startup_position


def _windows_startupinfo(
    startup_position: TerminalStartupPosition,
) -> subprocess.STARTUPINFO | None:
    """Build Windows-specific startup info for one terminal launch."""

    if startup_position not in {"maximized", "minimized"}:
        return None
    startupinfo_type = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_type is None:
        return None
    startupinfo = startupinfo_type()
    startupinfo.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 1))
    startupinfo.wShowWindow = 3 if startup_position == "maximized" else 2
    return startupinfo


def _apply_windows_terminal_startup_position_async(
    process: object,
    startup_position: TerminalStartupPosition,
) -> None:
    """Apply best-effort post-launch terminal window placement on Windows."""

    if os.name != "nt" or startup_position == "normal":
        return
    process_id = getattr(process, "pid", None)
    if not isinstance(process_id, int) or process_id <= 0:
        return
    worker = threading.Thread(
        target=_apply_windows_terminal_startup_position_worker,
        args=(process_id, startup_position),
        daemon=True,
    )
    worker.start()


def _apply_windows_terminal_startup_position_worker(
    process_id: int,
    startup_position: TerminalStartupPosition,
) -> None:
    """Wait for a launched terminal window and apply its target placement."""

    window_handle = _wait_for_main_window(process_id)
    if window_handle is None:
        return
    if startup_position == "maximized":
        _show_window(window_handle, 3)
        return
    if startup_position == "minimized":
        _show_window(window_handle, 2)
        return
    rect = _startup_rect_for_window(window_handle, startup_position)
    if rect is None:
        return
    _show_window(window_handle, 9)
    _set_window_rect(window_handle, rect)


def _wait_for_main_window(process_id: int) -> int | None:
    """Return the first visible top-level window for a process."""

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        window_handle = _find_main_window(process_id)
        if window_handle is not None:
            return window_handle
        time.sleep(0.05)
    return None


def _find_main_window(process_id: int) -> int | None:
    """Find the main visible top-level window for one process id."""

    from ctypes import WINFUNCTYPE, WinDLL, byref, c_bool
    from ctypes.wintypes import BOOL, DWORD, HWND, LPARAM

    user32 = WinDLL("user32", use_last_error=True)
    found_window: int | None = None

    @WINFUNCTYPE(BOOL, HWND, LPARAM)
    def _callback(window_handle: int, _lparam: int) -> bool:
        nonlocal found_window
        pid = DWORD(0)
        user32.GetWindowThreadProcessId(HWND(window_handle), byref(pid))
        if pid.value != process_id:
            return True
        if not c_bool(user32.IsWindowVisible(HWND(window_handle))).value:
            return True
        if int(user32.GetWindow(HWND(window_handle), 4)) != 0:
            return True
        found_window = int(window_handle)
        return False

    user32.EnumWindows(_callback, 0)
    return found_window


def _show_window(window_handle: int, command: int) -> None:
    """Apply one Win32 show-state command to a top-level window."""

    from ctypes import WinDLL
    from ctypes.wintypes import HWND

    user32 = WinDLL("user32", use_last_error=True)
    user32.ShowWindow(HWND(window_handle), command)


def _startup_rect_for_window(
    window_handle: int,
    startup_position: TerminalStartupPosition,
) -> tuple[int, int, int, int] | None:
    """Return the target rectangle for side-of-screen startup positions."""

    if startup_position not in {"left_of_screen", "right_of_screen"}:
        return None
    work_area = _monitor_work_area(window_handle)
    if work_area is None:
        return None
    left, top, right, bottom = work_area
    width = right - left
    height = bottom - top
    half_width = max(1, width // 2)
    if startup_position == "left_of_screen":
        return (left, top, half_width, height)
    return (left + half_width, top, width - half_width, height)


def _monitor_work_area(window_handle: int) -> tuple[int, int, int, int] | None:
    """Return the working area for the monitor nearest one window."""

    import ctypes
    from ctypes import WinDLL, byref
    from ctypes.wintypes import DWORD, HWND, RECT

    class _MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", DWORD),
        ]

    user32 = WinDLL("user32", use_last_error=True)
    monitor_handle = user32.MonitorFromWindow(HWND(window_handle), 2)
    if monitor_handle == 0:
        return None
    monitor_info = _MonitorInfo()
    monitor_info.cbSize = DWORD(ctypes.sizeof(_MonitorInfo))
    if not user32.GetMonitorInfoW(monitor_handle, byref(monitor_info)):
        return None
    work = monitor_info.rcWork
    return (int(work.left), int(work.top), int(work.right), int(work.bottom))


def _set_window_rect(window_handle: int, rect: tuple[int, int, int, int]) -> None:
    """Move and resize one top-level window to the requested rectangle."""

    from ctypes import WinDLL
    from ctypes.wintypes import HWND

    x, y, width, height = rect
    user32 = WinDLL("user32", use_last_error=True)
    user32.SetWindowPos(
        HWND(window_handle),
        0,
        x,
        y,
        width,
        height,
        0x0004 | 0x0010 | 0x0040,
    )


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
