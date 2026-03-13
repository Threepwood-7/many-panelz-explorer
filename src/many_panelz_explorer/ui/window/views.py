"""Saved-view coordination for explorer windows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...window import ExplorerWindow


type SavedViewState = dict[str, Any]


class WindowViewsCoordinator:
    """Manage saved view creation, replacement, and restoration."""

    def __init__(self, window: ExplorerWindow) -> None:
        """Store the owning window reference."""
        self.window = window

    def save_view(self) -> None:
        """Persist the current window state as a named saved view."""
        name, ok = QInputDialog.getText(self.window, "Save View", "View name:")
        if not ok:
            return
        view_name = name.strip()
        if not view_name:
            return

        if self.window.settings.get_saved_view(view_name) is not None:
            overwrite = QMessageBox.question(
                self.window,
                "Save View",
                f'View "{view_name}" already exists. Overwrite?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if overwrite != QMessageBox.StandardButton.Yes:
                return

        self.window.settings.set_saved_view(
            view_name,
            self.window.persistence_coordinator.serialize_state(include_geometry=True),
        )
        self.window.settings.sync()

    def restore_view(self) -> None:
        """Open a saved view in a newly created window."""
        view_state = self._prompt_saved_view("Restore View")
        if view_state is None:
            return
        self._restore_view_state(view_state)

    def restore_view_named(self, view_name: str) -> None:
        """Open the given saved view name in a newly created window."""
        payload = self.window.settings.get_saved_view(view_name)
        if payload is None:
            QMessageBox.warning(
                self.window,
                "Restore View",
                f'View "{view_name}" was not found.',
            )
            return
        self._restore_view_state(payload)

    def replace_view(self) -> None:
        """Replace the current window state with a saved view."""
        view_state = self._prompt_saved_view("Replace View")
        if view_state is None:
            return
        self.window.persistence_coordinator.apply_cloned_state(
            view_state,
            restore_geometry=True,
        )

    def populate_restore_view_menu(self, menu: QMenu) -> None:
        """Populate the restore-view submenu with saved views."""
        menu.clear()
        names = self.window.settings.list_saved_views()
        if not names:
            empty_action = menu.addAction("(N&o saved views)")
            empty_action.setEnabled(False)
            return

        for view_name in names:
            action = menu.addAction(view_name.replace("&", "&&"))
            action.triggered.connect(self._restore_view_named_callback(view_name))

    def _restore_view_state(self, view_state: SavedViewState) -> None:
        """Create a clone window and hydrate it from saved state."""
        new_window = self.window.controller.new_window(
            from_window=self.window,
            show=False,
        )
        new_window.persistence_coordinator.apply_cloned_state(
            view_state,
            restore_geometry=True,
        )
        new_window.show()

    def _prompt_saved_view(self, title: str) -> SavedViewState | None:
        """Prompt the user to choose a saved view payload."""
        names = self.window.settings.list_saved_views()
        if not names:
            QMessageBox.information(self.window, title, "No saved views.")
            return None

        selected_raw, ok = QInputDialog.getItem(
            self.window,
            title,
            "Select a saved view:",
            names,
            0,
            False,
        )
        selected = str(selected_raw).strip()
        if not ok or not selected:
            return None

        payload = self.window.settings.get_saved_view(selected)
        if payload is None:
            QMessageBox.warning(
                self.window,
                title,
                f'View "{selected}" was not found.',
            )
            return None
        return payload

    def _restore_view_named_callback(self, view_name: str) -> Callable[[bool], None]:
        """Build a callback that restores a fixed saved view name."""

        def _handle_triggered(_checked: bool = False) -> None:
            self.restore_view_named(view_name)

        return _handle_triggered
