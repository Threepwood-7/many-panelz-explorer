"""Shared normalization helpers for panel tab-position settings and state."""

from __future__ import annotations

TAB_POSITION_MODE_DEFAULT = "default"
TAB_POSITION_MODE_TOP = "top"
TAB_POSITION_MODE_BOTTOM = "bottom"
TAB_POSITION_MODE_LEFT = "left"
TAB_POSITION_MODE_LEFT_HORIZONTAL = "left_horizontal"
TAB_POSITION_MODE_RIGHT = "right"
TAB_POSITION_MODE_RIGHT_HORIZONTAL = "right_horizontal"

ALLOWED_DEFAULT_TAB_POSITIONS = {
    TAB_POSITION_MODE_TOP,
    TAB_POSITION_MODE_BOTTOM,
    TAB_POSITION_MODE_LEFT,
    TAB_POSITION_MODE_LEFT_HORIZONTAL,
    TAB_POSITION_MODE_RIGHT,
    TAB_POSITION_MODE_RIGHT_HORIZONTAL,
}
ALLOWED_PANEL_TAB_POSITION_MODES = {
    TAB_POSITION_MODE_DEFAULT,
    TAB_POSITION_MODE_TOP,
    TAB_POSITION_MODE_BOTTOM,
    TAB_POSITION_MODE_LEFT,
    TAB_POSITION_MODE_LEFT_HORIZONTAL,
    TAB_POSITION_MODE_RIGHT,
    TAB_POSITION_MODE_RIGHT_HORIZONTAL,
}


def normalize_default_tab_position(value: object) -> str:
    """Normalize a global default tab-position string."""

    normalized = str(value or "").strip().lower()
    if normalized in ALLOWED_DEFAULT_TAB_POSITIONS:
        return normalized
    return TAB_POSITION_MODE_TOP


def normalize_panel_tab_position_mode(value: object) -> str:
    """Normalize a per-panel tab-position mode string."""

    normalized = str(value or "").strip().lower()
    if normalized in ALLOWED_PANEL_TAB_POSITION_MODES:
        return normalized
    return TAB_POSITION_MODE_DEFAULT


def resolve_tab_position_mode(
    mode: object,
    *,
    default_tab_position: object,
) -> str:
    """Resolve a per-panel mode into the effective tab-position setting."""

    normalized_mode = normalize_panel_tab_position_mode(mode)
    if normalized_mode == TAB_POSITION_MODE_DEFAULT:
        return normalize_default_tab_position(default_tab_position)
    return normalized_mode
