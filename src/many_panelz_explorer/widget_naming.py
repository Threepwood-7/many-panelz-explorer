from __future__ import annotations


def window_widget_id(window_id: str) -> str:
    return f"window:{window_id}"


def panel_widget_id(panel_id: int) -> str:
    return f"panel:{int(panel_id)}"


def tab_widget_id(panel_id: int, tab_uuid: str) -> str:
    return f"{panel_widget_id(panel_id)}:tab:{tab_uuid}"


def panel_control_widget_id(panel_id: int, control: str) -> str:
    return f"{panel_widget_id(panel_id)}:{control.strip()}"


def file_list_widget_id(panel_id: int, tab_uuid: str) -> str:
    return f"{tab_widget_id(panel_id, tab_uuid)}:file_list"


def tab_short(tab_uuid: str) -> str:
    return str(tab_uuid).strip()[:8]


def panel_alias(panel_id: int) -> str:
    return f"P{int(panel_id)}"


def tab_alias(panel_id: int, tab_uuid: str) -> str:
    return f"{panel_alias(panel_id)}.T{tab_short(tab_uuid)}"


def panel_control_alias(panel_id: int, control: str) -> str:
    return f"{panel_alias(panel_id)}.{control.strip()}"


def file_list_alias(panel_id: int, tab_uuid: str) -> str:
    return f"{tab_alias(panel_id, tab_uuid)}.file_list"
