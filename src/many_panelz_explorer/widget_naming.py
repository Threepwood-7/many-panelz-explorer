"""Stable widget identity helpers used by tests and diagnostics."""

from __future__ import annotations


def window_widget_id(window_id: str) -> str:
    """Return the stable widget ID for a window."""

    return f"window:{window_id}"


def panel_widget_id(panel_id: int) -> str:
    """Return the stable widget ID for a panel."""

    return f"panel:{int(panel_id)}"


def tab_widget_id(panel_id: int, tab_uuid: str) -> str:
    """Return the stable widget ID for a tab inside a panel."""

    return f"{panel_widget_id(panel_id)}:tab:{tab_uuid}"


def panel_control_widget_id(panel_id: int, control: str) -> str:
    """Return the stable widget ID for a named panel control."""

    return f"{panel_widget_id(panel_id)}:{control.strip()}"


def file_list_widget_id(panel_id: int, tab_uuid: str) -> str:
    """Return the stable widget ID for a tab file-list widget."""

    return f"{tab_widget_id(panel_id, tab_uuid)}:file_list"


def tab_short(tab_uuid: str) -> str:
    """Return a short stable tab identifier for aliases."""

    return str(tab_uuid).strip()[:8]


def panel_alias(panel_id: int) -> str:
    """Return a short human-readable alias for a panel."""

    return f"P{int(panel_id)}"


def tab_alias(panel_id: int, tab_uuid: str) -> str:
    """Return a short human-readable alias for a tab."""

    return f"{panel_alias(panel_id)}.T{tab_short(tab_uuid)}"


def panel_control_alias(panel_id: int, control: str) -> str:
    """Return a short human-readable alias for a panel control."""

    return f"{panel_alias(panel_id)}.{control.strip()}"


def file_list_alias(panel_id: int, tab_uuid: str) -> str:
    """Return a short human-readable alias for a tab file list."""

    return f"{tab_alias(panel_id, tab_uuid)}.file_list"
