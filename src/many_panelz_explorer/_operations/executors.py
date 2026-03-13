"""Execute file operations through built-in and external backends."""

from __future__ import annotations

import shutil
from pathlib import Path

from send2trash import send2trash

from .artifacts import (
    expand_template,
    run_script,
    write_script,
    write_unstoppable_job_file,
)
from .path_helpers import (
    display_path,
    normalize_path,
    quoted,
    remove_existing,
    resolve_use_extended_paths,
    safe_target,
    split_args,
    to_windows_arg_path,
    to_windows_long_path,
)
from .types import (
    BACKEND_CMD_DELETE,
    BACKEND_EXPLORER,
    BACKEND_EXTERNAL_COPYMOVE,
    BACKEND_EXTERNAL_DELETE,
    BACKEND_PERMANENT_NATIVE,
    BACKEND_POWERSHELL_DELETE,
    BACKEND_PYTHON,
    BACKEND_RECYCLE_BIN,
    BACKEND_RIMRAF,
    BACKEND_ROBOCOPY,
    BACKEND_TERACOPY,
    BACKEND_UNSTOPPABLE,
    COMPANION_TOOL_NOT_FOUND,
    DEFAULT_UNSTOPPABLE_ARGS,
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationRequest,
    OperationResult,
)


def execute_python_builtin(request: OperationRequest) -> OperationResult:
    """Execute a request with the built-in Python file operations."""
    target_dir = request.target_dir
    if request.kind in {"copy", "move"} and target_dir is None:
        return OperationResult(status="failed", message="Target directory is required.")

    processed = 0
    for source in request.sources:
        source = normalize_path(source)
        if request.kind == "delete":
            send2trash(to_windows_long_path(source))
            processed += 1
            continue

        assert target_dir is not None
        destination_dir = normalize_path(target_dir)
        destination = destination_dir / source.name
        if destination.exists():
            policy = request.conflict_policy
            if policy == "cancel":
                return OperationResult(
                    status="cancelled",
                    message="Cancelled by conflict policy.",
                    processed_count=processed,
                )
            if policy == "skip":
                continue
            if policy == "rename":
                destination = safe_target(destination_dir, source.name)
            elif policy == "overwrite":
                if source.resolve() == destination.resolve():
                    continue
                remove_existing(destination)

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

    return OperationResult(
        status="succeeded", message="Operation completed.", processed_count=processed
    )


def execute_permanent_delete(request: OperationRequest) -> OperationResult:
    """Execute a non-recoverable native delete operation."""
    processed = 0
    for source in request.sources:
        path = normalize_path(source)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(to_windows_long_path(path))
        else:
            Path(to_windows_long_path(path)).unlink(missing_ok=False)
        processed += 1
    return OperationResult(
        status="succeeded",
        message="Permanent delete completed.",
        processed_count=processed,
    )


def execute_windows_explorer(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    preferences: OperationExecutionPreferences,
    wait: bool,
) -> OperationResult:
    """Execute copy or move through the Windows Explorer COM shell."""
    if request.kind not in {"copy", "move"} or request.target_dir is None:
        return OperationResult(
            status="failed", message="Windows Explorer backend supports copy/move only."
        )
    verb = "MoveHere" if request.kind == "move" else "CopyHere"
    source_items = ", ".join(
        f"@{{Parent={quoted(display_path(source.parent))};Name={quoted(source.name)}}}"
        for source in request.sources
    )
    command = (
        "$shell = New-Object -ComObject Shell.Application; "
        f"$dest = $shell.NameSpace({quoted(display_path(request.target_dir))}); "
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
    script_path = write_script(
        artifacts,
        [f"powershell -NoProfile -ExecutionPolicy Bypass -Command {quoted(command)}"],
    )
    return run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def execute_robocopy(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    """Execute copy or move through Robocopy wrapper scripts."""
    if request.kind not in {"copy", "move"} or request.target_dir is None:
        return OperationResult(
            status="failed", message="Robocopy backend supports copy/move only."
        )
    robocopy_exe = str(preferences.resolved_robocopy_path or "").strip()
    if not robocopy_exe or not Path(robocopy_exe).exists():
        return OperationResult(
            status="failed",
            message=f"Robocopy executable is unavailable: {robocopy_exe or '(empty)'}",
            processed_count=0,
        )
    target = normalize_path(request.target_dir)
    use_extended_paths = resolve_use_extended_paths(
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
    arg_tail = " ".join(split_args(args))
    script_lines: list[str] = []
    for source in request.sources:
        source = normalize_path(source)
        if source.is_dir():
            src = to_windows_arg_path(source, use_extended_paths=use_extended_paths)
            dst = to_windows_arg_path(
                target / source.name, use_extended_paths=use_extended_paths
            )
            script_lines.append(
                f"{quoted(robocopy_exe)} {quoted(src)} {quoted(dst)} {arg_tail}"
            )
        else:
            src_parent = to_windows_arg_path(
                source.parent, use_extended_paths=use_extended_paths
            )
            dst_parent = to_windows_arg_path(
                target, use_extended_paths=use_extended_paths
            )
            script_lines.append(
                f"{quoted(robocopy_exe)} {quoted(src_parent)} "
                f"{quoted(dst_parent)} {quoted(source.name)} {arg_tail}"
            )
        script_lines.append("if %ERRORLEVEL% GTR 7 exit /b %ERRORLEVEL%")
    # Robocopy uses 0-7 as success/info codes; normalize success to 0 for queue status.
    script_lines.append("cmd /c exit /b 0")
    script_path = write_script(artifacts, script_lines)
    return run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def execute_external_command(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
    executable: str,
    args_template: str,
    use_extended_paths_default: bool,
    operation_token: str | None = None,
) -> OperationResult:
    """Execute a request through a configured external command template."""
    exe = str(executable or "").strip()
    if not exe or exe == COMPANION_TOOL_NOT_FOUND:
        return OperationResult(status="failed", message="Executable is not configured.")
    use_extended_paths = resolve_use_extended_paths(
        request,
        default=use_extended_paths_default,
    )
    expanded = expand_template(
        args_template,
        kind=(operation_token if operation_token is not None else request.kind),
        sources=request.sources,
        target_dir=request.target_dir,
        use_extended_paths=use_extended_paths,
    )
    extra_args = str(request.backend_options.get("extra_args", "")).strip()
    if extra_args:
        expanded = f"{expanded} {extra_args}".strip()
    cmd_line = " ".join([quoted(exe), expanded]).strip()
    script_path = write_script(artifacts, [cmd_line])
    return run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def _unstoppable_operation_token(kind: str) -> str:
    normalized = str(kind or "").strip().lower()
    if normalized == "move":
        return "+m"
    return ""


def _merge_unstoppable_switch_args(
    *args_groups: str,
) -> str:
    plus_letters: list[str] = []
    minus_letters: list[str] = []
    other_tokens: list[str] = []

    def _append_unique(target: list[str], value: str) -> None:
        for letter in value:
            if letter and letter not in target:
                target.append(letter)

    for raw_group in args_groups:
        for token in split_args(raw_group):
            if token.startswith("+") and len(token) > 1:
                _append_unique(plus_letters, token[1:])
                continue
            if token.startswith("-") and len(token) > 1:
                _append_unique(minus_letters, token[1:])
                continue
            other_tokens.append(token)

    parts: list[str] = []
    if plus_letters:
        parts.append(f"+{''.join(plus_letters)}")
    if minus_letters:
        parts.append(f"-{''.join(minus_letters)}")
    parts.extend(other_tokens)
    return " ".join(parts).strip()


def execute_unstoppable(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    """Execute copy or move through Unstoppable Copier."""
    if request.kind not in {"copy", "move"} or request.target_dir is None:
        return OperationResult(
            status="failed",
            message="Unstoppable backend supports copy/move only.",
        )

    exe = str(preferences.unstoppable_executable or "").strip()
    if not exe or exe == COMPANION_TOOL_NOT_FOUND:
        return OperationResult(status="failed", message="Executable is not configured.")
    if not Path(exe).exists():
        return OperationResult(
            status="failed",
            message=f"Executable is unavailable: {exe}",
            processed_count=0,
        )

    use_extended_paths = resolve_use_extended_paths(
        request,
        default=preferences.use_extended_paths_unstoppable,
    )
    operation_token = _unstoppable_operation_token(request.kind)
    extra_args = str(request.backend_options.get("extra_args", "")).strip()
    job_file_path = write_unstoppable_job_file(
        artifacts,
        sources=tuple(normalize_path(source) for source in request.sources),
        target_dir=request.target_dir,
        use_extended_paths=use_extended_paths,
    )

    args_template = str(preferences.unstoppable_args_template or "").strip()
    if not args_template:
        args_template = DEFAULT_UNSTOPPABLE_ARGS
    expanded = expand_template(
        args_template,
        kind=operation_token,
        sources=(),
        target_dir=None,
        use_extended_paths=use_extended_paths,
    )
    expanded = _merge_unstoppable_switch_args(
        expanded,
        operation_token,
        extra_args,
    )
    expanded = " ".join(
        part for part in [expanded.strip(), quoted(str(job_file_path))] if part
    ).strip()
    cmd_line = " ".join([quoted(exe), expanded]).strip()
    script_lines = [cmd_line, "if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%"]

    script_path = write_script(artifacts, script_lines)
    return run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def execute_cmd_delete(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    """Execute delete operations through classic `cmd.exe` commands."""
    if request.kind != "delete":
        return OperationResult(
            status="failed", message="cmd delete backend supports delete only."
        )
    tail = " ".join(split_args(preferences.cmd_delete_args))
    use_extended_paths = resolve_use_extended_paths(
        request,
        default=preferences.use_extended_paths_cmd_delete,
    )
    script_lines: list[str] = []
    for source in request.sources:
        source = normalize_path(source)
        literal = quoted(
            to_windows_arg_path(source, use_extended_paths=use_extended_paths)
        )
        script_lines.append(
            f"if exist {literal}\\* (rmdir /S {tail} {literal}) "
            f"else (del {tail} {literal})"
        )
    script_path = write_script(artifacts, script_lines)
    return run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def execute_powershell_delete(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    """Execute delete operations through PowerShell."""
    if request.kind != "delete":
        return OperationResult(
            status="failed", message="PowerShell delete backend supports delete only."
        )
    options = " ".join(split_args(preferences.powershell_delete_args))
    use_extended_paths = resolve_use_extended_paths(
        request,
        default=preferences.use_extended_paths_powershell_delete,
    )
    literals = ", ".join(
        quoted(
            display_path(
                to_windows_arg_path(source, use_extended_paths=use_extended_paths)
            )
        )
        for source in request.sources
    )
    command = (
        f"Remove-Item -LiteralPath @({literals}) -Recurse {options} -ErrorAction Stop"
    )
    script_path = write_script(
        artifacts,
        [f"powershell -NoProfile -ExecutionPolicy Bypass -Command {quoted(command)}"],
    )
    return run_script(
        script_path,
        artifacts.log_path,
        cmd_path=preferences.resolved_cmd_path,
        wait=wait,
    )


def execute_rimraf_delete(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
    """Execute delete operations through `rimraf`."""
    if request.kind != "delete":
        return OperationResult(
            status="failed", message="rimraf backend supports delete only."
        )
    return execute_external_command(
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
    """Dispatch an operation request to the configured backend executor."""
    backend = request.backend_id
    if backend == BACKEND_PYTHON:
        return execute_python_builtin(request)
    if backend == BACKEND_RECYCLE_BIN:
        if request.kind != "delete":
            return OperationResult(
                status="failed", message="Recycle Bin backend supports delete only."
            )
        for source in request.sources:
            send2trash(to_windows_long_path(source))
        return OperationResult(
            status="succeeded",
            message=f"Deleted {len(request.sources)} item(s) to Recycle Bin.",
            processed_count=len(request.sources),
        )
    if backend == BACKEND_PERMANENT_NATIVE:
        return execute_permanent_delete(request)
    if backend == BACKEND_EXPLORER:
        return execute_windows_explorer(
            request,
            artifacts,
            preferences=preferences,
            wait=wait,
        )
    if backend == BACKEND_ROBOCOPY:
        return execute_robocopy(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_TERACOPY:
        return execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.teracopy_executable,
            args_template=preferences.teracopy_args_template,
            use_extended_paths_default=preferences.use_extended_paths_teracopy,
        )
    if backend == BACKEND_UNSTOPPABLE:
        return execute_unstoppable(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
        )
    if backend == BACKEND_EXTERNAL_COPYMOVE:
        return execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.generic_copymove_executable,
            args_template=preferences.generic_copymove_args_template,
            use_extended_paths_default=preferences.use_extended_paths_external_copymove,
        )
    if backend == BACKEND_CMD_DELETE:
        return execute_cmd_delete(
            request, artifacts, wait=wait, preferences=preferences
        )
    if backend == BACKEND_POWERSHELL_DELETE:
        return execute_powershell_delete(
            request, artifacts, wait=wait, preferences=preferences
        )
    if backend == BACKEND_RIMRAF:
        return execute_rimraf_delete(
            request, artifacts, wait=wait, preferences=preferences
        )
    if backend == BACKEND_EXTERNAL_DELETE:
        return execute_external_command(
            request,
            artifacts,
            wait=wait,
            preferences=preferences,
            executable=preferences.generic_delete_executable,
            args_template=preferences.generic_delete_args_template,
            use_extended_paths_default=preferences.use_extended_paths_external_delete,
        )
    return OperationResult(status="failed", message=f"Unknown backend: {backend}")
