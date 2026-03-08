from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .path_helpers import quoted, to_windows_arg_path
from .types import OperationArtifacts, OperationKind, OperationJob, OperationResult


def ensure_artifacts_root() -> Path:
    root = Path(tempfile.gettempdir()) / "many_panelz_explorer_ops"
    root.mkdir(parents=True, exist_ok=True)
    return root


def prepare_artifacts(job_id: str) -> OperationArtifacts:
    root = ensure_artifacts_root()
    job_dir = root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = job_dir / "job.json"
    log_path = job_dir / "output.log"
    return OperationArtifacts(job_dir=job_dir, metadata_path=metadata_path, log_path=log_path)


def write_metadata(job: OperationJob, artifacts: OperationArtifacts) -> None:
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


def write_script(artifacts: OperationArtifacts, script_lines: list[str]) -> Path:
    script_path = artifacts.job_dir / "run.cmd"
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


def run_script(
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
    command = quoted(str(script_path))
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


def expand_template(
    template: str,
    *,
    kind: OperationKind,
    sources: tuple[Path, ...],
    target_dir: Path | None,
    use_extended_paths: bool,
) -> str:
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
