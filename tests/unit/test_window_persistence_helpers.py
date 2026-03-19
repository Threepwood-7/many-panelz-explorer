from __future__ import annotations

from many_panelz_explorer.window_state_payloads import (
    coerce_bool,
    coerce_int,
    panel_state_payload,
    saved_view_state,
    tabs_state_from_panels_payload,
    window_tabs_payload,
)


def _default_group(
    *,
    current_index: int = 0,
    paths: list[str] | None = None,
) -> dict[str, object]:
    tabs = [{"path": path} for path in (paths or [])]
    return {
        "group_id": "main",
        "title": "Main",
        "current_index": current_index,
        "tabs": tabs,
        "column_widths": [],
    }


def test_coerce_int_accepts_supported_values_only() -> None:
    assert coerce_int(True) == 1
    assert coerce_int(4) == 4
    assert coerce_int("5") == 5
    assert coerce_int("bad") is None
    assert coerce_int(4.2) is None


def test_window_tabs_payload_ignores_invalid_rows() -> None:
    payload = window_tabs_payload(
        {
            "active_panel_id": "7",
            "panels": {
                "1": {"panel_id": 1, "tabs": [{"path": "c:/one"}]},
                "bad": {"panel_id": 2},
                "3": "invalid",
            },
            "recently_closed_tabs": [
                {"path": "c:/closed", "panel_id": "2"},
                {"path": "bad"},
            ],
        }
    )

    assert payload == {
        "active_panel_id": 7,
        "panels": {
            "1": {
                "active_group_id": "main",
                "groups": [_default_group(paths=["c:/one"])],
                "panel_id": 1,
                "tab_position_mode": "default",
            }
        },
        "recently_closed_tabs": [{"path": "c:/closed", "panel_id": 2}],
    }


def test_tabs_state_from_panels_payload_converts_keys_to_ints() -> None:
    tabs_state = tabs_state_from_panels_payload(
        {
            "1": {"panel_id": 1, "current_index": 0},
            2: {"panel_id": 2, "current_index": 1},
            "bad": {"panel_id": 3},
        }
    )

    assert tabs_state == {
        1: {
            "active_group_id": "main",
            "groups": [_default_group(current_index=0)],
            "panel_id": 1,
            "tab_position_mode": "default",
        },
        2: {
            "active_group_id": "main",
            "groups": [_default_group(current_index=1)],
            "panel_id": 2,
            "tab_position_mode": "default",
        },
    }


def test_saved_view_state_normalizes_flags_and_geometry() -> None:
    payload = saved_view_state(
        {
            "window_id": 123,
            "panel_tree": {"root": {"type": "leaf", "panel_id": 1}},
            "tabs": {"4": {"panel_id": 4, "tabs": [{"path": "c:/root"}]}},
            "active_panel_id": "4",
            "recently_closed_tabs": [{"path": "c:/closed", "panel_id": "6"}],
            "on_top": "yes",
            "maximized": "1",
            "geometry_b64": "abc123",
        }
    )

    assert payload == {
        "window_id": "123",
        "panel_tree": {"root": {"type": "leaf", "panel_id": 1}},
        "tabs": {
            4: {
                "active_group_id": "main",
                "groups": [_default_group(paths=["c:/root"])],
                "panel_id": 4,
                "tab_position_mode": "default",
            }
        },
        "active_panel_id": 4,
        "recently_closed_tabs": [{"path": "c:/closed", "panel_id": 6}],
        "on_top": True,
        "maximized": True,
        "geometry_b64": "abc123",
    }


def test_tabs_state_payload_normalizes_panel_tab_position_mode() -> None:
    tabs_state = tabs_state_from_panels_payload(
        {
            "1": {"panel_id": 1, "tab_position_mode": "right_horizontal"},
            "2": {"panel_id": 2, "tab_position_mode": "bottom"},
            "3": {"panel_id": 3, "tab_position_mode": "diagonal"},
        }
    )

    assert tabs_state == {
        1: {
            "active_group_id": "main",
            "groups": [_default_group()],
            "panel_id": 1,
            "tab_position_mode": "right_horizontal",
        },
        2: {
            "active_group_id": "main",
            "groups": [_default_group()],
            "panel_id": 2,
            "tab_position_mode": "bottom",
        },
        3: {
            "active_group_id": "main",
            "groups": [_default_group()],
            "panel_id": 3,
            "tab_position_mode": "default",
        },
    }


def test_coerce_bool_accepts_common_truthy_strings() -> None:
    assert coerce_bool(True) is True
    assert coerce_bool("on") is True
    assert coerce_bool("false") is False


def test_panel_state_payload_wraps_legacy_tabs_into_default_group() -> None:
    state = panel_state_payload(
        {
            "panel_id": 9,
            "current_index": "2",
            "tabs": [{"path": "c:/one"}, {"path": "c:/two"}],
            "column_widths": ["10", 20],
        }
    )

    assert state == {
        "panel_id": 9,
        "active_group_id": "main",
        "groups": [
            {
                "group_id": "main",
                "title": "Main",
                "current_index": 2,
                "tabs": [{"path": "c:/one"}, {"path": "c:/two"}],
                "column_widths": [10, 20],
            }
        ],
        "tab_position_mode": "default",
    }


def test_panel_state_payload_falls_back_to_first_valid_group() -> None:
    state = panel_state_payload(
        {
            "panel_id": 4,
            "active_group_id": "missing",
            "groups": [
                {
                    "group_id": "alpha",
                    "title": "Alpha",
                    "current_index": 0,
                    "tabs": [{"path": "c:/alpha"}],
                    "column_widths": [],
                },
                {
                    "group_id": "alpha",
                    "title": "Duplicate",
                    "current_index": 0,
                    "tabs": [{"path": "c:/ignored"}],
                    "column_widths": [],
                },
                {
                    "group_id": "beta",
                    "title": "Beta",
                    "current_index": 0,
                    "tabs": [{"path": "c:/beta"}],
                    "column_widths": [],
                },
            ],
        }
    )

    assert state == {
        "panel_id": 4,
        "active_group_id": "alpha",
        "groups": [
            {
                "group_id": "alpha",
                "title": "Alpha",
                "current_index": 0,
                "tabs": [{"path": "c:/alpha"}],
                "column_widths": [],
            },
            {
                "group_id": "beta",
                "title": "Beta",
                "current_index": 0,
                "tabs": [{"path": "c:/beta"}],
                "column_widths": [],
            },
        ],
        "tab_position_mode": "default",
    }
