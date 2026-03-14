"""Shared panel layout and persistence state aliases for window coordinators."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TabState(TypedDict):
    """Serialized state for one explorer tab."""

    path: str


class PanelState(TypedDict, total=False):
    """Serialized state for one panel and its tabs."""

    panel_id: int
    current_index: int
    tabs: list[TabState]
    column_widths: list[int]


type TabsState = dict[int, PanelState]
type PanelRows = list[list[int]]


class WindowTabsPayload(TypedDict):
    """Persisted tabs payload stored in settings."""

    active_panel_id: int | None
    panels: dict[str, PanelState]


class WindowStatePayload(TypedDict):
    """Serialized window state used for cloning and saved views."""

    window_id: str
    panel_tree: dict[str, object]
    tabs: TabsState
    active_panel_id: int | None
    on_top: bool
    maximized: bool
    geometry_b64: NotRequired[str]


type SavedViewState = WindowStatePayload
