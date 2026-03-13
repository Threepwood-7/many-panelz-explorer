"""Window-level coordination for copy, move, and delete actions."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from PySide6.QtWidgets import QMessageBox

from ..._operations.path_helpers import to_windows_long_path
from ..._operations.types import (
    SHORTCUT_BEHAVIOR_DIALOG,
    OperationKind,
    OperationRequest,
)
from .panels import resolve_window_target_panel_id

if TYPE_CHECKING:
    from ...window import ExplorerWindow


type ConflictChoice = Literal["overwrite", "skip", "rename", "cancel"]


class WindowOperationsCoordinator:
    """Coordinate file operations initiated from an explorer window."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Store the owning window reference."""
        self.window = window

    def delete_selected_items(self, configure: bool = False) -> None:
        panel = self.window.panels_coordinator.active_panel()
        if panel is None:
            return
        tab = panel.current_tab()
        if tab is None:
            return
        selected = tab.selected_paths()
        if not selected:
            self.window.statusBar().showMessage(
                "No items selected in source pane.", 3000
            )
            return

        request = self.build_operation_request(
            kind="delete",
            sources=[Path(path) for path in selected],
            target_dir=None,
            configure=configure,
        )
        if request is None:
            return
        job = self.window.controller.operation_queue_manager.submit(request)
        self.window.statusBar().showMessage(
            f"Delete job {job.job_id[:8]}: {job.status}.",
            3500,
        )
        if job.status in {"succeeded", "failed", "cancelled"}:
            panel.navigation_coordinator.refresh_current_path()

    def transfer_selected_to_target(
        self, *, move: bool, configure: bool = False
    ) -> None:
        source_panel = self.window.panels_coordinator.active_panel()
        source_id = self.window.active_panel_id
        if source_panel is None or source_id is None:
            return
        source_tab = source_panel.current_tab()
        if source_tab is None:
            return

        selected = source_tab.selected_paths()
        if not selected:
            self.window.statusBar().showMessage(
                "No items selected in source pane.", 3000
            )
            return

        target_id = resolve_window_target_panel_id(self.window, source_id)
        if target_id is None:
            QMessageBox.information(
                self.window,
                "Target Pane",
                "No target pane is available. Create another pane first.",
            )
            return
        target_panel = self.window.panel_widgets.get(target_id)
        if target_panel is None:
            return
        destination = target_panel.current_path()

        kind = "move" if move else "copy"
        request = self.build_operation_request(
            kind=kind,
            sources=[Path(path) for path in selected],
            target_dir=destination,
            configure=configure,
        )
        if request is None:
            return
        job = self.window.controller.operation_queue_manager.submit(request)
        verb = "Move" if move else "Copy"
        self.window.statusBar().showMessage(
            f"{verb} job {job.job_id[:8]}: {job.status}.",
            3500,
        )
        if job.status in {"succeeded", "failed", "cancelled"}:
            source_panel.navigation_coordinator.refresh_current_path()
            target_panel.navigation_coordinator.refresh_current_path()

    def build_operation_request(
        self,
        *,
        kind: OperationKind,
        sources: list[Path],
        target_dir: Path | None,
        configure: bool,
    ) -> OperationRequest | None:
        ui_preferences = self.window.settings.ui_preferences()
        use_dialog = bool(configure) or (
            self.window.preferences_coordinator.operation_shortcut_behavior
            == SHORTCUT_BEHAVIOR_DIALOG
        )
        if use_dialog:
            from ...dialogs.operation_dialog import OperationDialog

            dialog = OperationDialog(
                kind=kind,
                sources=sources,
                target_dir=target_dir,
                preferences=ui_preferences,
                parent=self.window,
            )
            if dialog.exec() != dialog.DialogCode.Accepted:
                return None
            return dialog.build_request(
                kind=kind,
                sources=sources,
                target_dir=target_dir,
                created_by=f"window:{self.window.window_id}",
            )

        backend_id = (
            self.window.preferences_coordinator.default_delete_backend
            if kind == "delete"
            else self.window.preferences_coordinator.default_copy_move_backend
        )
        return OperationRequest(
            kind=kind,
            sources=tuple(sources),
            target_dir=target_dir,
            backend_id=backend_id,
            dispatch_mode=self.window.preferences_coordinator.default_operation_dispatch_mode,
            conflict_policy=self.window.preferences_coordinator.default_operation_conflict_policy,
            created_by=f"window:{self.window.window_id}",
        )

    def copy_or_move_one(
        self, *, source: Path, destination_dir: Path, move: bool
    ) -> Literal["done", "skip", "cancel"]:
        destination_dir = Path(destination_dir)
        destination = destination_dir / source.name
        if destination.exists():
            choice = self.prompt_conflict_resolution(source, destination)
            if choice == "cancel":
                return "cancel"
            if choice == "skip":
                return "skip"
            if choice == "rename":
                destination = self.next_available_path(destination_dir, source.name)
            elif choice == "overwrite":
                if source.resolve() == destination.resolve():
                    return "skip"
                self.remove_existing_path(destination)
        try:
            source_raw = to_windows_long_path(source)
            destination_raw = to_windows_long_path(destination)
            if move:
                shutil.move(source_raw, destination_raw)
            else:
                if source.is_dir():
                    shutil.copytree(source_raw, destination_raw)
                else:
                    shutil.copy2(source_raw, destination_raw)
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self.window, "File Operation Failed", str(exc))
            return "cancel"
        return "done"

    def prompt_conflict_resolution(
        self, source: Path, destination: Path
    ) -> ConflictChoice:
        dialog = QMessageBox(self.window)
        dialog.setWindowTitle("Name Conflict")
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(
            f'"{destination.name}" already exists in target pane.\n\n'
            f"Source: {source}\nTarget: {destination}"
        )
        overwrite_button = dialog.addButton(
            "Overwrite", QMessageBox.ButtonRole.AcceptRole
        )
        skip_button = dialog.addButton("Skip", QMessageBox.ButtonRole.ActionRole)
        rename_button = dialog.addButton("Rename", QMessageBox.ButtonRole.ActionRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is overwrite_button:
            return "overwrite"
        if clicked is skip_button:
            return "skip"
        if clicked is rename_button:
            return "rename"
        _ = cancel_button
        return "cancel"

    def next_available_path(self, destination_dir: Path, base_name: str) -> Path:
        candidate = destination_dir / base_name
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while True:
            candidate = destination_dir / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def remove_existing_path(self, path: Path) -> None:
        raw = to_windows_long_path(path)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(raw)
            return
        Path(raw).unlink()
