"""Persistence helpers for saving and restoring window state."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QMessageBox

from ...panel_tree import PanelTreeModel
from .panels import serialize_window_tabs_state

if TYPE_CHECKING:
    from ...window import ExplorerWindow
    from .state_types import (
        PanelState,
        SavedViewState,
        TabsState,
        TabState,
        WindowStatePayload,
        WindowTabsPayload,
    )


def _coerce_int(value: object) -> int | None:
    """Normalize persisted integer-like values when possible."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _coerce_bool(value: object) -> bool:
    """Normalize persisted truthy values into a boolean."""

    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _panel_tree_payload(raw: object) -> dict[str, object] | None:
    """Return a panel-tree payload when the raw value is a mapping."""

    if not isinstance(raw, Mapping):
        return None
    mapping = cast("Mapping[object, object]", raw)
    return {str(key): value for key, value in mapping.items()}


def _tab_state_payload(raw: object) -> TabState | None:
    """Return a normalized tab payload when a valid path is present."""

    if not isinstance(raw, Mapping):
        return None
    mapping = cast("Mapping[object, object]", raw)
    path_value = mapping.get("path")
    if path_value is None:
        return None
    return {"path": str(path_value)}


def _panel_state_payload(raw: object) -> PanelState | None:
    """Normalize a raw panel payload into the shared serialized state shape."""

    if not isinstance(raw, Mapping):
        return None

    mapping = cast("Mapping[object, object]", raw)
    panel_state: PanelState = {}

    panel_id = _coerce_int(mapping.get("panel_id"))
    if panel_id is not None:
        panel_state["panel_id"] = panel_id

    current_index = _coerce_int(mapping.get("current_index"))
    if current_index is not None:
        panel_state["current_index"] = current_index

    tabs_raw = mapping.get("tabs")
    if isinstance(tabs_raw, list):
        tabs: list[TabState] = []
        for tab_raw in cast("list[object]", tabs_raw):
            tab_state = _tab_state_payload(tab_raw)
            if tab_state is not None:
                tabs.append(tab_state)
        panel_state["tabs"] = tabs

    widths_raw = mapping.get("column_widths")
    if isinstance(widths_raw, list):
        widths: list[int] = []
        for raw_width in cast("list[object]", widths_raw):
            width = _coerce_int(raw_width)
            if width is not None:
                widths.append(width)
        panel_state["column_widths"] = widths

    return panel_state


def _tabs_state_from_panels_payload(raw: object) -> TabsState:
    """Parse persisted panel payloads into integer-keyed tab state."""

    if not isinstance(raw, Mapping):
        return {}

    mapping = cast("Mapping[object, object]", raw)
    tabs_state: TabsState = {}
    for panel_id_raw, panel_state_raw in mapping.items():
        panel_id = _coerce_int(panel_id_raw)
        panel_state = _panel_state_payload(panel_state_raw)
        if panel_id is None or panel_state is None:
            continue
        tabs_state[panel_id] = panel_state
    return tabs_state


def _window_tabs_payload(raw: object) -> WindowTabsPayload:
    """Normalize the settings tabs payload into a typed mapping."""

    if not isinstance(raw, Mapping):
        return {"active_panel_id": None, "panels": {}}
    mapping = cast("Mapping[object, object]", raw)
    return {
        "active_panel_id": _coerce_int(mapping.get("active_panel_id")),
        "panels": {
            str(panel_id): panel_state
            for panel_id, panel_state in _tabs_state_from_panels_payload(
                mapping.get("panels", {})
            ).items()
        },
    }


def _saved_view_state(raw: object) -> SavedViewState:
    """Normalize saved-view payloads into the window-state contract."""

    if not isinstance(raw, Mapping):
        return {
            "window_id": "",
            "panel_tree": {},
            "tabs": {},
            "active_panel_id": None,
            "on_top": False,
            "maximized": False,
        }

    mapping = cast("Mapping[object, object]", raw)
    payload: SavedViewState = {
        "window_id": str(mapping.get("window_id", "")),
        "panel_tree": _panel_tree_payload(mapping.get("panel_tree")) or {},
        "tabs": _tabs_state_from_panels_payload(mapping.get("tabs", {})),
        "active_panel_id": _coerce_int(mapping.get("active_panel_id")),
        "on_top": _coerce_bool(mapping.get("on_top", False)),
        "maximized": _coerce_bool(mapping.get("maximized", False)),
    }
    geometry_b64 = mapping.get("geometry_b64")
    if isinstance(geometry_b64, str) and geometry_b64:
        payload["geometry_b64"] = geometry_b64
    return payload


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
