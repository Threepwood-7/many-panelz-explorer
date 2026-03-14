from __future__ import annotations

from many_panelz_explorer.ui.window.persistence import (
    _coerce_bool,
    _coerce_int,
    _saved_view_state,
    _tabs_state_from_panels_payload,
    _window_tabs_payload,
)


def test_coerce_int_accepts_supported_values_only() -> None:
    assert _coerce_int(True) == 1
    assert _coerce_int(4) == 4
    assert _coerce_int("5") == 5
    assert _coerce_int("bad") is None
    assert _coerce_int(4.2) is None


def test_window_tabs_payload_ignores_invalid_rows() -> None:
    payload = _window_tabs_payload(
        {
            "active_panel_id": "7",
            "panels": {
                "1": {"panel_id": 1, "tabs": [{"path": "c:/one"}]},
                "bad": {"panel_id": 2},
                "3": "invalid",
            },
        }
    )

    assert payload == {
        "active_panel_id": 7,
        "panels": {"1": {"panel_id": 1, "tabs": [{"path": "c:/one"}]}},
    }


def test_tabs_state_from_panels_payload_converts_keys_to_ints() -> None:
    tabs_state = _tabs_state_from_panels_payload(
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
    payload = _saved_view_state(
        {
            "window_id": 123,
            "panel_tree": {"root": {"type": "leaf", "panel_id": 1}},
            "tabs": {"4": {"panel_id": 4, "tabs": [{"path": "c:/root"}]}},
            "active_panel_id": "4",
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
        "on_top": True,
        "maximized": True,
        "geometry_b64": "abc123",
    }


def test_coerce_bool_accepts_common_truthy_strings() -> None:
    assert _coerce_bool(True) is True
    assert _coerce_bool("on") is True
    assert _coerce_bool("false") is False
