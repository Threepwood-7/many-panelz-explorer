"""Persistence helpers for saving and restoring window state."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QMessageBox

from ...panel_tree import PanelTreeModel
from ...window_state_payloads import (
    coerce_bool as _coerce_bool,
)
from ...window_state_payloads import (
    panel_tree_payload as _panel_tree_payload,
)
from ...window_state_payloads import (
    saved_view_state as _saved_view_state,
)
from ...window_state_payloads import (
    tabs_state_from_panels_payload as _tabs_state_from_panels_payload,
)
from ...window_state_payloads import (
    window_tabs_payload as _window_tabs_payload,
)
from .panels import serialize_window_tabs_state

if TYPE_CHECKING:
    from ...window import ExplorerWindow
    from .state_types import SavedViewState, WindowStatePayload, WindowTabsPayload


class WindowPersistenceCoordinator:
    """Serialize and restore panel, tab, and geometry state for a window."""

    def __init__(self, window: ExplorerWindow) -> None:
        self.window = window

    def encode_geometry(self) -> str:
        geometry = self.window.saveGeometry()
        encoded = geometry.toBase64().data()
        return bytes(encoded).decode("ascii")

    def restore_geometry_from_b64(self, encoded: str) -> None:
        raw = QByteArray.fromBase64(encoded.encode("ascii"))
        if not raw.isEmpty():
            self.window.default_maximize_on_first_show = False
            self.window.restoreGeometry(raw)

    def serialize_state(
        self,
        *,
        include_geometry: bool = False,
    ) -> WindowStatePayload:
        """Serialize the current window state for cloning or saved views."""

        self.window.layout_coordinator.sync_panel_tree_from_rows()
        payload: WindowStatePayload = {
            "window_id": self.window.window_id,
            "panel_tree": self.window.panel_tree.to_dict(),
            "tabs": serialize_window_tabs_state(self.window),
            "active_panel_id": self.window.active_panel_id,
            "on_top": self.window.on_top_action.isChecked(),
            "maximized": self._is_window_maximized(),
        }
        if include_geometry:
            payload["geometry_b64"] = self.encode_geometry()
        return payload

    def save_to_settings(self) -> None:
        """Persist the current session-backed window state into settings."""

        payload = self.serialize_state()
        self.window.settings.set_json(
            self.window.settings.window_key(self.window.window_id, "panel_tree"),
            payload["panel_tree"],
        )

        tabs_payload: WindowTabsPayload = {
            "active_panel_id": payload["active_panel_id"],
            "panels": {str(pid): state for pid, state in payload["tabs"].items()},
        }
        self.window.settings.set_json(
            self.window.settings.window_key(self.window.window_id, "tabs"), tabs_payload
        )
        self.window.settings.set_value(
            self.window.settings.window_key(self.window.window_id, "on_top"),
            payload["on_top"],
        )
        self.window.settings.set_value(
            self.window.settings.window_key(self.window.window_id, "geometry"),
            self.window.saveGeometry(),
        )
        self.window.settings.set_value(
            self.window.settings.window_key(self.window.window_id, "maximized"),
            self._is_window_maximized(),
        )

    def restore_from_settings(self) -> None:
        """Restore panel layout, tabs, and geometry state from settings."""

        panel_tree_data = self.window.settings.get_json(
            self.window.settings.window_key(self.window.window_id, "panel_tree"), None
        )
        panel_tree_payload = _panel_tree_payload(panel_tree_data)
        if panel_tree_payload is not None:
            try:
                self.window.panel_tree = PanelTreeModel.from_dict(panel_tree_payload)
            except Exception as exc:  # pragma: no cover - defensive path
                QMessageBox.warning(
                    self.window, "Restore", f"Could not restore panel tree: {exc}"
                )
                self.window.panel_tree = (
                    self.window.layout_coordinator.default_startup_tree()
                )
        self.window.layout_rows = self.window.layout_coordinator.rows_from_tree(
            self.window.panel_tree.root
        )

        tabs_payload_raw = self.window.settings.get_json(
            self.window.settings.window_key(self.window.window_id, "tabs"), {}
        )
        tabs_payload = _window_tabs_payload(tabs_payload_raw)
        tabs_state = _tabs_state_from_panels_payload(tabs_payload["panels"])
        self.window.layout_rows = (
            self.window.layout_coordinator.append_missing_panel_ids(
                self.window.layout_rows,
                list(tabs_state.keys()),
            )
        )
        self.window.layout_coordinator.sync_panel_tree_from_rows()

        self.window.panels_coordinator.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=tabs_payload["active_panel_id"],
        )

        on_top_value = self.window.settings.value(
            self.window.settings.window_key(self.window.window_id, "on_top"), False
        )
        self.window.set_on_top(_coerce_bool(on_top_value))

        geometry = self.window.settings.value(
            self.window.settings.window_key(self.window.window_id, "geometry")
        )
        if isinstance(geometry, QByteArray):
            self.window.default_maximize_on_first_show = False
            self.window.restoreGeometry(geometry)
        maximized_value = self.window.settings.value(
            self.window.settings.window_key(self.window.window_id, "maximized"),
            False,
        )
        maximized = _coerce_bool(maximized_value)
        if geometry is not None or maximized:
            self.window.default_maximize_on_first_show = False
            self._apply_maximized_state(maximized)

    def apply_cloned_state(
        self,
        state: SavedViewState,
        *,
        restore_geometry: bool = False,
    ) -> None:
        """Apply a serialized window state to the current live window."""

        self.window.default_maximize_on_first_show = False
        payload = _saved_view_state(state)
        panel_tree_payload = _panel_tree_payload(payload.get("panel_tree"))
        if panel_tree_payload is not None:
            self.window.panel_tree = PanelTreeModel.from_dict(panel_tree_payload)
        self.window.layout_rows = self.window.layout_coordinator.rows_from_tree(
            self.window.panel_tree.root
        )

        tabs_state = _tabs_state_from_panels_payload(deepcopy(payload.get("tabs", {})))
        self.window.layout_rows = (
            self.window.layout_coordinator.append_missing_panel_ids(
                self.window.layout_rows,
                list(tabs_state.keys()),
            )
        )
        self.window.layout_coordinator.sync_panel_tree_from_rows()

        self.window.panels_coordinator.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=payload["active_panel_id"],
        )
        self.window.set_on_top(payload["on_top"])
        if restore_geometry:
            geometry_b64 = payload.get("geometry_b64")
            if isinstance(geometry_b64, str) and geometry_b64:
                self.restore_geometry_from_b64(geometry_b64)
            self._apply_maximized_state(payload["maximized"])

    def _apply_maximized_state(self, maximized: bool) -> None:
        """Apply the persisted maximized state to the window."""
        if maximized:
            self.window.setWindowState(
                self.window.windowState() | Qt.WindowState.WindowMaximized
            )
            return
        self.window.setWindowState(
            self.window.windowState() & ~Qt.WindowState.WindowMaximized
        )

    def _is_window_maximized(self) -> bool:
        """Return whether the window state currently includes maximize."""

        return bool(self.window.windowState() & Qt.WindowState.WindowMaximized)
