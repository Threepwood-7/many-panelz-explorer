"""Context-menu and file action helpers for a single explorer tab."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox

from . import file_ops
from .dialogs.properties_dialog import PropertiesDialog

if TYPE_CHECKING:
    from collections.abc import Callable

    from .explorer_tab import ExplorerTab


class ExplorerTabActions(QObject):
    """Own context-menu actions and file operations for an explorer tab."""

    def __init__(self, tab: ExplorerTab, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tab = tab

    def open_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self._tab)
        for text, handler in self._menu_specs():
            if text is None:
                menu.addSeparator()
                continue
            action = QAction(text, self._tab)
            action.triggered.connect(handler)
            menu.addAction(action)
        menu.exec(self._tab.view.viewport().mapToGlobal(pos))

    def open_path(self, path: Path) -> None:
        target = Path(path)
        if target.is_dir():
            self._tab.navigation.set_path(target)
            return
        self._run_action(lambda: file_ops.open_with_default(target))

    def _menu_specs(self) -> list[tuple[str | None, Callable[[], None]]]:
        return [
            ("Open", self._open_selected),
            ("Rename", self._rename_selected),
            ("New folder", self._new_folder),
            (None, self._open_selected),
            ("Copy", self._copy_selected),
            ("Cut", self._cut_selected),
            ("Paste", self._paste_into_current),
            ("Move...", self._move_selected),
            ("Delete", self._delete_selected),
            (None, self._open_selected),
            ("Properties", self._show_properties),
            ("Create ZIP...", self._zip_create),
            ("Extract ZIP...", self._zip_extract),
            ("Open terminal here", self._open_terminal),
        ]

    def _open_selected(self) -> None:
        for path in self._tab.selected_paths():
            if path.is_dir():
                self._tab.navigation.set_path(path)
                continue
            self._run_action(lambda p=path: file_ops.open_with_default(p))

    def _rename_selected(self) -> None:
        selected = self._tab.selected_paths()
        if len(selected) != 1:
            return
        source = selected[0]
        name, ok = QInputDialog.getText(
            self._tab,
            "Rename",
            "New name:",
            text=source.name,
        )
        if not ok or not name.strip():
            return
        self._run_and_refresh(lambda: file_ops.rename_path(source, name.strip()))

    def _new_folder(self) -> None:
        name, ok = QInputDialog.getText(
            self._tab,
            "New folder",
            "Folder name:",
            text="New Folder",
        )
        if not ok or not name.strip():
            return
        self._run_and_refresh(
            lambda: file_ops.create_folder(self._tab.navigation.path, name.strip())
        )

    def _copy_selected(self) -> None:
        selected = self._tab.selected_paths()
        if selected:
            file_ops.set_clipboard(selected, cut=False)

    def _cut_selected(self) -> None:
        selected = self._tab.selected_paths()
        if selected:
            file_ops.set_clipboard(selected, cut=True)

    def _paste_into_current(self) -> None:
        self._run_and_refresh(lambda: file_ops.paste_items(self._tab.navigation.path))

    def _move_selected(self) -> None:
        selected = self._tab.selected_paths()
        if not selected:
            return
        dest = QFileDialog.getExistingDirectory(
            self._tab,
            "Move items",
            str(self._tab.navigation.path),
        )
        if not dest:
            return
        self._run_and_refresh(lambda: file_ops.move_items(selected, Path(dest)))

    def _delete_selected(self) -> None:
        selected = self._tab.selected_paths()
        if not selected:
            return
        names = "\n".join(path.name for path in selected[:10])
        confirm = QMessageBox.question(
            self._tab,
            "Delete to Recycle Bin",
            f"Move selected items to Recycle Bin?\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._run_and_refresh(lambda: file_ops.delete_to_recycle_bin(selected))

    def _show_properties(self) -> None:
        selected = self._tab.selected_paths()
        if len(selected) != 1:
            return
        dialog = PropertiesDialog(
            selected[0],
            self._tab,
            size_formatter=self._tab.properties_size_formatter,
        )
        dialog.exec()

    def _zip_create(self) -> None:
        selected = self._tab.selected_paths()
        if not selected:
            return
        default_name = (
            f"{selected[0].name}.zip" if len(selected) == 1 else "archive.zip"
        )
        target, _ = QFileDialog.getSaveFileName(
            self._tab,
            "Create ZIP",
            str(self._tab.navigation.path / default_name),
            "ZIP Files (*.zip)",
        )
        if not target:
            return
        self._run_action(lambda: file_ops.zip_create(selected, Path(target)))

    def _zip_extract(self) -> None:
        selected = self._tab.selected_paths()
        if len(selected) != 1:
            return
        archive = selected[0]
        if archive.suffix.lower() != ".zip":
            return
        target = QFileDialog.getExistingDirectory(
            self._tab,
            "Extract ZIP",
            str(self._tab.navigation.path),
        )
        if not target:
            return
        self._run_and_refresh(lambda: file_ops.zip_extract(archive, Path(target)))

    def _open_terminal(self) -> None:
        self._run_action(lambda: file_ops.open_terminal_here(self._tab.navigation.path))

    def _run_and_refresh(self, action: Callable[[], object]) -> None:
        self._run_action(action)
        self._tab.navigation.refresh()

    def _run_action(self, action: Callable[[], object]) -> None:
        try:
            action()
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self._tab, "Operation failed", str(exc))
