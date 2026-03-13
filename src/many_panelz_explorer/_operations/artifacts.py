"""Prepare on-disk artifacts for external operation executors."""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import traceback
from contextlib import suppress
from pathlib import Path
from typing import Any

from .path_helpers import quoted, to_windows_arg_path
from .types import OperationArtifacts, OperationJob, OperationResult

_artifacts_root: Path | None = None
_ARTIFACTS_ROOT_LOCK = threading.Lock()


def ensure_artifacts_root() -> Path:
    """Return the shared artifact root used for companion process files."""

    global _artifacts_root

    with _ARTIFACTS_ROOT_LOCK:
        if _artifacts_root is None:
            _artifacts_root = Path(tempfile.mkdtemp(prefix="many-panelz-explorer-ops-"))
            with suppress(OSError):
                _artifacts_root.chmod(0o700)
        return _artifacts_root


def prepare_artifacts(job_id: str) -> OperationArtifacts:
    """Create per-job artifact paths for the given operation job id."""
    root = ensure_artifacts_root()
    job_dir = root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = job_dir / "job.json"
    log_path = job_dir / "output.log"
    script_path = job_dir / "run.cmd"
    return OperationArtifacts(
        job_dir=job_dir,
        metadata_path=metadata_path,
        log_path=log_path,
        script_path=script_path,
    )


def write_metadata(job: OperationJob, artifacts: OperationArtifacts) -> None:
    """Persist a JSON metadata snapshot for a queued or running job."""
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
        "script_path": str(job.artifacts.script_path) if job.artifacts else None,
        "backend_options": dict(job.request.backend_options),
        "created_by": job.request.created_by,
    }
    artifacts.metadata_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def write_exception_log(
    artifacts: OperationArtifacts,
    exc: BaseException,
) -> None:
    """Persist an executor traceback to the job log for failed operations."""

    traceback_text = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    artifacts.log_path.write_text(
        f"Executor failure:\n\n{traceback_text}",
        encoding="utf-8",
        newline="\n",
    )


def write_script(artifacts: OperationArtifacts, script_lines: list[str]) -> Path:
    """Write the launcher script used by companion executors."""
    script_path = artifacts.script_path or (artifacts.job_dir / "run.cmd")
    full_text = "\n".join(
        [
            "@echo off",
            "chcp 65001 >nul",
            "setlocal enableextensions",
            *list(script_lines),
            "exit /b %ERRORLEVEL%",
        ]
    )
    script_path.write_text(full_text, encoding="utf-8", newline="\n")
    return script_path


def write_unstoppable_job_file(
    artifacts: OperationArtifacts,
    *,
    sources: tuple[Path, ...],
    target_dir: Path,
    use_extended_paths: bool,
) -> Path:
    """Write the UTF-16 UCB job file consumed by Unstoppable Copier."""
    job_path = artifacts.job_dir / "unstoppable.ucb"
    lines = [
        (
            f"{to_windows_arg_path(source, use_extended_paths=use_extended_paths)}"
            f"|{to_windows_arg_path(target_dir, use_extended_paths=use_extended_paths)}"
        )
        for source in sources
    ]
    payload = "\r\n".join(lines)
    if payload:
        payload = f"{payload}\r\n"
    job_path.write_text(payload, encoding="utf-16", newline="")
    return job_path


def run_script(
    script_path: Path,
    log_path: Path,
    *,
    cmd_path: str,
    wait: bool,
) -> OperationResult:
    """Run a prepared launcher script and return its execution result."""
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
    creationflags = int(getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    process = subprocess.Popen(
        [cmd_executable, "/d", "/c", str(script_path)],
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
        return OperationResult(
            status="succeeded", message="Script completed.", processed_count=0
        )
    return OperationResult(
        status="failed",
        message=f"Script failed with exit code {code}.",
        processed_count=0,
    )


def expand_template(
    template: str,
    *,
    kind: str,
    sources: tuple[Path, ...],
    target_dir: Path | None,
    use_extended_paths: bool,
) -> str:
    """Expand operation placeholders into an executor argument template."""
    source_literals = " ".join(
        quoted(to_windows_arg_path(path, use_extended_paths=use_extended_paths))
        for path in sources
    )
    first_source = (
        quoted(to_windows_arg_path(sources[0], use_extended_paths=use_extended_paths))
        if sources
        else ""
    )
    target_literal = (
        quoted(to_windows_arg_path(target_dir, use_extended_paths=use_extended_paths))
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
