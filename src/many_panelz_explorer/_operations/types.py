from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path


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
DEFAULT_UNSTOPPABLE_ARGS = ""
DEFAULT_GENERIC_COPYMOVE_EXE = ""
DEFAULT_GENERIC_COPYMOVE_ARGS = "{operation} {sources} {target}"
DEFAULT_GENERIC_DELETE_EXE = ""
DEFAULT_GENERIC_DELETE_ARGS = "{operation} {sources}"
DEFAULT_ROBOCOPY_COPY_ARGS = "/E /R:0 /W:0"
DEFAULT_ROBOCOPY_MOVE_ARGS = "/E /MOVE /R:0 /W:0"
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


def utcnow() -> datetime:
    return datetime.now(UTC)
