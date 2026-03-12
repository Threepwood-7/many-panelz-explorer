from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QTreeView

from .fast_dir_model import FastDirModel


class ExplorerTabColumns(QObject):
    changed = Signal(object)

    def __init__(
        self,
        *,
        model: FastDirModel,
        view: QTreeView,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._view = view
        self._syncing = False
        self._pending_widths: list[int] = []
        self._view.header().sectionResized.connect(self._on_column_resized)
        self._model.directoryLoaded.connect(self._on_directory_loaded)

    @property
    def widths(self) -> tuple[int, ...]:
        header = self._view.header()
        return tuple(
            header.sectionSize(column) for column in range(self._model.columnCount())
        )

    def set_widths(self, widths: Sequence[object]) -> None:
        normalized = self._coerce_widths(widths)
        if not normalized:
            return
        self._pending_widths = list(normalized)
        self._apply_widths_once(normalized)

    def preserve_for_reload(self) -> None:
        normalized = self._coerce_widths(self.widths)
        if normalized:
            self._pending_widths = list(normalized)

    def _apply_widths_once(self, widths: Sequence[int]) -> None:
        self._syncing = True
        try:
            for column, width in enumerate(widths[: self._model.columnCount()]):
                value = int(width)
                if value > 0:
                    self._view.setColumnWidth(column, value)
        finally:
            self._syncing = False

    def _on_column_resized(
        self, _logical_index: int, _old_size: int, _new_size: int
    ) -> None:
        if self._syncing:
            return
        normalized = self._coerce_widths(self.widths)
        if normalized:
            self._pending_widths = list(normalized)
            self.changed.emit(tuple(normalized))

    def _on_directory_loaded(self, _path: str) -> None:
        if self._pending_widths:
            self._apply_widths_once(self._pending_widths)

    def _coerce_widths(self, widths: Sequence[object]) -> list[int]:
        normalized: list[int] = []
        for width in widths:
            if isinstance(width, bool):
                value = int(width)
            elif isinstance(width, int):
                value = width
            elif isinstance(width, float):
                value = int(width)
            elif isinstance(width, str):
                try:
                    value = int(width)
                except ValueError:
                    continue
            else:
                continue
            if value > 0:
                normalized.append(value)
        return normalized
