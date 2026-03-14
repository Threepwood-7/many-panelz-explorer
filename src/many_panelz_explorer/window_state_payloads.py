"""Typed normalization helpers for persisted window-state payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .panel_tree import PanelTreeNodePayload, PanelTreePayload
    from .ui.window.state_types import (
        PanelState,
        SavedViewState,
        TabsState,
        TabState,
        WindowTabsPayload,
    )


def _mapping_payload(raw: object) -> Mapping[object, object] | None:
    """Return the raw value as a generic mapping when possible."""

    if isinstance(raw, Mapping):
        mapping: dict[object, object] = {}
        for key, value in cast("Mapping[object, object]", raw).items():
            mapping[key] = value
        return mapping
    return None


def _list_payload(raw: object) -> list[object] | None:
    """Return the raw value as a shallow object list when possible."""

    if isinstance(raw, list):
        values: list[object] = []
        for item in cast("list[object]", raw):
            values.append(item)
        return values
    return None


def string_list_payload(raw: object) -> list[str]:
    """Normalize a raw list payload into string values."""

    values = _list_payload(raw)
    if values is None:
        return []
    return [str(item) for item in values]


def coerce_int(value: object) -> int | None:
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


def coerce_bool(value: object) -> bool:
    """Normalize persisted truthy values into a boolean."""

    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def coerce_float(value: object) -> float | None:
    """Normalize persisted float-like values when possible."""

    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def panel_tree_node_payload(raw: object) -> PanelTreeNodePayload | None:
    """Return a validated panel-tree node payload."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return None

    node_type = str(mapping.get("type", "")).strip().lower()
    if node_type == "leaf":
        panel_id = coerce_int(mapping.get("panel_id"))
        if panel_id is None:
            return None
        return {"type": "leaf", "panel_id": panel_id}

    if node_type == "split":
        orientation_value = mapping.get("orientation")
        ratio = coerce_float(mapping.get("ratio", 0.5))
        left = panel_tree_node_payload(mapping.get("left"))
        right = panel_tree_node_payload(mapping.get("right"))
        if orientation_value is None or ratio is None or left is None or right is None:
            return None
        return {
            "type": "split",
            "orientation": str(orientation_value),
            "ratio": ratio,
            "left": left,
            "right": right,
        }

    return None


def panel_tree_payload(raw: object) -> PanelTreePayload | None:
    """Return a panel-tree payload when the raw value is a mapping."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return None
    return {"root": panel_tree_node_payload(mapping.get("root"))}


def tab_state_payload(raw: object) -> TabState | None:
    """Return a normalized tab payload when a valid path is present."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return None

    path_value = mapping.get("path")
    if path_value is None:
        return None
    return {"path": str(path_value)}


def panel_state_payload(raw: object) -> PanelState | None:
    """Normalize a raw panel payload into the shared serialized state shape."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return None

    panel_state: PanelState = {}

    panel_id = coerce_int(mapping.get("panel_id"))
    if panel_id is not None:
        panel_state["panel_id"] = panel_id

    current_index = coerce_int(mapping.get("current_index"))
    if current_index is not None:
        panel_state["current_index"] = current_index

    tabs_raw = _list_payload(mapping.get("tabs"))
    if tabs_raw is not None:
        tabs: list[TabState] = []
        for tab_raw in tabs_raw:
            tab_state = tab_state_payload(tab_raw)
            if tab_state is not None:
                tabs.append(tab_state)
        panel_state["tabs"] = tabs

    widths_raw = _list_payload(mapping.get("column_widths"))
    if widths_raw is not None:
        widths: list[int] = []
        for raw_width in widths_raw:
            width = coerce_int(raw_width)
            if width is not None:
                widths.append(width)
        panel_state["column_widths"] = widths

    return panel_state


def tabs_state_from_panels_payload(raw: object) -> TabsState:
    """Parse persisted panel payloads into integer-keyed tab state."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return {}

    tabs_state: TabsState = {}
    for panel_id_raw, panel_state_raw in mapping.items():
        panel_id = coerce_int(panel_id_raw)
        panel_state = panel_state_payload(panel_state_raw)
        if panel_id is None or panel_state is None:
            continue
        tabs_state[panel_id] = panel_state
    return tabs_state


def window_tabs_payload(raw: object) -> WindowTabsPayload:
    """Normalize the settings tabs payload into a typed mapping."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return {"active_panel_id": None, "panels": {}}

    return {
        "active_panel_id": coerce_int(mapping.get("active_panel_id")),
        "panels": {
            str(panel_id): panel_state
            for panel_id, panel_state in tabs_state_from_panels_payload(
                mapping.get("panels", {})
            ).items()
        },
    }


def saved_view_state(raw: object) -> SavedViewState:
    """Normalize saved-view payloads into the window-state contract."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return {
            "window_id": "",
            "panel_tree": {"root": None},
            "tabs": {},
            "active_panel_id": None,
            "on_top": False,
            "maximized": False,
        }

    payload: SavedViewState = {
        "window_id": str(mapping.get("window_id", "")),
        "panel_tree": panel_tree_payload(mapping.get("panel_tree")) or {"root": None},
        "tabs": tabs_state_from_panels_payload(mapping.get("tabs", {})),
        "active_panel_id": coerce_int(mapping.get("active_panel_id")),
        "on_top": coerce_bool(mapping.get("on_top", False)),
        "maximized": coerce_bool(mapping.get("maximized", False)),
    }
    geometry_b64 = mapping.get("geometry_b64")
    if isinstance(geometry_b64, str) and geometry_b64:
        payload["geometry_b64"] = geometry_b64
    return payload


def saved_views_payload(raw: object) -> dict[str, SavedViewState]:
    """Normalize the saved-view mapping stored in session settings."""

    mapping = _mapping_payload(raw)
    if mapping is None:
        return {}

    views: dict[str, SavedViewState] = {}
    for key, value in mapping.items():
        if _mapping_payload(value) is None:
            continue
        views[str(key)] = saved_view_state(value)
    return views
