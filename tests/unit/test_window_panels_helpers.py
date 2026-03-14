from __future__ import annotations

from types import SimpleNamespace

from many_panelz_explorer.ui.window.panels import (
    resolve_window_target_panel_id,
    serialize_window_tabs_state,
    window_default_close_warning,
)


class _StateCoordinatorStub:
    def __init__(self, state: dict[str, object]) -> None:
        self._state = state

    def serialize_state(self) -> dict[str, object]:
        return dict(self._state)


class _PanelStub:
    def __init__(self, *, tab_count: int, state: dict[str, object]) -> None:
        self._tab_count = tab_count
        self.state_coordinator = _StateCoordinatorStub(state)

    def tab_count(self) -> int:
        return self._tab_count


def test_serialize_window_tabs_state_collects_each_panel_state() -> None:
    window = SimpleNamespace(
        panel_widgets={
            1: _PanelStub(tab_count=1, state={"panel_id": 1, "tabs": []}),
            2: _PanelStub(tab_count=2, state={"panel_id": 2, "tabs": [{"path": "x"}]}),
        }
    )

    assert serialize_window_tabs_state(window) == {
        1: {"panel_id": 1, "tabs": []},
        2: {"panel_id": 2, "tabs": [{"path": "x"}]},
    }


def test_resolve_window_target_panel_prefers_last_non_source_panel() -> None:
    window = SimpleNamespace(
        layout_rows=[[1, 2], [3, 4]],
        last_non_source_panel_id=4,
    )

    assert resolve_window_target_panel_id(window, 1) == 4


def test_resolve_window_target_panel_falls_back_to_first_other_panel() -> None:
    window = SimpleNamespace(
        layout_rows=[[1, 2], [3]],
        last_non_source_panel_id=1,
    )

    assert resolve_window_target_panel_id(window, 1) == 2


def test_window_default_close_warning_depends_on_panel_and_tab_count() -> None:
    single_panel = _PanelStub(tab_count=1, state={"panel_id": 1, "tabs": []})
    multi_tab_panel = _PanelStub(
        tab_count=2,
        state={"panel_id": 1, "tabs": [{"path": "a"}, {"path": "b"}]},
    )

    safe_window = SimpleNamespace(
        panel_widgets={1: single_panel},
        active_panel_id=1,
    )
    lossy_window = SimpleNamespace(
        panel_widgets={1: multi_tab_panel},
        active_panel_id=1,
    )
    split_window = SimpleNamespace(
        panel_widgets={1: single_panel, 2: single_panel},
        active_panel_id=1,
    )

    assert window_default_close_warning(safe_window) is False
    assert window_default_close_warning(lossy_window) is True
    assert window_default_close_warning(split_window) is True
