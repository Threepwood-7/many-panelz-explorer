from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from PySide6.QtCore import QObject, Signal
from send2trash import send2trash

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


OperationKind = Literal["copy", "move", "delete"]
OperationStatus = Literal[
    "queued",
    "running",
    "dispatched",
    "succeeded",
    "failed",
    "cancelled",
]
OperationDispatchMode = Literal["queue", "launch_now_no_wait", "run_now_wait"]
OperationConflictPolicy = Literal["overwrite", "skip", "rename", "cancel"]
CopyMoveBackendId = Literal[
    "python_builtin",
    "windows_explorer",
    "robocopy",
    "teracopy",
    "unstoppable",
    "external_copymove",
]
DeleteBackendId = Literal[
    "recycle_bin",
    "permanent_native",
    "cmd_delete",
    "powershell_delete",
    "rimraf",
    "external_delete",
]
OperationBackendId = CopyMoveBackendId | DeleteBackendId

DISPATCH_MODE_QUEUE: OperationDispatchMode = "queue"
DISPATCH_MODE_LAUNCH_NO_WAIT: OperationDispatchMode = "launch_now_no_wait"
DISPATCH_MODE_RUN_WAIT: OperationDispatchMode = "run_now_wait"

SHORTCUT_BEHAVIOR_DIRECT: str = "direct_enqueue"
SHORTCUT_BEHAVIOR_DIALOG: str = "always_dialog"

QUEUE_VIEW_DOCK: str = "dock_tab"
QUEUE_VIEW_FLOATING: str = "floating_window"
QUEUE_VIEW_BOTH: str = "both"

BACKEND_PYTHON: CopyMoveBackendId = "python_builtin"
BACKEND_EXPLORER: CopyMoveBackendId = "windows_explorer"
BACKEND_ROBOCOPY: CopyMoveBackendId = "robocopy"
BACKEND_TERACOPY: CopyMoveBackendId = "teracopy"
BACKEND_UNSTOPPABLE: CopyMoveBackendId = "unstoppable"
BACKEND_EXTERNAL_COPYMOVE: CopyMoveBackendId = "external_copymove"

BACKEND_RECYCLE_BIN: DeleteBackendId = "recycle_bin"
BACKEND_PERMANENT_NATIVE: DeleteBackendId = "permanent_native"
BACKEND_CMD_DELETE: DeleteBackendId = "cmd_delete"
BACKEND_POWERSHELL_DELETE: DeleteBackendId = "powershell_delete"
BACKEND_RIMRAF: DeleteBackendId = "rimraf"
BACKEND_EXTERNAL_DELETE: DeleteBackendId = "external_delete"

DEFAULT_TERA_COPY_EXE = "TeraCopy.exe"
DEFAULT_TERA_COPY_ARGS = "{operation} {sources} {target}"
DEFAULT_UNSTOPPABLE_EXE = "UnstoppableCopier.exe"
DEFAULT_UNSTOPPABLE_ARGS = "{operation} {sources} {target}"
DEFAULT_GENERIC_COPYMOVE_EXE = ""
DEFAULT_GENERIC_COPYMOVE_ARGS = "{operation} {sources} {target}"
DEFAULT_GENERIC_DELETE_EXE = ""
DEFAULT_GENERIC_DELETE_ARGS = "{operation} {sources}"
DEFAULT_ROBOCOPY_COPY_ARGS = "/E /R:0 /W:0 /NFL /NDL /NJH /NJS /NP"
DEFAULT_ROBOCOPY_MOVE_ARGS = "/E /MOVE /R:0 /W:0 /NFL /NDL /NJH /NJS /NP"
DEFAULT_CMD_DELETE_ARGS = "/Q"
DEFAULT_POWERSHELL_DELETE_ARGS = "-Force"
DEFAULT_RIMRAF_EXE = "rimraf"
DEFAULT_RIMRAF_ARGS = ""
COMPANION_TOOL_NOT_FOUND = "<not-found>"
DEFAULT_SYSTEM_CMD_FALLBACK = r"C:\Windows\System32\cmd.exe"
DEFAULT_SYSTEM_ROBOCOPY_FALLBACK = r"C:\Windows\System32\robocopy.exe"


@dataclass(frozen=True)
class OperationExecutionPreferences:
    default_copy_move_backend: str = BACKEND_PYTHON
    default_delete_backend: str = BACKEND_RECYCLE_BIN
    default_dispatch_mode: str = DISPATCH_MODE_QUEUE
    default_conflict_policy: str = "rename"
    shortcut_behavior: str = SHORTCUT_BEHAVIOR_DIRECT
    queue_view_mode: str = QUEUE_VIEW_DOCK
    default_editor_executable: str = ""
    default_viewer_executable: str = ""
    file_open_overrides_json: str = "{}"
    use_extended_paths_robocopy: bool = False
    use_extended_paths_teracopy: bool = False
    use_extended_paths_unstoppable: bool = False
    use_extended_paths_external_copymove: bool = False
    use_extended_paths_cmd_delete: bool = False
    use_extended_paths_powershell_delete: bool = False
    use_extended_paths_rimraf: bool = False
    use_extended_paths_external_delete: bool = False
    script_editor_executable: str = ""
    teracopy_executable: str = DEFAULT_TERA_COPY_EXE
    teracopy_args_template: str = DEFAULT_TERA_COPY_ARGS
    unstoppable_executable: str = DEFAULT_UNSTOPPABLE_EXE
    unstoppable_args_template: str = DEFAULT_UNSTOPPABLE_ARGS
    generic_copymove_executable: str = DEFAULT_GENERIC_COPYMOVE_EXE
    generic_copymove_args_template: str = DEFAULT_GENERIC_COPYMOVE_ARGS
    generic_delete_executable: str = DEFAULT_GENERIC_DELETE_EXE
    generic_delete_args_template: str = DEFAULT_GENERIC_DELETE_ARGS
    robocopy_copy_args: str = DEFAULT_ROBOCOPY_COPY_ARGS
    robocopy_move_args: str = DEFAULT_ROBOCOPY_MOVE_ARGS
    cmd_delete_args: str = DEFAULT_CMD_DELETE_ARGS
    powershell_delete_args: str = DEFAULT_POWERSHELL_DELETE_ARGS
    rimraf_executable: str = DEFAULT_RIMRAF_EXE
    rimraf_args_template: str = DEFAULT_RIMRAF_ARGS
    resolved_cmd_path: str = DEFAULT_SYSTEM_CMD_FALLBACK
    resolved_robocopy_path: str = DEFAULT_SYSTEM_ROBOCOPY_FALLBACK


@dataclass(frozen=True)
class OperationRequest:
    kind: OperationKind
    sources: tuple[Path, ...]
    target_dir: Path | None
    backend_id: str
    dispatch_mode: str
    conflict_policy: str
    backend_options: dict[str, str] = field(default_factory=dict)
    created_by: str = "unknown"


@dataclass(frozen=True)
class OperationResult:
    status: OperationStatus
    message: str
    processed_count: int = 0
    pid: int | None = None


@dataclass(frozen=True)
class OperationArtifacts:
    job_dir: Path
    metadata_path: Path
    log_path: Path
    script_path: Path | None = None


@dataclass(frozen=True)
class OperationJob:
    job_id: str
    request: OperationRequest
    status: OperationStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str = ""
    artifacts: OperationArtifacts | None = None
    pid: int | None = None
    processed_count: int = 0
    cancel_requested: bool = False

    def summary(self) -> str:
        source_count = len(self.request.sources)
        if self.request.kind == "delete":
            return f"Delete {source_count} item(s)"
        target = str(self.request.target_dir) if self.request.target_dir is not None else "(none)"
        verb = "Copy" if self.request.kind == "copy" else "Move"
        return f"{verb} {source_count} item(s) to {target}"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_path(path: Path | str) -> Path:
    return Path(path).expanduser()


def to_windows_long_path(path: Path | str) -> str:
    raw = str(_normalize_path(path))
    if os.name != "nt":
        return raw
    if raw.startswith("\\\\?\\"):
        return raw
    absolute = os.path.abspath(raw)
    if absolute.startswith("\\\\"):
        return f"\\\\?\\UNC\\{absolute[2:]}"
    return f"\\\\?\\{absolute}"


def to_windows_arg_path(path: Path | str, *, use_extended_paths: bool) -> str:
    raw = str(_normalize_path(path))
    if os.name != "nt":
        return raw
    if use_extended_paths:
        return to_windows_long_path(raw)
    if raw.startswith("\\\\?\\"):
        return _display_path(raw)
    return os.path.abspath(raw)


def _resolve_use_extended_paths(
    request: OperationRequest,
    *,
    default: bool,
) -> bool:
    _ = request
    return bool(default)


def _display_path(path: Path | str) -> str:
    raw = str(path)
    if raw.startswith("\\\\?\\UNC\\"):
        return f"\\\\{raw[8:]}"
    if raw.startswith("\\\\?\\"):
        return raw[4:]
    return raw


def _quoted(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def _split_args(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(" ") if part.strip()]


def _is_success_robocopy_exit_code(code: int) -> bool:
    return int(code) <= 7


def _safe_target(destination: Path, source_name: str) -> Path:
    candidate = destination / source_name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        next_candidate = destination / f"{stem} ({index}){suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def _remove_existing(path: Path) -> None:
    long_raw = to_windows_long_path(path)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(long_raw)
        return
    Path(long_raw).unlink(missing_ok=False)


def _ensure_artifacts_root() -> Path:
    root = Path(tempfile.gettempdir()) / "many_panelz_explorer_ops"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _prepare_artifacts(job_id: str) -> OperationArtifacts:
    root = _ensure_artifacts_root()
    job_dir = root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = job_dir / "job.json"
    log_path = job_dir / "output.log"
    return OperationArtifacts(job_dir=job_dir, metadata_path=metadata_path, log_path=log_path)


def _write_metadata(job: OperationJob, artifacts: OperationArtifacts) -> None:
    payload: dict[str, Any] = {
        "job_id": job.job_id,
        "kind": job.request.kind,
        "status": job.status,
        "backend": job.request.backend_id,
        "dispatch_mode": job.request.dispatch_mode,
        "conflict_policy": job.request.conflict_policy,
        "sources": [str(source) for source in job.request.sources],
        "target_dir": str(job.request.target_dir) if job.request.target_dir else None,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "message": job.message,
        "processed_count": job.processed_count,
        "pid": job.pid,
        "backend_options": dict(job.request.backend_options),
        "created_by": job.request.created_by,
    }
    artifacts.metadata_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def _write_script(artifacts: OperationArtifacts, script_lines: Sequence[str]) -> Path:
    script_path = artifacts.job_dir / "run.cmd"
    full_text = "\n".join(
        [
            "@echo off",
            "chcp 65001 >nul",
            "setlocal enableextensions",
        ]
        + list(script_lines)
        + ["exit /b %ERRORLEVEL%"]
    )
    script_path.write_text(full_text, encoding="utf-8", newline="\n")
    return script_path


def _run_script(
    script_path: Path,
    log_path: Path,
    *,
    cmd_path: str,
    wait: bool,
) -> OperationResult:
    cmd_executable = str(cmd_path or "").strip()
    if not cmd_executable or not Path(cmd_executable).exists():
        return OperationResult(
            status="failed",
            message=f"Command shell is unavailable: {cmd_executable or '(empty)'}",
            processed_count=0,
        )
    # Companion tool output is shown in the live console; no stdout/stderr capture here.
    log_path.write_text(
        "Companion output is not redirected; see the subprocess console window.\n",
        encoding="utf-8",
        newline="\n",
    )
    command = _quoted(str(script_path))
    creationflags = int(getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    process = subprocess.Popen(
        [cmd_executable, "/d", "/c", command],
        creationflags=creationflags,
    )
    if not wait:
        return OperationResult(
            status="dispatched",
            message=f"Dispatched script: {script_path.name}",
            processed_count=0,
            pid=process.pid,
        )
    code = process.wait()
    if code == 0:
        return OperationResult(status="succeeded", message="Script completed.", processed_count=0)
    return OperationResult(status="failed", message=f"Script failed with exit code {code}.", processed_count=0)


def _expand_template(
    template: str,
    *,
    kind: OperationKind,
    sources: Sequence[Path],
    target_dir: Path | None,
    use_extended_paths: bool,
) -> str:
    source_literals = " ".join(
        _quoted(to_windows_arg_path(path, use_extended_paths=use_extended_paths))
        for path in sources
    )
    first_source = (
        _quoted(to_windows_arg_path(sources[0], use_extended_paths=use_extended_paths))
        if sources
        else ""
    )
    target_literal = (
        _quoted(to_windows_arg_path(target_dir, use_extended_paths=use_extended_paths))
        if target_dir
        else ""
    )
    return (
        str(template or "")
        .replace("{operation}", kind)
        .replace("{sources}", source_literals)
        .replace("{source}", first_source)
        .replace("{target}", target_literal)
    )


def _execute_python_builtin(request: OperationRequest) -> OperationResult:
    target_dir = request.target_dir
    if request.kind in {"copy", "move"} and target_dir is None:
        return OperationResult(status="failed", message="Target directory is required.")

    processed = 0
    for source in request.sources:
        source = _normalize_path(source)
        if request.kind == "delete":
            send2trash(to_windows_long_path(source))
            processed += 1
            continue

        assert target_dir is not None
        destination_dir = _normalize_path(target_dir)
        destination = destination_dir / source.name
        if destination.exists():
            policy = request.conflict_policy
            if policy == "cancel":
                return OperationResult(status="cancelled", message="Cancelled by conflict policy.", processed_count=processed)
            if policy == "skip":
                continue
            if policy == "rename":
                destination = _safe_target(destination_dir, source.name)
            elif policy == "overwrite":
                if source.resolve() == destination.resolve():
                    continue
                _remove_existing(destination)

        destination_dir.mkdir(parents=True, exist_ok=True)
        if request.kind == "move":
            moved_to = Path(
                shutil.move(
                    to_windows_long_path(source),
                    to_windows_long_path(destination),
                )
            )
            _ = moved_to
            processed += 1
            continue

        if source.is_dir():
            shutil.copytree(
                to_windows_long_path(source),
                to_windows_long_path(destination),
            )
        else:
            shutil.copy2(
                to_windows_long_path(source),
                to_windows_long_path(destination),
            )
        processed += 1

    return OperationResult(status="succeeded", message="Operation completed.", processed_count=processed)


def _execute_permanent_delete(request: OperationRequest) -> OperationResult:
    processed = 0
    for source in request.sources:
        path = _normalize_path(source)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(to_windows_long_path(path))
        else:
            Path(to_windows_long_path(path)).unlink(missing_ok=False)
        processed += 1
    return OperationResult(status="succeeded", message="Permanent delete completed.", processed_count=processed)


def _execute_windows_explorer(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    preferences: OperationExecutionPreferences,
    wait: bool,
) -> OperationResult:
    if request.kind not in {"copy", "move"} or request.target_dir is None:
        return OperationResult(status="failed", message="Windows Explorer backend supports copy/move only.")
    verb = "MoveHere" if request.kind == "move" else "CopyHere"
    source_items = ", ".join(
        f'@{{Parent={_quoted(_display_path(source.parent))};Name={_quoted(source.name)}}}'
        for source in request.sources
    )
    command = (
        "$shell = New-Object -ComObject Shell.Application; "
        f"$dest = $shell.NameSpace({_quoted(_display_path(request.target_dir))}); "
        "if ($dest -eq $null) { exit 1 }; "
        f"$items = @({source_items}); "
        "foreach ($item in $items) { "
        "$folder = $shell.NameSpace($item.Parent); "
        "if ($folder -eq $null) { exit 2 }; "
        "$entry = $folder.ParseName($item.Name); "
        "if ($entry -eq $null) { exit 3 }; "
        f"$dest.{verb}($entry, 16) "
        "}; "
        "exit 0"
    )
    script_path = _write_script(
        artifacts,
        [f"powershell -NoProfile -ExecutionPolicy Bypass -Command {_quoted(command)}"],
    )
    return _run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def _execute_robocopy(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    if request.kind not in {"copy", "move"} or request.target_dir is None:
        return OperationResult(status="failed", message="Robocopy backend supports copy/move only.")
    robocopy_exe = str(preferences.resolved_robocopy_path or "").strip()
    if not robocopy_exe or not Path(robocopy_exe).exists():
        return OperationResult(
            status="failed",
            message=f"Robocopy executable is unavailable: {robocopy_exe or '(empty)'}",
            processed_count=0,
        )
    target = _normalize_path(request.target_dir)
    use_extended_paths = _resolve_use_extended_paths(
        request,
        default=preferences.use_extended_paths_robocopy,
    )
    selected_args = request.backend_options.get("robocopy_args", "").strip()
    args = (
        selected_args
        if selected_args
        else (
            preferences.robocopy_move_args
            if request.kind == "move"
            else preferences.robocopy_copy_args
        )
    )
    arg_tail = " ".join(_split_args(args))
    script_lines: list[str] = []
    for source in request.sources:
        source = _normalize_path(source)
        if source.is_dir():
            src = to_windows_arg_path(source, use_extended_paths=use_extended_paths)
            dst = to_windows_arg_path(
                target / source.name, use_extended_paths=use_extended_paths
            )
            script_lines.append(
                f'{_quoted(robocopy_exe)} {_quoted(src)} {_quoted(dst)} {arg_tail}'
            )
        else:
            src_parent = to_windows_arg_path(
                source.parent, use_extended_paths=use_extended_paths
            )
            dst_parent = to_windows_arg_path(
                target, use_extended_paths=use_extended_paths
            )
            script_lines.append(
                f'{_quoted(robocopy_exe)} {_quoted(src_parent)} {_quoted(dst_parent)} {_quoted(source.name)} {arg_tail}'
            )
        script_lines.append("if %ERRORLEVEL% GTR 7 exit /b %ERRORLEVEL%")
    script_path = _write_script(artifacts, script_lines)
    return _run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def _execute_external_command(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
    executable: str,
    args_template: str,
    use_extended_paths_default: bool,
) -> OperationResult:
    exe = str(executable or "").strip()
    if not exe or exe == COMPANION_TOOL_NOT_FOUND:
        return OperationResult(status="failed", message="Executable is not configured.")
    use_extended_paths = _resolve_use_extended_paths(
        request,
        default=use_extended_paths_default,
    )
    expanded = _expand_template(
        args_template,
        kind=request.kind,
        sources=request.sources,
        target_dir=request.target_dir,
        use_extended_paths=use_extended_paths,
    )
    extra_args = str(request.backend_options.get("extra_args", "")).strip()
    if extra_args:
        expanded = f"{expanded} {extra_args}".strip()
    cmd_line = " ".join([_quoted(exe), expanded]).strip()
    script_path = _write_script(artifacts, [cmd_line])
    return _run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def _execute_cmd_delete(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    if request.kind != "delete":
        return OperationResult(status="failed", message="cmd delete backend supports delete only.")
    tail = " ".join(_split_args(preferences.cmd_delete_args))
    use_extended_paths = _resolve_use_extended_paths(
        request,
        default=preferences.use_extended_paths_cmd_delete,
    )
    script_lines: list[str] = []
    for source in request.sources:
        source = _normalize_path(source)
        literal = _quoted(
            to_windows_arg_path(source, use_extended_paths=use_extended_paths)
        )
        script_lines.append(f"if exist {literal}\\* (rmdir /S {tail} {literal}) else (del {tail} {literal})")
    script_path = _write_script(artifacts, script_lines)
    return _run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def _execute_powershell_delete(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    if request.kind != "delete":
        return OperationResult(status="failed", message="PowerShell delete backend supports delete only.")
    options = " ".join(_split_args(preferences.powershell_delete_args))
    use_extended_paths = _resolve_use_extended_paths(
        request,
        default=preferences.use_extended_paths_powershell_delete,
    )
    literals = ", ".join(
        _quoted(
            _display_path(
                to_windows_arg_path(source, use_extended_paths=use_extended_paths)
            )
        )
        for source in request.sources
    )
    command = f"Remove-Item -LiteralPath @({literals}) -Recurse {options} -ErrorAction Stop"
    script_path = _write_script(
        artifacts,
        [f"powershell -NoProfile -ExecutionPolicy Bypass -Command {_quoted(command)}"],
    )
    return _run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def _execute_rimraf_delete(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    if request.kind != "delete":
        return OperationResult(status="failed", message="rimraf backend supports delete only.")
    return _execute_external_command(
        request,
        artifacts,
        wait=wait,
        preferences=preferences,
        executable=preferences.rimraf_executable,
        args_template=f"{preferences.rimraf_args_template} {{sources}}",
        use_extended_paths_default=preferences.use_extended_paths_rimraf,
    )


def execute_operation_request(
    request: OperationRequest,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
    artifacts: OperationArtifacts,
) -> OperationResult:
    backend = request.backend_id
    if backend == BACKEND_PYTHON:
        return _execute_python_builtin(request)
    if backend == BACKEND_RECYCLE_BIN:
        if request.kind != "delete":
            return OperationResult(status="failed", message="Recycle Bin backend supports delete only.")
        for source in request.sources:
            send2trash(to_windows_long_path(source))
        return OperationResult(
            status="succeeded",
            message=f"Deleted {len(request.sources)} item(s) to Recycle Bin.",
            processed_count=len(request.sources),
        )
    if backend == BACKEND_PERMANENT_NATIVE:
        return _execute_permanent_delete(request)
    if backend == BACKEND_EXPLORER:
        return _execute_windows_explorer(
            request,
            artifacts,
            preferences=preferences,
            wait=wait,
        )
    if backend == BACKEND_ROBOCOPY:
        return _execute_robocopy(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_TERACOPY:
        return _execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.teracopy_executable,
            args_template=preferences.teracopy_args_template,
            use_extended_paths_default=preferences.use_extended_paths_teracopy,
        )
    if backend == BACKEND_UNSTOPPABLE:
        return _execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.unstoppable_executable,
            args_template=preferences.unstoppable_args_template,
            use_extended_paths_default=preferences.use_extended_paths_unstoppable,
        )
    if backend == BACKEND_EXTERNAL_COPYMOVE:
        return _execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.generic_copymove_executable,
            args_template=preferences.generic_copymove_args_template,
            use_extended_paths_default=preferences.use_extended_paths_external_copymove,
        )
    if backend == BACKEND_CMD_DELETE:
        return _execute_cmd_delete(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_POWERSHELL_DELETE:
        return _execute_powershell_delete(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_RIMRAF:
        return _execute_rimraf_delete(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_EXTERNAL_DELETE:
        return _execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.generic_delete_executable,
            args_template=preferences.generic_delete_args_template,
            use_extended_paths_default=preferences.use_extended_paths_external_delete,
        )
    return OperationResult(status="failed", message=f"Unknown backend: {backend}")


class OperationQueueManager(QObject):
    job_added = Signal(object)
    job_updated = Signal(object)
    jobs_reset = Signal()

    def __init__(
        self,
        *,
        preferences: OperationExecutionPreferences | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._preferences = preferences or OperationExecutionPreferences()
        self._jobs: list[OperationJob] = []
        self._jobs_by_id: dict[str, OperationJob] = {}
        self._queue: list[str] = []
        self._running_job_id: str | None = None
        self._lock = threading.RLock()
        self._running_processes: dict[str, subprocess.Popen[bytes]] = {}

    @property
    def preferences(self) -> OperationExecutionPreferences:
        return self._preferences

    def set_preferences(self, preferences: OperationExecutionPreferences) -> None:
        self._preferences = preferences

    def jobs(self) -> list[OperationJob]:
        return list(self._jobs)

    def get_job(self, job_id: str) -> OperationJob | None:
        return self._jobs_by_id.get(job_id)

    def submit(self, request: OperationRequest) -> OperationJob:
        job = OperationJob(
            job_id=uuid.uuid4().hex,
            request=request,
            status="queued",
            created_at=_utcnow(),
            message="Queued",
        )
        with self._lock:
            self._jobs.append(job)
            self._jobs_by_id[job.job_id] = job
            self.job_added.emit(job)
            mode = request.dispatch_mode
            if mode == DISPATCH_MODE_LAUNCH_NO_WAIT:
                dispatched = self._execute_one(job, wait=False)
                self._replace_job(dispatched)
                self.job_updated.emit(dispatched)
                return dispatched
            if mode == DISPATCH_MODE_RUN_WAIT:
                running = self._replace_job(
                    replace(job, status="running", started_at=_utcnow(), message="Running")
                )
                self.job_updated.emit(running)
                completed = self._execute_one(running, wait=True)
                self._replace_job(completed)
                self.job_updated.emit(completed)
                return completed
            self._queue.append(job.job_id)
            self._maybe_run_next_locked()
            return job

    def cancel_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs_by_id.get(job_id)
            if job is None:
                return
            if job.status == "queued":
                self._queue = [jid for jid in self._queue if jid != job_id]
                cancelled = replace(job, status="cancelled", message="Cancelled while queued.", completed_at=_utcnow())
                self._replace_job(cancelled)
                self.job_updated.emit(cancelled)
                return
            if job.status == "running":
                cancelled = replace(
                    job,
                    cancel_requested=True,
                    message="Cancellation requested.",
                )
                self._replace_job(cancelled)
                self.job_updated.emit(cancelled)

    def retry_job(self, job_id: str) -> OperationJob | None:
        job = self._jobs_by_id.get(job_id)
        if job is None:
            return None
        if job.status not in {"failed", "cancelled"}:
            return None
        retry_request = replace(job.request)
        return self.submit(retry_request)

    def clear_finished(self) -> None:
        with self._lock:
            self._jobs = [
                job
                for job in self._jobs
                if job.status not in {"succeeded", "failed", "cancelled", "dispatched"}
            ]
            self._jobs_by_id = {job.job_id: job for job in self._jobs}
            self.jobs_reset.emit()

    def _replace_job(self, job: OperationJob) -> OperationJob:
        self._jobs_by_id[job.job_id] = job
        for index, existing in enumerate(self._jobs):
            if existing.job_id == job.job_id:
                self._jobs[index] = job
                break
        return job

    def _maybe_run_next_locked(self) -> None:
        if self._running_job_id is not None:
            return
        if not self._queue:
            return
        next_job_id = self._queue.pop(0)
        job = self._jobs_by_id.get(next_job_id)
        if job is None:
            self._maybe_run_next_locked()
            return
        self._running_job_id = job.job_id
        running = replace(job, status="running", started_at=_utcnow(), message="Running")
        self._replace_job(running)
        self.job_updated.emit(running)
        thread = threading.Thread(
            target=self._run_one_thread,
            args=(running.job_id,),
            daemon=True,
        )
        thread.start()

    def _run_one_thread(self, job_id: str) -> None:
        completed: OperationJob | None = None
        with self._lock:
            job = self._jobs_by_id.get(job_id)
        if job is None:
            return
        completed = self._execute_one(job, wait=True)
        with self._lock:
            self._replace_job(completed)
            self.job_updated.emit(completed)
            self._running_job_id = None
            self._maybe_run_next_locked()

    def _execute_one(self, job: OperationJob, *, wait: bool) -> OperationJob:
        artifacts = _prepare_artifacts(job.job_id)
        running = replace(job, artifacts=artifacts, started_at=job.started_at or _utcnow())
        _write_metadata(running, artifacts)
        try:
            result = execute_operation_request(
                running.request,
                wait=wait,
                preferences=self._preferences,
                artifacts=artifacts,
            )
        except Exception as exc:
            failed = replace(
                running,
                status="failed",
                message=str(exc),
                completed_at=_utcnow(),
            )
            _write_metadata(failed, artifacts)
            return failed

        final = replace(
            running,
            status=result.status,
            message=result.message,
            processed_count=result.processed_count,
            pid=result.pid,
            completed_at=_utcnow() if result.status != "dispatched" else None,
        )
        _write_metadata(final, artifacts)
        return final


def normalize_operation_kind(value: str, *, fallback: OperationKind = "copy") -> OperationKind:
    normalized = str(value).strip().lower()
    if normalized in {"copy", "move", "delete"}:
        return normalized
    return fallback


def normalize_dispatch_mode(
    value: str,
    *,
    fallback: OperationDispatchMode = DISPATCH_MODE_QUEUE,
) -> OperationDispatchMode:
    normalized = str(value).strip().lower()
    if normalized in {
        DISPATCH_MODE_QUEUE,
        DISPATCH_MODE_LAUNCH_NO_WAIT,
        DISPATCH_MODE_RUN_WAIT,
    }:
        return normalized
    return fallback


def normalize_conflict_policy(
    value: str,
    *,
    fallback: OperationConflictPolicy = "rename",
) -> OperationConflictPolicy:
    normalized = str(value).strip().lower()
    if normalized in {"overwrite", "skip", "rename", "cancel"}:
        return normalized
    return fallback


def normalize_shortcut_behavior(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {SHORTCUT_BEHAVIOR_DIRECT, SHORTCUT_BEHAVIOR_DIALOG}:
        return normalized
    return SHORTCUT_BEHAVIOR_DIRECT


def normalize_queue_view_mode(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {QUEUE_VIEW_DOCK, QUEUE_VIEW_FLOATING, QUEUE_VIEW_BOTH}:
        return normalized
    return QUEUE_VIEW_DOCK


def normalize_copy_move_backend(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {
        BACKEND_PYTHON,
        BACKEND_EXPLORER,
        BACKEND_ROBOCOPY,
        BACKEND_TERACOPY,
        BACKEND_UNSTOPPABLE,
        BACKEND_EXTERNAL_COPYMOVE,
    }:
        return normalized
    return BACKEND_PYTHON


def normalize_delete_backend(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {
        BACKEND_RECYCLE_BIN,
        BACKEND_PERMANENT_NATIVE,
        BACKEND_CMD_DELETE,
        BACKEND_POWERSHELL_DELETE,
        BACKEND_RIMRAF,
        BACKEND_EXTERNAL_DELETE,
    }:
        return normalized
    return BACKEND_RECYCLE_BIN


def _common_tool_search_dirs() -> list[Path]:
    dirs: list[Path] = [Path("C:/bin")]
    env_vars = [
        "ProgramFiles",
        "ProgramFiles(x86)",
        "LOCALAPPDATA",
        "APPDATA",
    ]
    for env_name in env_vars:
        raw = os.environ.get(env_name, "").strip()
        if not raw:
            continue
        base = Path(raw)
        dirs.append(base)
        dirs.append(base / "Programs")
        dirs.append(base / "Tools")
        dirs.append(base / "Utilities")
        dirs.append(base / "npm")
    return dirs


def _candidate_executable_paths(executable_name: str) -> list[Path]:
    exe = str(executable_name or "").strip().strip('"')
    if not exe:
        return []
    candidates: list[Path] = []
    which_hit = shutil.which(exe)
    if which_hit:
        candidates.append(Path(which_hit))
    raw_path = Path(exe)
    if raw_path.is_absolute():
        candidates.append(raw_path)
    for directory in _common_tool_search_dirs():
        # Typical Windows companion install subdirectories.
        roots = [
            directory,
            directory / "TeraCopy",
            directory / "Roadkil's Unstoppable Copier",
            directory / "nodejs",
        ]
        for root in roots:
            candidates.append(root / exe)
    # Common Windows command wrappers for bare command names.
    if raw_path.suffix.lower() != ".cmd":
        for directory in _common_tool_search_dirs():
            roots = [
                directory,
                directory / "TeraCopy",
                directory / "Roadkil's Unstoppable Copier",
                directory / "nodejs",
            ]
            for root in roots:
                candidates.append(root / f"{exe}.cmd")
                candidates.append(root / f"{exe}.exe")
    return candidates


def _resolve_if_missing(configured: str, default_name: str) -> str:
    configured_text = str(configured or "").strip()
    if configured_text == COMPANION_TOOL_NOT_FOUND:
        return COMPANION_TOOL_NOT_FOUND
    if configured_text and Path(configured_text).is_absolute():
        return configured_text

    # Only auto-discover when unset or using simple default command name.
    if configured_text and configured_text not in {default_name, Path(default_name).name}:
        return configured_text

    for candidate in _candidate_executable_paths(default_name):
        if candidate.exists():
            return str(candidate)
    for candidate in _candidate_executable_paths(configured_text or default_name):
        if candidate.exists():
            return str(candidate)
    return COMPANION_TOOL_NOT_FOUND


def is_scripted_backend(backend_id: str) -> bool:
    return str(backend_id).strip().lower() in {
        BACKEND_EXPLORER,
        BACKEND_ROBOCOPY,
        BACKEND_TERACOPY,
        BACKEND_UNSTOPPABLE,
        BACKEND_EXTERNAL_COPYMOVE,
        BACKEND_CMD_DELETE,
        BACKEND_POWERSHELL_DELETE,
        BACKEND_RIMRAF,
        BACKEND_EXTERNAL_DELETE,
    }


def resolve_system_command_paths() -> tuple[str, str]:
    comspec_raw = str(os.environ.get("ComSpec", "")).strip()
    windir_raw = str(os.environ.get("WINDIR", r"C:\Windows")).strip() or r"C:\Windows"
    cmd_candidates: list[Path] = []
    robocopy_candidates: list[Path] = []
    if comspec_raw:
        cmd_candidates.append(Path(comspec_raw))
    cmd_candidates.append(Path(windir_raw) / "System32" / "cmd.exe")
    cmd_candidates.append(Path(DEFAULT_SYSTEM_CMD_FALLBACK))
    robocopy_candidates.append(Path(windir_raw) / "System32" / "robocopy.exe")
    robocopy_candidates.append(Path(DEFAULT_SYSTEM_ROBOCOPY_FALLBACK))

    resolved_cmd = next(
        (str(candidate) for candidate in cmd_candidates if candidate.exists()),
        str(cmd_candidates[0]),
    )
    resolved_robocopy = next(
        (str(candidate) for candidate in robocopy_candidates if candidate.exists()),
        str(robocopy_candidates[0]),
    )
    return resolved_cmd, resolved_robocopy


def resolve_companion_tool_paths(
    preferences: OperationExecutionPreferences,
) -> OperationExecutionPreferences:
    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    return replace(
        preferences,
        teracopy_executable=_resolve_if_missing(
            preferences.teracopy_executable,
            DEFAULT_TERA_COPY_EXE,
        ),
        unstoppable_executable=_resolve_if_missing(
            preferences.unstoppable_executable,
            DEFAULT_UNSTOPPABLE_EXE,
        ),
        rimraf_executable=_resolve_if_missing(
            preferences.rimraf_executable,
            DEFAULT_RIMRAF_EXE,
        ),
        resolved_cmd_path=resolved_cmd,
        resolved_robocopy_path=resolved_robocopy,
    )


def discover_single_companion_tool(
    *,
    configured: str,
    default_executable: str,
) -> str:
    return _resolve_if_missing(configured, default_executable)
