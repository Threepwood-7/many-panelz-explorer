"""Explorer tab widget hosting the file tree and tab navigation state."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QEvent, QModelIndex, QObject, Qt
from PySide6.QtGui import QKeyEvent, QShortcut
from PySide6.QtWidgets import QAbstractItemView, QTreeView, QVBoxLayout, QWidget

from ._explorer_tab_actions import ExplorerTabActions
from ._explorer_tab_columns import ExplorerTabColumns
from ._explorer_tab_navigation import ExplorerTabNavigation
from .fast_dir_model import FastDirModel

if TYPE_CHECKING:
    from collections.abc import Callable


class ExplorerTab(QWidget):
    """Combine directory model, view, actions, and navigation for one tab."""

    def __init__(
        self,
        initial_path: Path,
        show_hidden: bool = True,
        file_list_size_formatter: Callable[[int], str] | None = None,
        properties_size_formatter: Callable[[int], str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tab_uuid = uuid.uuid4().hex
        self._file_list_size_formatter = (
            file_list_size_formatter or self._default_file_list_size_formatter
        )
        self._properties_size_formatter = (
            properties_size_formatter or self._default_properties_size_formatter
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.model = FastDirModel(self)
        self.model.set_size_formatter(self._file_list_size_formatter)
        self.model.setReadOnly(False)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setRootIsDecorated(False)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(False)
        self.view.setDropIndicatorShown(False)
        self.view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.view.setSortingEnabled(True)
        self.view.installEventFilter(self)
        root.addWidget(self.view)

        self.columns = ExplorerTabColumns(
            model=self.model,
            view=self.view,
            parent=self,
        )
        self.navigation = ExplorerTabNavigation(
            owner=self,
            model=self.model,
            view=self.view,
            columns=self.columns,
            show_hidden=show_hidden,
            parent=self,
        )
        self._actions = ExplorerTabActions(self, parent=self)

        self.view.customContextMenuRequested.connect(self._actions.open_context_menu)
        self.view.doubleClicked.connect(self._on_item_activated)
        self.view.activated.connect(self._on_item_activated)

        self._alt_left_shortcut = QShortcut("Alt+Left", self)
        self._alt_left_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._alt_left_shortcut.activated.connect(self.navigation.go_back)

        self._alt_right_shortcut = QShortcut("Alt+Right", self)
        self._alt_right_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._alt_right_shortcut.activated.connect(self.navigation.go_forward)

        self._alt_up_shortcut = QShortcut("Alt+Up", self)
        self._alt_up_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._alt_up_shortcut.activated.connect(self.navigation.go_up)

        self.navigation.set_path(initial_path)
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    @property
    def tab_uuid(self) -> str:
        return self._tab_uuid

    @property
    def properties_size_formatter(self) -> Callable[[int], str]:
        return self._properties_size_formatter

    def serialize_state(self) -> dict[str, str]:
        return {"path": str(self.navigation.path)}

    def set_file_size_formatter(self, formatter: Callable[[int], str] | None) -> None:
        self._file_list_size_formatter = (
            formatter or self._default_file_list_size_formatter
        )
        self.model.set_size_formatter(self._file_list_size_formatter)

    def set_properties_size_formatter(
        self,
        formatter: Callable[[int], str] | None,
    ) -> None:
        self._properties_size_formatter = (
            formatter or self._default_properties_size_formatter
        )

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

    def _on_item_activated(self, index: QModelIndex) -> None:
        file_path = self.model.filePath(index)
        if not file_path:
            return
        self._actions.open_path(Path(file_path))

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.view and event.type() == QEvent.Type.KeyPress:
            key_event = cast("QKeyEvent", event)
            if self._handle_navigation_key(key_event):
                index = self.view.currentIndex()
                if index.isValid() and key_event.key() == int(Qt.Key.Key_Right):
                    self._on_item_activated(index)
                return True
        return super().eventFilter(obj, event)

    def _handle_navigation_key(self, key_event: QKeyEvent) -> bool:
        modifiers = key_event.modifiers()
        key = key_event.key()
        dispatch: dict[tuple[Qt.KeyboardModifier, int], Callable[[], None]] = {
            (
                Qt.KeyboardModifier.AltModifier,
                int(Qt.Key.Key_Left),
            ): self.navigation.go_back,
            (
                Qt.KeyboardModifier.AltModifier,
                int(Qt.Key.Key_Right),
            ): self.navigation.go_forward,
            (
                Qt.KeyboardModifier.AltModifier,
                int(Qt.Key.Key_Up),
            ): self.navigation.go_up,
            (
                Qt.KeyboardModifier.NoModifier,
                int(Qt.Key.Key_Left),
            ): self.navigation.go_up,
            (
                Qt.KeyboardModifier.NoModifier,
                int(Qt.Key.Key_Backspace),
            ): self.navigation.go_up,
        }
        handler = dispatch.get((modifiers, key))
        if handler is not None:
            handler()
            return True
        return modifiers == Qt.KeyboardModifier.NoModifier and key == int(
            Qt.Key.Key_Right
        )

    def _default_file_list_size_formatter(self, value: int) -> str:
        return f"{int(value):,}"

    def _default_properties_size_formatter(self, value: int) -> str:
        return f"{int(value):,}"
