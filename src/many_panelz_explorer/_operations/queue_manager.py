"""Operation queue execution and lifecycle management."""

from __future__ import annotations

import threading
import uuid
from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from .artifacts import prepare_artifacts, write_exception_log, write_metadata
from .executors import execute_operation_request
from .types import (
    DISPATCH_MODE_LAUNCH_NO_WAIT,
    DISPATCH_MODE_RUN_WAIT,
    OperationExecutionPreferences,
    OperationJob,
    OperationRequest,
    utcnow,
)

if TYPE_CHECKING:
    import subprocess


class OperationQueueManager(QObject):
    """Queue and execute file-operation jobs for the window UI."""

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
            created_at=utcnow(),
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
                    replace(
                        job, status="running", started_at=utcnow(), message="Running"
                    )
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
                cancelled = replace(
                    job,
                    status="cancelled",
                    message="Cancelled while queued.",
                    completed_at=utcnow(),
                )
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
        running = replace(job, status="running", started_at=utcnow(), message="Running")
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
        artifacts = prepare_artifacts(job.job_id)
        running = replace(
            job, artifacts=artifacts, started_at=job.started_at or utcnow()
        )
        write_metadata(running, artifacts)
        try:
            result = execute_operation_request(
                running.request,
                wait=wait,
                preferences=self._preferences,
                artifacts=artifacts,
            )
        except Exception as exc:
            write_exception_log(artifacts, exc)
            failed = replace(
                running,
                status="failed",
                message=f"{type(exc).__name__}: {exc}",
                completed_at=utcnow(),
            )
            write_metadata(failed, artifacts)
            return failed

        final = replace(
            running,
            status=result.status,
            message=result.message,
            processed_count=result.processed_count,
            pid=result.pid,
            completed_at=utcnow() if result.status != "dispatched" else None,
        )
        write_metadata(final, artifacts)
        return final
