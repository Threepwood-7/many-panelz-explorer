from __future__ import annotations

import shutil
from pathlib import Path

from send2trash import send2trash

from .artifacts import expand_template, run_script, write_script
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
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationRequest,
    OperationResult,
)


def execute_python_builtin(request: OperationRequest) -> OperationResult:
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
                return OperationResult(status="cancelled", message="Cancelled by conflict policy.", processed_count=processed)
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

    return OperationResult(status="succeeded", message="Operation completed.", processed_count=processed)


def execute_permanent_delete(request: OperationRequest) -> OperationResult:
    processed = 0
    for source in request.sources:
        path = normalize_path(source)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(to_windows_long_path(path))
        else:
            Path(to_windows_long_path(path)).unlink(missing_ok=False)
        processed += 1
    return OperationResult(status="succeeded", message="Permanent delete completed.", processed_count=processed)


def execute_windows_explorer(
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
        f'@{{Parent={quoted(display_path(source.parent))};Name={quoted(source.name)}}}'
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
    if request.kind not in {"copy", "move"} or request.target_dir is None:
        return OperationResult(status="failed", message="Robocopy backend supports copy/move only.")
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
                f'{quoted(robocopy_exe)} {quoted(src)} {quoted(dst)} {arg_tail}'
            )
        else:
            src_parent = to_windows_arg_path(
                source.parent, use_extended_paths=use_extended_paths
            )
            dst_parent = to_windows_arg_path(
                target, use_extended_paths=use_extended_paths
            )
            script_lines.append(
                f'{quoted(robocopy_exe)} {quoted(src_parent)} {quoted(dst_parent)} {quoted(source.name)} {arg_tail}'
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
        # +d: load program defaults, +m: move mode.
        return "+dm"
    # +d: load program defaults for predictable copy behavior.
    return "+d"


def execute_unstoppable(
    request: OperationRequest,
    artifacts: OperationArtifacts,
    *,
    wait: bool,
    preferences: OperationExecutionPreferences,
) -> OperationResult:
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

    script_lines: list[str] = []
    for source in request.sources:
        expanded = expand_template(
            preferences.unstoppable_args_template,
            kind=operation_token,
            sources=(normalize_path(source),),
            target_dir=request.target_dir,
            use_extended_paths=use_extended_paths,
        )
        if extra_args:
            expanded = f"{expanded} {extra_args}".strip()
        cmd_line = " ".join([quoted(exe), expanded]).strip()
        script_lines.append(cmd_line)
        script_lines.append("if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%")

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
    if request.kind != "delete":
        return OperationResult(status="failed", message="cmd delete backend supports delete only.")
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
        script_lines.append(f"if exist {literal}\\* (rmdir /S {tail} {literal}) else (del {tail} {literal})")
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
    if request.kind != "delete":
        return OperationResult(status="failed", message="PowerShell delete backend supports delete only.")
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
    command = f"Remove-Item -LiteralPath @({literals}) -Recurse {options} -ErrorAction Stop"
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
    if request.kind != "delete":
        return OperationResult(status="failed", message="rimraf backend supports delete only.")
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
    backend = request.backend_id
    if backend == BACKEND_PYTHON:
        return execute_python_builtin(request)
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
        return execute_cmd_delete(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_POWERSHELL_DELETE:
        return execute_powershell_delete(request, artifacts, wait=wait, preferences=preferences)
    if backend == BACKEND_RIMRAF:
        return execute_rimraf_delete(request, artifacts, wait=wait, preferences=preferences)
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
