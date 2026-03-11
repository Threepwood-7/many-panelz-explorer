from __future__ import annotations

import fnmatch
import os
import weakref
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from PySide6.QtCore import QAbstractTableModel, QDir, QModelIndex, QObject, Qt, Signal

_HIDDEN_ATTRIBUTE_MASK = 0x2
_SYSTEM_ATTRIBUTE_MASK = 0x4


@dataclass(slots=True)
class _DirEntry:
    path: Path
    name: str
    extension: str
    is_dir: bool
    size: int
    modified_ts: float
    is_hidden: bool
    is_system: bool


def _scan_directory(path: Path) -> list[_DirEntry]:
    entries: list[_DirEntry] = []
    with os.scandir(path) as iterator:
        for item in iterator:
            item_path = Path(item.path)
            try:
                item_stat = item.stat(follow_symlinks=False)
            except OSError:
                continue

            try:
                is_dir = item.is_dir(follow_symlinks=False)
            except OSError:
                is_dir = False

            name = item.name
            extension = "" if is_dir else item_path.suffix.lstrip(".")
            size = 0 if is_dir else int(item_stat.st_size)
            hidden = name.startswith(".")
            system = False

            if os.name == "nt":
                attributes = int(getattr(item_stat, "st_file_attributes", 0))
                hidden = hidden or bool(attributes & _HIDDEN_ATTRIBUTE_MASK)
                system = bool(attributes & _SYSTEM_ATTRIBUTE_MASK)

            entries.append(
                _DirEntry(
                    path=item_path,
                    name=name,
                    extension=extension,
                    is_dir=is_dir,
                    size=size,
                    modified_ts=float(item_stat.st_mtime),
                    is_hidden=hidden,
                    is_system=system,
                )
            )
    return entries


class _ModelSignals(QObject):
    listing_ready = Signal(int, str, object, object)


class FastDirModel(QAbstractTableModel):
    directoryLoaded = Signal(str)  # noqa: N815

    _HEADERS = ("Name", "Ext", "Size", "Date")
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mpe-dir-scan")

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        size_formatter: Callable[[int], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_path = Path.home()
        self._filter_flags = (
            QDir.Filter.AllEntries | QDir.Filter.AllDirs | QDir.Filter.NoDot
        )
        self._name_filters: list[str] = []
        self._name_filter_disables = True
        self._all_entries: list[_DirEntry] = []
        self._visible_entries: list[_DirEntry] = []
        self._show_parent_entry = True
        self._show_hidden = False
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._request_id = 0
        self._size_formatter = size_formatter or self._default_size_formatter
        self._signals = _ModelSignals(self)
        self._signals.listing_ready.connect(self._on_listing_ready)
        self._refresh_filter_flags()

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._visible_entries) + (1 if self._show_parent_entry else 0)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._HEADERS)

    def index(
        self,
        row: int | str,
        column: int = 0,
        parent: QModelIndex | None = None,
    ) -> QModelIndex:
        if parent is None:
            parent = QModelIndex()
        if isinstance(row, str):
            return self.index_for_path(Path(row))
        if parent.isValid() or row < 0 or column < 0:
            return QModelIndex()
        if row >= self.rowCount() or column >= self.columnCount():
            return QModelIndex()
        return self.createIndex(int(row), int(column), None)

    def parent(self, _index: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> object:
        if not index.isValid():
            return None

        if role == int(Qt.ItemDataRole.TextAlignmentRole) and index.column() == 2:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if role == int(Qt.ItemDataRole.UserRole):
            return self.filePath(index)

        if role != int(Qt.ItemDataRole.DisplayRole):
            return None

        row = index.row()
        col = index.column()

        if self._is_parent_row(row):
            return ".." if col == 0 else ""

        entry = self._entry_for_row(row)
        if entry is None:
            return ""

        if col == 0:
            return f"[{entry.name}]" if entry.is_dir else entry.name
        if col == 1:
            return "" if entry.is_dir else entry.extension
        if col == 2:
            return "" if entry.is_dir else self._format_size(entry.size)
        if col == 3:
            return datetime.fromtimestamp(entry.modified_ts).strftime("%Y-%m-%d %H:%M")
        return ""

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> object:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == int(Qt.ItemDataRole.DisplayRole)
            and 0 <= section < len(self._HEADERS)
        ):
            return self._HEADERS[section]
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setReadOnly(self, _read_only: bool) -> None:  # noqa: N802
        # Compatibility no-op: ExplorerTab expects QFileSystemModel-style API.
        return

    def setRootPath(self, path: str) -> QModelIndex:  # noqa: N802
        target = Path(path).expanduser()
        if not target.exists() or not target.is_dir():
            target = Path.home()
        self._current_path = target

        self._request_id += 1
        request_id = self._request_id

        self.beginResetModel()
        self._all_entries = []
        self._visible_entries = []
        self.endResetModel()

        model_ref = weakref.ref(self)

        def _done_callback(future: Future[list[_DirEntry]]) -> None:
            model = model_ref()
            if model is None:
                return
            try:
                listing = future.result()
                error: str | None = None
            except Exception as exc:  # pragma: no cover - defensive
                listing = []
                error = str(exc)
            model._signals.listing_ready.emit(
                request_id, str(target), list(listing), error
            )

        future = self._executor.submit(_scan_directory, target)
        future.add_done_callback(_done_callback)
        return QModelIndex()

    def filePath(self, index: QModelIndex) -> str:  # noqa: N802
        if not index.isValid():
            return ""
        row = index.row()
        if self._is_parent_row(row):
            return str(self._current_path.parent)
        entry = self._entry_for_row(row)
        return str(entry.path) if entry is not None else ""

    def index_for_path(self, path: Path) -> QModelIndex:
        target = self._path_key(path)
        if self._show_parent_entry and self._path_key(self._current_path.parent) == target:
            return self.index(0, 0)
        offset = 1 if self._show_parent_entry else 0
        for idx, entry in enumerate(self._visible_entries):
            if self._path_key(entry.path) == target:
                return self.index(idx + offset, 0)
        return QModelIndex()

    def is_parent_index(self, index: QModelIndex) -> bool:
        return index.isValid() and self._is_parent_row(index.row())

    def setFilter(self, flags: QDir.Filters | QDir.Filter) -> None:  # noqa: N802
        self._filter_flags = cast("QDir.Filter", flags)
        self._refresh_filter_flags()
        self._rebuild_visible(reset=True)

    def filter(self) -> QDir.Filter:
        return self._filter_flags

    def setNameFilters(self, filters: list[str]) -> None:  # noqa: N802
        self._name_filters = [str(pattern) for pattern in filters]
        self._rebuild_visible(reset=True)

    def nameFilters(self) -> list[str]:  # noqa: N802
        return list(self._name_filters)

    def setNameFilterDisables(self, disables: bool) -> None:  # noqa: N802
        self._name_filter_disables = bool(disables)
        self._rebuild_visible(reset=True)

    def nameFilterDisables(self) -> bool:  # noqa: N802
        return self._name_filter_disables

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:
        self._sort_column = max(0, min(int(column), len(self._HEADERS) - 1))
        self._sort_order = order
        self._rebuild_visible(reset=True)

    def set_size_formatter(self, formatter: Callable[[int], str] | None) -> None:
        self._size_formatter = formatter or self._default_size_formatter
        row_count = self.rowCount()
        if row_count <= 0:
            return
        top = self.index(0, 2)
        bottom = self.index(row_count - 1, 2)
        if top.isValid() and bottom.isValid():
            self.dataChanged.emit(
                top,
                bottom,
                [int(Qt.ItemDataRole.DisplayRole)],
            )

    def _on_listing_ready(
        self,
        request_id: int,
        path: str,
        entries: object,
        error: object,
    ) -> None:
        if request_id != self._request_id:
            return
        if self._path_key(Path(path)) != self._path_key(self._current_path):
            return
        if error is not None:
            parsed_entries: list[_DirEntry] = []
        else:
            parsed_entries = cast("list[_DirEntry]", entries)

        self.beginResetModel()
        self._all_entries = parsed_entries
        self._visible_entries = self._sort_entries(self._apply_entry_filters(parsed_entries))
        self.endResetModel()
        self.directoryLoaded.emit(str(self._current_path))

    def _refresh_filter_flags(self) -> None:
        self._show_hidden = bool(
            self._filter_flags & (QDir.Filter.Hidden | QDir.Filter.System)
        )
        self._show_parent_entry = not bool(self._filter_flags & QDir.Filter.NoDotDot)

    def _apply_entry_filters(self, entries: list[_DirEntry]) -> list[_DirEntry]:
        filtered: list[_DirEntry] = []
        for entry in entries:
            if not self._show_hidden and (entry.is_hidden or entry.is_system):
                continue
            if not self._matches_name_filters(entry):
                continue
            filtered.append(entry)
        return filtered

    def _matches_name_filters(self, entry: _DirEntry) -> bool:
        if self._name_filter_disables or not self._name_filters:
            return True
        candidate = entry.name.casefold()
        for pattern in self._name_filters:
            if fnmatch.fnmatch(candidate, str(pattern).casefold()):
                return True
        return False

    def _sort_entries(self, entries: list[_DirEntry]) -> list[_DirEntry]:
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder
        sorted_entries = list(entries)

        if self._sort_column == 0:
            sorted_entries.sort(
                key=lambda item: (0 if item.is_dir else 1, item.name.casefold()),
                reverse=reverse,
            )
            return sorted_entries

        # Compatibility fallback for non-name sort columns.
        if self._sort_column == 1:
            def key_fn(item: _DirEntry) -> tuple[int, str, str]:
                return (
                    0 if item.is_dir else 1,
                    item.extension.casefold(),
                    item.name.casefold(),
                )
        elif self._sort_column == 2:
            def key_fn(item: _DirEntry) -> tuple[int, int, str]:
                return (
                    0 if item.is_dir else 1,
                    item.size,
                    item.name.casefold(),
                )
        else:
            def key_fn(item: _DirEntry) -> tuple[int, float, str]:
                return (
                    0 if item.is_dir else 1,
                    item.modified_ts,
                    item.name.casefold(),
                )

        sorted_entries = sorted(sorted_entries, key=key_fn, reverse=reverse)
        return sorted_entries

    def _rebuild_visible(self, *, reset: bool) -> None:
        if reset:
            self.beginResetModel()
        self._visible_entries = self._sort_entries(
            self._apply_entry_filters(self._all_entries)
        )
        if reset:
            self.endResetModel()

    def _is_parent_row(self, row: int) -> bool:
        return self._show_parent_entry and row == 0

    def _entry_for_row(self, row: int) -> _DirEntry | None:
        offset = 1 if self._show_parent_entry else 0
        idx = row - offset
        if idx < 0 or idx >= len(self._visible_entries):
            return None
        return self._visible_entries[idx]

    def _format_size(self, value: int) -> str:
        try:
            return str(self._size_formatter(int(value)))
        except Exception:  # pragma: no cover - defensive
            return self._default_size_formatter(int(value))

    def _default_size_formatter(self, value: int) -> str:
        return f"{int(value):,}"

    def _path_key(self, path: Path) -> str:
        return os.path.normcase(os.path.normpath(str(path)))
