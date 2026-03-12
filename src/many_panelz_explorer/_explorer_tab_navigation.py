from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QDir, QItemSelectionModel, QObject, QTimer, Signal
from PySide6.QtWidgets import QAbstractItemView, QTreeView, QWidget
from shiboken6 import isValid
from threep_commons.fs_paths import coerce_path, is_drive_root, path_key

if TYPE_CHECKING:
    from ._explorer_tab_columns import ExplorerTabColumns
    from .fast_dir_model import FastDirModel


class ExplorerTabNavigation(QObject):
    changed = Signal()

    _SELECTION_RESTORE_INTERVAL_MS = 25
    _SELECTION_RESTORE_ATTEMPTS = 40

    def __init__(
        self,
        *,
        owner: QWidget,
        model: FastDirModel,
        view: QTreeView,
        columns: ExplorerTabColumns,
        show_hidden: bool,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._owner = owner
        self._model = model
        self._view = view
        self._columns = columns
        self._history: list[Path] = []
        self._history_index = -1
        self._show_hidden = bool(show_hidden)
        self._selection_memory: dict[str, Path] = {}
        self._selection_restore_token = 0
        self._show_parent_entry = True
        self._inline_filter_text = ""
        self._apply_model_filters()

    @property
    def path(self) -> Path:
        if not self._history:
            return Path.home()
        return self._history[self._history_index]

    @property
    def can_go_back(self) -> bool:
        return self._history_index > 0

    @property
    def can_go_forward(self) -> bool:
        return self._history_index >= 0 and self._history_index < len(self._history) - 1

    @property
    def history(self) -> tuple[Path, ...]:
        return tuple(self._history)

    @property
    def history_index(self) -> int:
        return self._history_index

    @property
    def inline_filter_text(self) -> str:
        return self._inline_filter_text

    def set_show_hidden(self, enabled: bool) -> None:
        self._show_hidden = bool(enabled)
        self._apply_model_filters()
        self.refresh()

    def set_inline_filter(self, text: str) -> None:
        normalized = str(text or "").strip()
        if normalized == self._inline_filter_text:
            return
        self._inline_filter_text = normalized
        self._apply_model_filters()
        self.changed.emit()

    def clear_inline_filter(self) -> None:
        self.set_inline_filter("")

    def set_path(
        self,
        path: Path | str,
        *,
        push_history: bool = True,
        selection_hint: Path | None = None,
    ) -> None:
        previous_path = self.path if self._history else None
        if previous_path is not None:
            self._remember_selection_for_path(previous_path)

        target = coerce_path(path)
        if not target.exists() or not target.is_dir():
            target = Path.home()

        self._show_parent_entry = self._should_show_parent_entry(target)
        self._apply_model_filters()

        if push_history:
            if not self._history or self._history[self._history_index] != target:
                self._history = self._history[: self._history_index + 1]
                self._history.append(target)
                self._history_index = len(self._history) - 1
        elif not self._history:
            self._history = [target]
            self._history_index = 0

        self._columns.preserve_for_reload()
        index = self._model.setRootPath(str(target))
        self._view.setRootIndex(index)
        self._restore_selection_for_path(target, preferred=selection_hint)
        self.changed.emit()

    def refresh(self) -> None:
        self.set_path(self.path, push_history=False)

    def go_back(self) -> None:
        if not self.can_go_back:
            return
        self._history_index -= 1
        self.set_path(self._history[self._history_index], push_history=False)

    def go_forward(self) -> None:
        if not self.can_go_forward:
            return
        self._history_index += 1
        self.set_path(self._history[self._history_index], push_history=False)

    def go_up(self) -> None:
        current = self.path
        parent = current.parent
        if parent != current:
            self.set_path(parent, selection_hint=current)

    def go_to_history_index(self, index: int) -> None:
        if index < 0 or index >= len(self._history):
            return
        self._history_index = index
        self.set_path(self._history[self._history_index], push_history=False)

    def _apply_model_filters(self) -> None:
        filters: Any = QDir.Filter.AllEntries | QDir.Filter.AllDirs | QDir.Filter.NoDot
        if not self._show_parent_entry:
            filters |= QDir.Filter.NoDotDot
        if self._show_hidden:
            filters |= QDir.Filter.Hidden | QDir.Filter.System
        model_any: Any = self._model
        model_any.setFilter(filters)
        if self._inline_filter_text:
            self._model.setNameFilterDisables(False)
            self._model.setNameFilters([f"*{self._inline_filter_text}*"])
            return
        self._model.setNameFilters([])
        self._model.setNameFilterDisables(True)

    def _should_show_parent_entry(self, path: Path) -> bool:
        if path.parent == path:
            return False
        return not is_drive_root(path)

    def _selected_or_current_path(self) -> Path | None:
        selection_model = self._view.selectionModel()
        selected_rows = selection_model.selectedRows()
        index = selected_rows[0] if selected_rows else self._view.currentIndex()
        if not index.isValid() or self._model.is_parent_index(index):
            return None
        return Path(self._model.filePath(index))

    def _remember_selection_for_path(self, path: Path) -> None:
        selected = self._selected_or_current_path()
        if selected is None or selected.parent != path:
            return
        self._selection_memory[self._path_key(path)] = selected

    def _restore_selection_for_path(
        self, path: Path, preferred: Path | None = None
    ) -> None:
        candidate = preferred or self._selection_memory.get(self._path_key(path))
        if candidate is None or candidate.parent != path:
            return
        self._selection_restore_token += 1
        token = self._selection_restore_token
        self._try_restore_selection(
            candidate,
            token,
            attempts_remaining=self._SELECTION_RESTORE_ATTEMPTS,
        )

    def _try_restore_selection(
        self,
        candidate: Path,
        token: int,
        *,
        attempts_remaining: int,
    ) -> None:
        if token != self._selection_restore_token:
            return
        if (
            not isValid(self._owner)
            or not isValid(self._model)
            or not isValid(self._view)
        ):
            return

        index = self._model.index_for_path(candidate)
        if index.isValid():
            selection_model = self._view.selectionModel()
            flags = (
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows
            )
            selection_model.setCurrentIndex(index, flags)
            self._view.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
            return

        if attempts_remaining <= 0:
            return
        QTimer.singleShot(
            self._SELECTION_RESTORE_INTERVAL_MS,
            lambda: self._try_restore_selection(
                candidate,
                token,
                attempts_remaining=attempts_remaining - 1,
            ),
        )

    def _path_key(self, path: Path) -> str:
        return path_key(path)
