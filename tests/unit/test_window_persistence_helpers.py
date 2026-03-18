from __future__ import annotations

from many_panelz_explorer.window_state_payloads import (
    coerce_bool,
    coerce_int,
    saved_view_state,
    tabs_state_from_panels_payload,
    window_tabs_payload,
)


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
        "panels": {"1": {"panel_id": 1, "tabs": [{"path": "c:/one"}]}},
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
        1: {"panel_id": 1, "current_index": 0},
        2: {"panel_id": 2, "current_index": 1},
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
        "tabs": {4: {"panel_id": 4, "tabs": [{"path": "c:/root"}]}},
        "active_panel_id": 4,
        "recently_closed_tabs": [{"path": "c:/closed", "panel_id": 6}],
        "on_top": True,
        "maximized": True,
        "geometry_b64": "abc123",
    }


def test_coerce_bool_accepts_common_truthy_strings() -> None:
    assert coerce_bool(True) is True
    assert coerce_bool("on") is True
    assert coerce_bool("false") is False
