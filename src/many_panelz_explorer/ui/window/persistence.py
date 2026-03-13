"""Persistence helpers for saving and restoring window state."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QMessageBox

from ...panel_tree import PanelTreeModel
from .panels import serialize_window_tabs_state

if TYPE_CHECKING:
    from ...window import ExplorerWindow


type PanelState = dict[str, Any]
type TabsState = dict[int, PanelState]


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
            self.window.restoreGeometry(raw)

    def serialize_state(self, *, include_geometry: bool = False) -> dict[str, Any]:
        self.window.layout_coordinator.sync_panel_tree_from_rows()
        payload: dict[str, Any] = {
            "window_id": self.window.window_id,
            "panel_tree": self.window.panel_tree.to_dict(),
            "tabs": serialize_window_tabs_state(self.window),
            "active_panel_id": self.window.active_panel_id,
            "on_top": self.window.on_top_action.isChecked(),
        }
        if include_geometry:
            payload["geometry_b64"] = self.encode_geometry()
        return payload

    def save_to_settings(self) -> None:
        payload = self.serialize_state()
        self.window.settings.set_json(
            self.window.settings.window_key(self.window.window_id, "panel_tree"),
            payload["panel_tree"],
        )

        tabs_payload = {
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

    def restore_from_settings(self) -> None:
        panel_tree_data = self.window.settings.get_json(
            self.window.settings.window_key(self.window.window_id, "panel_tree"), None
        )
        if isinstance(panel_tree_data, dict):
            try:
                self.window.panel_tree = PanelTreeModel.from_dict(
                    cast("dict[str, Any]", panel_tree_data)
                )
            except Exception as exc:  # pragma: no cover - defensive path
                QMessageBox.warning(
                    self.window, "Restore", f"Could not restore panel tree: {exc}"
                )
                self.window.panel_tree = PanelTreeModel()
        self.window.layout_rows = self.window.layout_coordinator.rows_from_tree(
            self.window.panel_tree.root
        )

        tabs_payload_raw = self.window.settings.get_json(
            self.window.settings.window_key(self.window.window_id, "tabs"), {}
        )
        tabs_payload = (
            cast("dict[str, Any]", tabs_payload_raw)
            if isinstance(tabs_payload_raw, dict)
            else {}
        )
        raw_panels_obj = tabs_payload.get("panels", {})
        tabs_state: TabsState = {}
        raw_panels = (
            cast("dict[str, Any]", raw_panels_obj)
            if isinstance(raw_panels_obj, dict)
            else {}
        )
        for panel_id_str, state in raw_panels.items():
            try:
                panel_id = int(panel_id_str)
            except (TypeError, ValueError):
                continue
            if isinstance(state, dict):
                tabs_state[panel_id] = state
        self.window.layout_rows = (
            self.window.layout_coordinator.append_missing_panel_ids(
                self.window.layout_rows,
                list(tabs_state.keys()),
            )
        )
        self.window.layout_coordinator.sync_panel_tree_from_rows()

        preferred_active = None
        raw_active = tabs_payload.get("active_panel_id")
        if raw_active is not None:
            try:
                preferred_active = int(raw_active)
            except (TypeError, ValueError):
                preferred_active = None

        self.window.panels_coordinator.rebuild_from_tree(
            tabs_state=tabs_state, preferred_active_panel=preferred_active
        )

        on_top_value = self.window.settings.value(
            self.window.settings.window_key(self.window.window_id, "on_top"), False
        )
        on_top = (
            on_top_value
            if isinstance(on_top_value, bool)
            else str(on_top_value).strip().lower() in {"1", "true", "yes", "on"}
        )
        self.window.set_on_top(bool(on_top))

        geometry = self.window.settings.value(
            self.window.settings.window_key(self.window.window_id, "geometry")
        )
        if isinstance(geometry, QByteArray):
            self.window.restoreGeometry(geometry)

    def apply_cloned_state(
        self, state: dict[str, Any], *, restore_geometry: bool = False
    ) -> None:
        panel_tree_data = state.get("panel_tree")
        if isinstance(panel_tree_data, dict):
            self.window.panel_tree = PanelTreeModel.from_dict(
                cast("dict[str, Any]", panel_tree_data)
            )
        self.window.layout_rows = self.window.layout_coordinator.rows_from_tree(
            self.window.panel_tree.root
        )

        tabs_state: TabsState = {}
        raw_tabs = deepcopy(state.get("tabs", {}))
        if isinstance(raw_tabs, dict):
            for panel_id, panel_state in cast("dict[str, Any]", raw_tabs).items():
                try:
                    panel_id_int = int(panel_id)
                except (TypeError, ValueError):
                    continue
                if isinstance(panel_state, dict):
                    tabs_state[panel_id_int] = panel_state
        self.window.layout_rows = (
            self.window.layout_coordinator.append_missing_panel_ids(
                self.window.layout_rows,
                list(tabs_state.keys()),
            )
        )
        self.window.layout_coordinator.sync_panel_tree_from_rows()

        preferred_active_panel: int | None
        raw_active_panel = state.get("active_panel_id")
        try:
            preferred_active_panel = (
                int(raw_active_panel) if raw_active_panel is not None else None
            )
        except (TypeError, ValueError):
            preferred_active_panel = None

        self.window.panels_coordinator.rebuild_from_tree(
            tabs_state=tabs_state,
            preferred_active_panel=preferred_active_panel,
        )
        self.window.set_on_top(bool(state.get("on_top", False)))
        if restore_geometry:
            geometry_b64 = state.get("geometry_b64")
            if isinstance(geometry_b64, str) and geometry_b64:
                self.restore_geometry_from_b64(geometry_b64)
