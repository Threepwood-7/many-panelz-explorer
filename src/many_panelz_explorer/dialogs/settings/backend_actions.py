"""Backend executable and test helpers for the settings dialog."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QLineEdit, QMessageBox

from ..._operations.backend_options import resolve_copy_move_backend_args
from ..._operations.discovery import (
    discover_single_companion_tool,
    resolve_companion_tool_paths,
    resolve_system_command_paths,
)
from ..._operations.executors import execute_operation_request
from ..._operations.types import (
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationKind,
    OperationRequest,
)
from ..._settings import normalize as settings_normalize
from ...runtime_text import write_runtime_lines

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def browse_executable(dialog: SettingsDialog, edit: QLineEdit) -> None:
    """Browse for an executable path and normalize the selected text."""

    selected, _ = QFileDialog.getOpenFileName(
        dialog,
        "Select Executable",
        str(Path.home()),
        "Executable Files (*.exe *.cmd *.bat);;All Files (*.*)",
    )
    if not selected:
        return
    edit.setText(settings_normalize.normalize_windows_path_text(selected, fallback=""))
    dialog.on_controls_changed()


def find_executable(
    dialog: SettingsDialog,
    edit: QLineEdit,
    *,
    default_executable: str,
) -> None:
    """Resolve a configured executable path from the local system."""

    resolved = discover_single_companion_tool(
        configured=edit.text().strip(),
        default_executable=default_executable,
    )
    edit.setText(resolved)
    dialog.on_controls_changed()


def reset_command_controls(
    dialog: SettingsDialog,
    executable_edit: QLineEdit,
    args_edit: QLineEdit,
    *,
    default_executable: str,
    default_args: str,
) -> None:
    """Reset a command row to its default executable and argument values."""

    executable_edit.setText(default_executable)
    args_edit.setText(default_args)
    dialog.on_controls_changed()


def test_backend(
    dialog: SettingsDialog,
    kind: OperationKind,
    backend_id: str,
) -> None:
    """Execute a backend smoke test using temporary sample paths."""

    dialog.on_controls_changed()
    root = (
        Path(tempfile.gettempdir()) / "many_panelz_explorer_op_tests" / uuid.uuid4().hex
    )
    root.mkdir(parents=True, exist_ok=True)
    sources, target_dir = create_test_paths(root, kind=kind)
    request_kind: OperationKind = "delete" if kind == "delete" else "copy"
    request = OperationRequest(
        kind=request_kind,
        sources=tuple(sources),
        target_dir=target_dir,
        backend_id=backend_id,
        dispatch_mode="run_now_wait",
        conflict_policy=dialog.working_preferences.default_operation_conflict_policy,
        backend_options={},
        created_by="settings-dialog:test-backend",
    )
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifacts = OperationArtifacts(
        job_dir=artifacts_dir,
        metadata_path=artifacts_dir / "job.json",
        log_path=artifacts_dir / "output.log",
    )
    result = execute_operation_request(
        request,
        wait=True,
        preferences=operation_execution_preferences_from_working(dialog),
        artifacts=artifacts,
    )
    details = (
        f"Backend: {backend_id}\n"
        f"Status: {result.status}\n"
        f"Message: {result.message}\n"
        f"Processed: {result.processed_count}\n"
        f"Test root: {root}\n"
        f"Artifacts: {artifacts_dir}"
    )
    if result.status in {"succeeded", "dispatched"}:
        QMessageBox.information(dialog, "Backend Test Result", details)
        return
    QMessageBox.warning(dialog, "Backend Test Failed", details)


def create_test_paths(
    root: Path,
    *,
    kind: OperationKind,
) -> tuple[list[Path], Path | None]:
    """Create sample file and directory paths for a backend smoke test."""

    if kind in {"copy", "move"}:
        source_root = root / "source"
        source_root.mkdir(parents=True, exist_ok=True)
        sample_file = source_root / "sample-file.txt"
        write_runtime_lines(sample_file, ["many-panelz test"], trailing_newline=True)
        sample_dir = source_root / "sample-dir"
        sample_dir.mkdir(parents=True, exist_ok=True)
        write_runtime_lines(
            sample_dir / "nested.txt",
            ["nested"],
            trailing_newline=True,
        )
        target_dir = root / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        return [sample_file, sample_dir], target_dir

    delete_root = root / "delete-source"
    delete_root.mkdir(parents=True, exist_ok=True)
    sample_file = delete_root / "to-delete.txt"
    write_runtime_lines(sample_file, ["delete me"], trailing_newline=True)
    sample_dir = delete_root / "to-delete-dir"
    sample_dir.mkdir(parents=True, exist_ok=True)
    write_runtime_lines(
        sample_dir / "nested.txt",
        ["delete nested"],
        trailing_newline=True,
    )
    return [sample_file, sample_dir], None


def operation_execution_preferences_from_working(
    dialog: SettingsDialog,
) -> OperationExecutionPreferences:
    """Resolve executor preferences from the dialog's working settings."""

    preferences = dialog.working_preferences
    resolved_cmd, resolved_robocopy = resolve_system_command_paths()
    resolved_copy_move = resolve_copy_move_backend_args(
        robocopy_options=preferences.robocopy_structured_options,
        teracopy_options=preferences.teracopy_structured_options,
        unstoppable_options=preferences.unstoppable_structured_options,
        external_copymove_options=preferences.external_copymove_structured_options,
    )
    base = OperationExecutionPreferences(
        default_copy_move_backend=preferences.default_copy_move_backend,
        default_delete_backend=preferences.default_delete_backend,
        default_dispatch_mode=preferences.default_operation_dispatch_mode,
        default_conflict_policy=preferences.default_operation_conflict_policy,
        shortcut_behavior=preferences.operation_shortcut_behavior,
        queue_view_mode=preferences.operation_queue_view_mode,
        default_editor_executable=preferences.default_editor_executable,
        default_viewer_executable=preferences.default_viewer_executable,
        file_open_overrides_json=preferences.file_open_overrides_json,
        use_extended_paths_robocopy=preferences.use_extended_paths_robocopy,
        use_extended_paths_teracopy=preferences.use_extended_paths_teracopy,
        use_extended_paths_unstoppable=preferences.use_extended_paths_unstoppable,
        use_extended_paths_external_copymove=preferences.use_extended_paths_external_copymove,
        use_extended_paths_cmd_delete=preferences.use_extended_paths_cmd_delete,
        use_extended_paths_powershell_delete=preferences.use_extended_paths_powershell_delete,
        use_extended_paths_rimraf=preferences.use_extended_paths_rimraf,
        use_extended_paths_external_delete=preferences.use_extended_paths_external_delete,
        teracopy_executable=preferences.teracopy_executable,
        teracopy_args_template=resolved_copy_move.teracopy_args_template,
        unstoppable_executable=preferences.unstoppable_executable,
        unstoppable_args_template=resolved_copy_move.unstoppable_args_template,
        generic_copymove_executable=preferences.generic_copymove_executable,
        generic_copymove_args_template=resolved_copy_move.external_copymove_args_template,
        generic_delete_executable=preferences.generic_delete_executable,
        generic_delete_args_template=preferences.generic_delete_args_template,
        robocopy_copy_args=resolved_copy_move.robocopy_copy_args,
        robocopy_move_args=resolved_copy_move.robocopy_move_args,
        cmd_delete_args=preferences.cmd_delete_args,
        powershell_delete_args=preferences.powershell_delete_args,
        rimraf_executable=preferences.rimraf_executable,
        rimraf_args_template=preferences.rimraf_args_template,
        resolved_cmd_path=resolved_cmd,
        resolved_robocopy_path=resolved_robocopy,
    )
    return resolve_companion_tool_paths(base)
