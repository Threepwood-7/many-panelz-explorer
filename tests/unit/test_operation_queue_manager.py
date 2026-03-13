"""Tests for operation queue failure handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from many_panelz_explorer._operations import queue_manager
from many_panelz_explorer._operations.types import (
    BACKEND_PYTHON,
    DISPATCH_MODE_RUN_WAIT,
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationRequest,
    OperationResult,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_run_wait_records_exception_type_and_traceback(
    monkeypatch, tmp_path: Path
) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir(parents=True, exist_ok=True)
    artifacts = OperationArtifacts(
        job_dir=job_dir,
        metadata_path=job_dir / "job.json",
        log_path=job_dir / "output.log",
        script_path=None,
    )

    def _prepare_artifacts(_job_id: str) -> OperationArtifacts:
        return artifacts

    def _raise_executor(
        _request: OperationRequest,
        *,
        wait: bool,
        preferences: OperationExecutionPreferences,
        artifacts: OperationArtifacts,
    ) -> OperationResult:
        del wait, preferences, artifacts
        raise ValueError("boom")

    monkeypatch.setattr(queue_manager, "prepare_artifacts", _prepare_artifacts)
    monkeypatch.setattr(queue_manager, "execute_operation_request", _raise_executor)

    manager = queue_manager.OperationQueueManager(
        preferences=OperationExecutionPreferences()
    )
    request = OperationRequest(
        kind="copy",
        sources=(tmp_path / "source.txt",),
        target_dir=tmp_path / "target",
        backend_id=BACKEND_PYTHON,
        dispatch_mode=DISPATCH_MODE_RUN_WAIT,
        conflict_policy="rename",
    )

    job = manager.submit(request)

    assert job.status == "failed"
    assert job.message == "ValueError: boom"
    log_text = artifacts.log_path.read_text(encoding="utf-8")
    assert "Executor failure:" in log_text
    assert "Traceback" in log_text
    assert "ValueError: boom" in log_text
