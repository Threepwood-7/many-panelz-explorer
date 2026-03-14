"""Context-menu and file action helpers for a single explorer tab."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QItemSelectionModel, QObject, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
)

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

    def open_context_menu_from_keyboard(self) -> None:
        """Open the file-list context menu near the current row."""

        current_index = self._tab.view.currentIndex()
        current_rect = self._tab.view.visualRect(current_index)
        if current_index.isValid() and current_rect.isValid():
            self.open_context_menu(current_rect.center())
            return
        self.open_context_menu(self._tab.view.viewport().rect().center())

    def open_path(self, path: Path) -> None:
        target = Path(path)
        if target.is_dir():
            self._tab.navigation.set_path(target)
            return
        self._run_action(lambda: file_ops.open_with_default(target))

    def open_selected_or_current(self) -> None:
        """Open selected files, or the current row when nothing is selected."""

        targets = self._selected_or_current_paths()
        if not targets:
            return
        files = [path for path in targets if path.is_file()]
        directories = [path for path in targets if path.is_dir()]
        if files:

            def _open_files() -> None:
                for path in files:
                    file_ops.open_with_default(path)

            self._run_action(_open_files)
            return
        if len(directories) == 1:
            self._tab.navigation.set_path(directories[0])

    def view_selected_or_current(self) -> None:
        """Open selected files in a dedicated viewer when configured."""

        targets = self._selected_or_current_paths()
        if not targets:
            return
        files = [path for path in targets if path.is_file()]
        directories = [path for path in targets if path.is_dir()]
        if files:
            fallback_used = False

            def _open_targets() -> None:
                nonlocal fallback_used
                for path in files:
                    if not file_ops.open_with_viewer(path):
                        fallback_used = True
                        file_ops.open_with_default(path)

            self._run_action(_open_targets)
            if fallback_used:
                self._show_status_message(
                    "No dedicated viewer configured; used default opener.",
                    2200,
                )
            return
        if len(directories) == 1:
            self._tab.navigation.set_path(directories[0])

    def edit_selected_or_current(self) -> None:
        """Edit selected files, or the current file when nothing is selected."""

        files = [path for path in self._selected_or_current_paths() if path.is_file()]
        if not files:
            return

        def _open_files() -> None:
            for path in files:
                file_ops.open_in_text_editor(path)

        self._run_action(_open_files)

    def create_new_text_file_and_edit(self) -> None:
        """Prompt for a new text file name, create it, and open it in the editor."""

        name, ok = QInputDialog.getText(
            self._tab,
            "New text file",
            "File name:",
            text="New File.txt",
        )
        if not ok or not name.strip():
            return

        def _create_and_open() -> None:
            created = file_ops.create_text_file(self._tab.navigation.path, name.strip())
            self._tab.navigation.set_path(
                self._tab.navigation.path,
                push_history=False,
                selection_hint=created,
            )
            file_ops.open_in_text_editor(created)

        self._run_action(_create_and_open)

    def copy_selected_item_or_panel_path(self) -> None:
        """Copy a selected path, or fall back to the active panel path."""

        selected = self._selected_real_paths()
        if len(selected) == 1:
            self._copy_text_to_clipboard(str(selected[0]))
            return
        self._copy_text_to_clipboard(str(self._tab.navigation.path))
        self._show_status_message("Copied panel path to clipboard.", 1800)

    def select_all_items(self) -> None:
        """Select all real filesystem rows in the current file list."""

        selection_model = self._tab.view.selectionModel()
        selection_model.clearSelection()
        root_index = self._tab.view.rootIndex()
        flags = (
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows
        )
        for row in range(self._tab.model.rowCount(root_index)):
            index = self._tab.model.index(row, 0, root_index)
            if not index.isValid() or self._tab.model.is_parent_index(index):
                continue
            selection_model.select(index, flags)
        last_index = self._tab.view.currentIndex()
        if last_index.isValid() and not self._tab.model.is_parent_index(last_index):
            selection_model.setCurrentIndex(last_index, flags)

    def create_directory(self) -> None:
        """Prompt for and create a new directory in the current path."""

        self._new_folder()

    def create_zip_from_selection(self) -> None:
        """Launch the ZIP creation flow for the current selection."""

        self._zip_create()

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

    def _selected_real_paths(self) -> list[Path]:
        selected: list[Path] = []
        selection_model = self._tab.view.selectionModel()
        for index in selection_model.selectedRows():
            if not index.isValid() or self._tab.model.is_parent_index(index):
                continue
            file_path = self._tab.model.filePath(index)
            if file_path:
                selected.append(Path(file_path))
        return selected

    def _selected_or_current_paths(self) -> list[Path]:
        selected = self._selected_real_paths()
        if selected:
            return selected
        current_index = self._tab.view.currentIndex()
        if not current_index.isValid() or self._tab.model.is_parent_index(
            current_index
        ):
            return []
        file_path = self._tab.model.filePath(current_index)
        if not file_path:
            return []
        return [Path(file_path)]

    def _copy_text_to_clipboard(self, value: str) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(str(value or ""))

    def _show_status_message(self, message: str, timeout_ms: int) -> None:
        window = self._tab.window()
        if isinstance(window, QMainWindow):
            window.statusBar().showMessage(message, timeout_ms)

    def _run_and_refresh(self, action: Callable[[], object]) -> None:
        self._run_action(action)
        self._tab.navigation.refresh()

    def _run_action(self, action: Callable[[], object]) -> None:
        try:
            action()
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self._tab, "Operation failed", str(exc))
