"""Shared panel layout and persistence state aliases for window coordinators."""

from __future__ import annotations

type PanelState = dict[str, object]
type TabsState = dict[int, PanelState]
type PanelRows = list[list[int]]
