from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import (
    QDir,
    QEvent,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QAction, QKeyEvent, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from . import file_ops
from .dialogs.properties_dialog import PropertiesDialog
from .fast_dir_model import FastDirModel

if TYPE_CHECKING:
    from collections.abc import Callable


class ExplorerTab(QWidget):
    path_changed = Signal(str)
    history_changed = Signal(bool, bool)
    column_widths_changed = Signal(list)

    def __init__(
        self,
        initial_path: Path,
        show_hidden: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tab_uuid = uuid.uuid4().hex
        self._history: list[Path] = []
        self._history_index = -1
        self._show_hidden = show_hidden
        self._selection_memory: dict[str, Path] = {}
        self._selection_restore_token = 0
        self._syncing_column_widths = False
        self._pending_column_widths: list[int] = []
        self._show_parent_entry = True
        self._inline_filter_text = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.model = FastDirModel(self)
        self.model.setReadOnly(False)
        self._apply_hidden_filter()
        self.model.directoryLoaded.connect(self._on_directory_loaded)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setRootIsDecorated(False)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._open_context_menu)
        self.view.doubleClicked.connect(self._on_item_activated)
        self.view.activated.connect(self._on_item_activated)
        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(False)
        self.view.setDropIndicatorShown(False)
        self.view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.view.setSortingEnabled(True)
        self.view.header().sectionResized.connect(self._on_column_resized)
        self.view.installEventFilter(self)

        root.addWidget(self.view)

        self._alt_left_shortcut = QShortcut("Alt+Left", self)
        self._alt_left_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._alt_left_shortcut.activated.connect(self.go_back)

        self._alt_right_shortcut = QShortcut("Alt+Right", self)
        self._alt_right_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._alt_right_shortcut.activated.connect(self.go_forward)

        self._alt_up_shortcut = QShortcut("Alt+Up", self)
        self._alt_up_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._alt_up_shortcut.activated.connect(self.go_up)

        self.set_path(initial_path)
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    @property
    def tab_uuid(self) -> str:
        return self._tab_uuid

    def current_path(self) -> Path:
        if not self._history:
            return Path.home()
        return self._history[self._history_index]

    def serialize_state(self) -> dict[str, str]:
        return {"path": str(self.current_path())}

    def set_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        self._apply_hidden_filter()
        self.refresh()

    def set_path(
        self,
        path: Path,
        *,
        push_history: bool = True,
        selection_hint: Path | None = None,
    ) -> None:
        previous_path = self.current_path() if self._history else None
        if previous_path is not None:
            self._remember_selection_for_path(previous_path)

        target = Path(path).expanduser()
        if not target.exists() or not target.is_dir():
            target = Path.home()
        self._show_parent_entry = self._should_show_parent_entry(target)
        self._apply_hidden_filter()

        if push_history:
            if self._history and self._history[self._history_index] == target:
                pass
            else:
                self._history = self._history[: self._history_index + 1]
                self._history.append(target)
                self._history_index = len(self._history) - 1
        elif not self._history:
            self._history = [target]
            self._history_index = 0

        index = self.model.setRootPath(str(target))
        self.view.setRootIndex(index)
        self._restore_selection_for_path(target, preferred=selection_hint)
        self.path_changed.emit(str(target))
        self._emit_history_state()

    def refresh(self) -> None:
        self.set_path(self.current_path(), push_history=False)

    def set_inline_filter(self, text: str) -> None:
        normalized = str(text or "").strip()
        if normalized == self._inline_filter_text:
            return
        self._inline_filter_text = normalized
        if self._inline_filter_text:
            self.model.setNameFilterDisables(False)
            self.model.setNameFilters([f"*{self._inline_filter_text}*"])
        else:
            self.model.setNameFilters([])
            self.model.setNameFilterDisables(True)

    def clear_inline_filter(self) -> None:
        self.set_inline_filter("")

    def inline_filter_text(self) -> str:
        return self._inline_filter_text

    def go_back(self) -> None:
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self.set_path(self._history[self._history_index], push_history=False)

    def go_forward(self) -> None:
        if self._history_index < 0:
            return
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self.set_path(self._history[self._history_index], push_history=False)

    def go_up(self) -> None:
        current = self.current_path()
        parent = current.parent
        if parent != current:
            self.set_path(parent, selection_hint=current)

    def can_go_back(self) -> bool:
        return self._history_index > 0

    def can_go_forward(self) -> bool:
        return self._history_index >= 0 and self._history_index < len(self._history) - 1

    def history_snapshot(self) -> tuple[list[Path], int]:
        return list(self._history), self._history_index

    def go_to_history_index(self, index: int) -> None:
        if index < 0 or index >= len(self._history):
            return
        self._history_index = index
        self.set_path(self._history[self._history_index], push_history=False)

    def selected_paths(self) -> list[Path]:
        rows = self.view.selectionModel().selectedRows()
        paths: list[Path] = []
        for idx in rows:
            if self.model.is_parent_index(idx):
                continue
            file_path = self.model.filePath(idx)
            if file_path:
                paths.append(Path(file_path))
        return paths

    def column_widths(self) -> list[int]:
        header = self.view.header()
        return [
            header.sectionSize(column) for column in range(self.model.columnCount())
        ]

    def apply_column_widths(self, widths: list[int]) -> None:
        if not widths:
            return
        normalized = [int(width) for width in widths if int(width) > 0]
        if not normalized:
            return
        self._pending_column_widths = list(normalized)
        self._apply_column_widths_once(normalized)

    def _apply_column_widths_once(self, widths: list[int]) -> None:
        self._syncing_column_widths = True
        try:
            for column, width in enumerate(widths[: self.model.columnCount()]):
                if int(width) > 0:
                    self.view.setColumnWidth(column, int(width))
        finally:
            self._syncing_column_widths = False

    def _on_item_activated(self, index: QModelIndex) -> None:
        file_path = self.model.filePath(index)
        if not file_path:
            return
        path = Path(file_path)
        if path.is_dir():
            self.set_path(path)
            return
        self._run_action(lambda: file_ops.open_with_default(path))

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.view and event.type() == QEvent.Type.KeyPress:
            key_event = cast("QKeyEvent", event)
            modifiers = key_event.modifiers()
            key = key_event.key()
            if modifiers == Qt.KeyboardModifier.AltModifier and key == int(
                Qt.Key.Key_Left
            ):
                self.go_back()
                return True
            if modifiers == Qt.KeyboardModifier.AltModifier and key == int(
                Qt.Key.Key_Right
            ):
                self.go_forward()
                return True
            if modifiers == Qt.KeyboardModifier.AltModifier and key == int(
                Qt.Key.Key_Up
            ):
                self.go_up()
                return True
            if modifiers == Qt.KeyboardModifier.NoModifier and key == int(
                Qt.Key.Key_Left
            ):
                self.go_up()
                return True
            if modifiers == Qt.KeyboardModifier.NoModifier and key == int(
                Qt.Key.Key_Backspace
            ):
                self.go_up()
                return True
            if modifiers == Qt.KeyboardModifier.NoModifier and key == int(
                Qt.Key.Key_Right
            ):
                index = self.view.currentIndex()
                if index.isValid():
                    self._on_item_activated(index)
                return True
        return super().eventFilter(obj, event)

    def _open_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self._open_selected)
        menu.addAction(open_action)

        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(self._rename_selected)
        menu.addAction(rename_action)

        new_folder_action = QAction("New folder", self)
        new_folder_action.triggered.connect(self._new_folder)
        menu.addAction(new_folder_action)

        menu.addSeparator()

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self._copy_selected)
        menu.addAction(copy_action)

        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self._cut_selected)
        menu.addAction(cut_action)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self._paste_into_current)
        menu.addAction(paste_action)

        move_action = QAction("Move...", self)
        move_action.triggered.connect(self._move_selected)
        menu.addAction(move_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)

        menu.addSeparator()

        properties_action = QAction("Properties", self)
        properties_action.triggered.connect(self._show_properties)
        menu.addAction(properties_action)

        zip_create_action = QAction("Create ZIP...", self)
        zip_create_action.triggered.connect(self._zip_create)
        menu.addAction(zip_create_action)

        zip_extract_action = QAction("Extract ZIP...", self)
        zip_extract_action.triggered.connect(self._zip_extract)
        menu.addAction(zip_extract_action)

        terminal_action = QAction("Open terminal here", self)
        terminal_action.triggered.connect(self._open_terminal)
        menu.addAction(terminal_action)

        menu.exec(self.view.viewport().mapToGlobal(pos))

    def _open_selected(self) -> None:
        for path in self.selected_paths():
            if path.is_dir():
                self.set_path(path)
                continue
            self._run_action(lambda p=path: file_ops.open_with_default(p))

    def _rename_selected(self) -> None:
        selected = self.selected_paths()
        if len(selected) != 1:
            return
        source = selected[0]
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=source.name)
        if not ok or not name.strip():
            return
        self._run_action(lambda: file_ops.rename_path(source, name.strip()))
        self.refresh()

    def _new_folder(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New folder", "Folder name:", text="New Folder"
        )
        if not ok or not name.strip():
            return
        self._run_action(
            lambda: file_ops.create_folder(self.current_path(), name.strip())
        )
        self.refresh()

    def _copy_selected(self) -> None:
        selected = self.selected_paths()
        if selected:
            file_ops.set_clipboard(selected, cut=False)

    def _cut_selected(self) -> None:
        selected = self.selected_paths()
        if selected:
            file_ops.set_clipboard(selected, cut=True)

    def _paste_into_current(self) -> None:
        self._run_action(lambda: file_ops.paste_items(self.current_path()))
        self.refresh()

    def _move_selected(self) -> None:
        selected = self.selected_paths()
        if not selected:
            return
        dest = QFileDialog.getExistingDirectory(
            self, "Move items", str(self.current_path())
        )
        if not dest:
            return
        self._run_action(lambda: file_ops.move_items(selected, Path(dest)))
        self.refresh()

    def _delete_selected(self) -> None:
        selected = self.selected_paths()
        if not selected:
            return
        names = "\n".join(path.name for path in selected[:10])
        confirm = QMessageBox.question(
            self,
            "Delete to Recycle Bin",
            f"Move selected items to Recycle Bin?\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._run_action(lambda: file_ops.delete_to_recycle_bin(selected))
        self.refresh()

    def _show_properties(self) -> None:
        selected = self.selected_paths()
        if len(selected) != 1:
            return
        dialog = PropertiesDialog(selected[0], self)
        dialog.exec()

    def _zip_create(self) -> None:
        selected = self.selected_paths()
        if not selected:
            return

        default_name = (
            f"{selected[0].name}.zip" if len(selected) == 1 else "archive.zip"
        )
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Create ZIP",
            str(self.current_path() / default_name),
            "ZIP Files (*.zip)",
        )
        if not target:
            return
        self._run_action(lambda: file_ops.zip_create(selected, Path(target)))

    def _zip_extract(self) -> None:
        selected = self.selected_paths()
        if len(selected) != 1:
            return
        archive = selected[0]
        if archive.suffix.lower() != ".zip":
            return

        target = QFileDialog.getExistingDirectory(
            self, "Extract ZIP", str(self.current_path())
        )
        if not target:
            return
        self._run_action(lambda: file_ops.zip_extract(archive, Path(target)))
        self.refresh()

    def _open_terminal(self) -> None:
        self._run_action(lambda: file_ops.open_terminal_here(self.current_path()))

    def _run_action(self, action: Callable[[], object]) -> None:
        try:
            action()
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self, "Operation failed", str(exc))

    def _apply_hidden_filter(self) -> None:
        filters = QDir.Filter.AllEntries | QDir.Filter.AllDirs | QDir.Filter.NoDot
        if not self._show_parent_entry:
            filters |= QDir.Filter.NoDotDot
        if self._show_hidden:
            filters |= QDir.Filter.Hidden | QDir.Filter.System
        self.model.setFilter(filters)
        if self._inline_filter_text:
            self.model.setNameFilterDisables(False)
            self.model.setNameFilters([f"*{self._inline_filter_text}*"])
        else:
            self.model.setNameFilters([])
            self.model.setNameFilterDisables(True)

    def _should_show_parent_entry(self, path: Path) -> bool:
        if path.parent == path:
            return False
        if path.drive:
            drive_root = Path(f"{path.drive}{os.sep}")
            if self._path_key(path) == self._path_key(drive_root):
                return False
        return True

    def _emit_history_state(self) -> None:
        self.history_changed.emit(self.can_go_back(), self.can_go_forward())

    def _on_column_resized(
        self, _logical_index: int, _old_size: int, _new_size: int
    ) -> None:
        if self._syncing_column_widths:
            return
        self.column_widths_changed.emit(self.column_widths())

    def _on_directory_loaded(self, _path: str) -> None:
        if self._pending_column_widths:
            self._apply_column_widths_once(self._pending_column_widths)

    def _path_key(self, path: Path) -> str:
        return os.path.normcase(os.path.normpath(str(path)))

    def _selected_or_current_path(self) -> Path | None:
        selection_model = self.view.selectionModel()

        selected_rows = selection_model.selectedRows()
        index = selected_rows[0] if selected_rows else self.view.currentIndex()
        if not index.isValid():
            return None
        if self.model.is_parent_index(index):
            return None
        return Path(self.model.filePath(index))

    def _remember_selection_for_path(self, path: Path) -> None:
        selected = self._selected_or_current_path()
        if selected is None:
            return
        if selected.parent != path:
            return
        self._selection_memory[self._path_key(path)] = selected

    def _restore_selection_for_path(
        self, path: Path, preferred: Path | None = None
    ) -> None:
        candidate = preferred or self._selection_memory.get(self._path_key(path))
        if candidate is None:
            return
        if candidate.parent != path:
            return

        self._selection_restore_token += 1
        token = self._selection_restore_token
        self._try_restore_selection(candidate, token, attempts_remaining=40)

    def _try_restore_selection(
        self,
        candidate: Path,
        token: int,
        *,
        attempts_remaining: int,
    ) -> None:
        if token != self._selection_restore_token:
            return
        if not isValid(self) or not isValid(self.model) or not isValid(self.view):
            return

        index = self.model.index_for_path(candidate)
        if index.isValid():
            selection_model = self.view.selectionModel()
            flags = (
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows
            )
            selection_model.setCurrentIndex(index, flags)
            self.view.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
            return

        if attempts_remaining <= 0:
            return
        QTimer.singleShot(
            25,
            lambda: self._try_restore_selection(
                candidate,
                token,
                attempts_remaining=attempts_remaining - 1,
            ),
        )
