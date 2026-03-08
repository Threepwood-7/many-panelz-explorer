import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

import many_panelz_explorer.panel_widget as panel_widget_module
from many_panelz_explorer.panel_widget import PanelWidget
from many_panelz_explorer import widget_naming


def _norm(path: Path | str) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _index_for_root(panel: PanelWidget, target: Path) -> int:
    for idx, root in enumerate(panel._root_paths):
        if _norm(root) == _norm(target):
            return idx
    raise AssertionError(f"root not found: {target}")


def _button_for_root(panel: PanelWidget, target: Path):
    for idx, root in enumerate(panel._root_paths):
        if _norm(root) == _norm(target):
            return panel.root_buttons[idx]
    raise AssertionError(f"button root not found: {target}")


def test_panel_toolbar_controls_active_tab_navigation(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    b = a / "b"
    c = root / "c"
    b.mkdir(parents=True)
    c.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root, a, c],
    )
    qtbot.addWidget(panel)
    panel.show()

    tab = panel.add_tab(root)
    assert len(panel.root_buttons) == 3
    assert panel.back_btn.text() == "<"
    assert panel.forward_btn.text() == ">"
    assert panel.up_btn.text() == ".."
    assert panel.root_btn.text() == "\\"
    tab.set_path(a)
    tab.set_path(b)
    assert tab.current_path() == b

    panel.back_btn.click()
    assert tab.current_path() == a

    panel.forward_btn.click()
    assert tab.current_path() == b

    panel.up_btn.click()
    assert tab.current_path() == a

    panel.refresh_btn.click()
    assert tab.current_path() == a


def test_panel_toolbar_address_updates_on_tab_switch(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    c = root / "c"
    a.mkdir(parents=True)
    c.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root, a, c],
    )
    qtbot.addWidget(panel)
    panel.show()

    tab_a = panel.add_tab(a)
    tab_c = panel.add_tab(c)
    _ = tab_a, tab_c

    panel.tabs.setCurrentIndex(0)
    qtbot.waitUntil(lambda: _norm(panel.address_edit.text()) == _norm(a))

    panel.tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: _norm(panel.address_edit.text()) == _norm(c))

    panel.address_edit.setText(str(root))
    panel.address_edit.returnPressed.emit()
    assert panel.current_tab() is not None
    assert panel.current_tab().current_path() == root


def test_address_autocomplete_shows_live_directory_suggestions(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    alpha = root / "alpha"
    alpine = root / "alpine"
    beta = root / "beta"
    alpha.mkdir(parents=True)
    alpine.mkdir(parents=True)
    beta.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    panel.address_edit.setFocus()
    panel.address_edit.selectAll()
    QTest.keyClicks(panel.address_edit, "al")

    qtbot.waitUntil(
        lambda: len(panel._address_completion_model.stringList()) >= 2,
        timeout=2000,
    )
    suggestions = panel._address_completion_model.stringList()
    assert _norm(alpha) in {_norm(item) for item in suggestions}
    assert _norm(alpine) in {_norm(item) for item in suggestions}
    assert panel._address_completer.popup().isVisible() is True


def test_address_autocomplete_respects_show_hidden_setting(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    visible = root / "visible"
    hidden = root / ".hidden_dir"
    visible.mkdir(parents=True)
    hidden.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=False,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    panel.address_edit.setFocus()
    panel.address_edit.selectAll()
    QTest.keyClicks(panel.address_edit, ".hid")
    qtbot.wait(220)
    suggestions_hidden_off = panel._address_completion_model.stringList()
    assert _norm(hidden) not in {_norm(item) for item in suggestions_hidden_off}

    panel.set_show_hidden(True)
    panel.address_edit.selectAll()
    QTest.keyClicks(panel.address_edit, ".hid")
    qtbot.waitUntil(
        lambda: _norm(hidden)
        in {_norm(item) for item in panel._address_completion_model.stringList()},
        timeout=2000,
    )


def test_address_autocomplete_activation_fills_and_navigates_on_enter(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    alpha = root / "alpha"
    alpha.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)

    panel.address_edit.setFocus()
    panel.address_edit.selectAll()
    QTest.keyClicks(panel.address_edit, "al")
    qtbot.waitUntil(
        lambda: _norm(alpha)
        in {_norm(item) for item in panel._address_completion_model.stringList()},
        timeout=2000,
    )

    panel._on_address_completion_activated(str(alpha))
    assert _norm(panel.address_edit.text()) == _norm(alpha)

    panel.address_edit.returnPressed.emit()
    assert tab.current_path() == alpha


def test_root_picker_navigates_active_tab_only(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    c = root / "c"
    a.mkdir(parents=True)
    c.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root, a, c],
    )
    qtbot.addWidget(panel)
    panel.show()

    tab_a = panel.add_tab(a)
    tab_c = panel.add_tab(c)

    panel.tabs.setCurrentWidget(tab_a)
    _button_for_root(panel, root).click()

    assert tab_a.current_path() == root
    assert tab_c.current_path() == c


def test_toolbar_back_forward_enablement_tracks_history(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    b = a / "b"
    b.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root, a],
    )
    qtbot.addWidget(panel)
    panel.show()

    tab = panel.add_tab(root)
    assert panel.back_btn.isEnabled() is False
    assert panel.forward_btn.isEnabled() is False

    tab.set_path(a)
    tab.set_path(b)
    assert panel.back_btn.isEnabled() is True
    assert panel.forward_btn.isEnabled() is False

    panel.back_btn.click()
    assert panel.forward_btn.isEnabled() is True


def test_root_dropdown_is_optional(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    a.mkdir(parents=True)

    panel_default = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root, a],
    )
    qtbot.addWidget(panel_default)
    panel_default.show()
    panel_default.add_tab(root)
    assert panel_default.root_combo.isVisible() is False
    assert len(panel_default.root_buttons) == 2

    panel_with_dropdown = PanelWidget(
        panel_id=2,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [root, a],
    )
    qtbot.addWidget(panel_with_dropdown)
    panel_with_dropdown.show()
    panel_with_dropdown.add_tab(root)
    assert panel_with_dropdown.root_combo.isVisible() is True
    qtbot.waitUntil(lambda: panel_with_dropdown.root_combo.width() > 0)
    assert len(panel_with_dropdown.root_buttons) == 2

    index = _index_for_root(panel_with_dropdown, a)
    panel_with_dropdown._on_root_selected(index)
    assert panel_with_dropdown.current_tab() is not None
    assert panel_with_dropdown.current_tab().current_path() == a


def test_root_controls_sorted_alphabetically(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    aa = root / "AA"
    h2 = root / "HDD02"
    h1 = root / "HDD01"
    aa.mkdir(parents=True)
    h1.mkdir(parents=True)
    h2.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [h2, aa, h1],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    button_labels = [button.text() for button in panel.root_buttons]
    combo_labels = [
        panel.root_combo.itemText(i) for i in range(panel.root_combo.count())
    ]

    assert button_labels == ["AA", "HDD01", "HDD02"]
    assert combo_labels == ["AA", "HDD01", "HDD02"]


def test_toolbar_visibility_flags_are_independent(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    qtbot.waitUntil(lambda: panel.root_combo.isVisible() and panel.root_combo.width() > 0)
    assert panel.refresh_btn.isVisible() is True
    assert panel.root_buttons_host.isVisible() is True
    assert panel.address_edit.isVisible() is True
    assert panel.back_btn.isVisible() is True

    panel.apply_toolbar_visibility(
        show_refresh_button=False,
        show_root_buttons=False,
        show_root_dropdown=False,
        show_address_bar=False,
        show_navigation_buttons=False,
    )
    assert panel.refresh_btn.isVisible() is False
    assert panel.root_buttons_host.isVisible() is False
    assert panel.root_combo.isVisible() is False
    assert panel.address_edit.isVisible() is False
    assert panel.back_btn.isVisible() is False
    assert panel.forward_btn.isVisible() is False
    assert panel.up_btn.isVisible() is False
    assert panel.root_btn.isVisible() is False

    panel.apply_toolbar_visibility(
        show_refresh_button=False,
        show_root_buttons=True,
        show_root_dropdown=False,
        show_address_bar=True,
        show_navigation_buttons=False,
    )
    assert panel.refresh_btn.isVisible() is False
    assert panel.root_buttons_host.isVisible() is True
    assert panel.root_combo.isVisible() is False
    assert panel.address_edit.isVisible() is True
    assert panel.back_btn.isVisible() is False

    panel.apply_toolbar_visibility(
        show_refresh_button=True,
        show_root_buttons=True,
        show_root_dropdown=True,
        show_address_bar=True,
        show_navigation_buttons=True,
    )
    qtbot.waitUntil(lambda: panel.root_combo.isVisible() and panel.root_combo.width() > 0)
    assert panel.refresh_btn.isVisible() is True
    assert panel.root_buttons_host.isVisible() is True
    assert panel.address_edit.isVisible() is True
    assert panel.back_btn.isVisible() is True


def test_windows_mountpoint_uses_last_segment_and_tooltip(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    mount = root / "M" / "HDD01"
    mount.mkdir(parents=True)

    monkeypatch.setattr(panel_widget_module, "_is_windows", lambda: True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [mount],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    assert panel.root_buttons[0].text() == "HDD01"
    assert panel.root_buttons[0].toolTip().endswith("HDD01")
    assert panel.root_combo.itemText(0) == "HDD01"
    assert str(
        panel.root_combo.itemData(0, panel_widget_module.Qt.ToolTipRole)
    ).endswith("HDD01")


def test_alt_down_shows_current_tab_history_menu(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    b = a / "b"
    b.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)
    tab.set_path(a)
    tab.set_path(b)

    panel.address_edit.setFocus()
    QTest.keyClick(panel.address_edit, Qt.Key_Down, Qt.AltModifier)

    qtbot.waitUntil(lambda: panel._history_menu is not None)
    labels = [action.text() for action in panel._history_menu.actions()]
    assert any(str(b) in text for text in labels)
    assert any(str(a) in text for text in labels)
    assert any(str(root) in text for text in labels)


def test_column_widths_sync_across_tabs_in_panel(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()

    first_tab = panel.add_tab(root)
    second_tab = panel.add_tab(root)
    assert first_tab is not None
    assert second_tab is not None

    original_width = second_tab.view.columnWidth(0)
    first_tab.view.setColumnWidth(0, 420)
    qtbot.wait(40)
    assert second_tab.view.columnWidth(0) == original_width
    qtbot.waitUntil(lambda: second_tab.view.columnWidth(0) == 420)

    second_tab.view.setColumnWidth(2, 260)
    qtbot.wait(40)
    assert first_tab.view.columnWidth(2) != 260
    qtbot.waitUntil(lambda: first_tab.view.columnWidth(2) == 260)


def test_column_widths_persist_when_navigating_directories_in_same_tab(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()

    tab = panel.add_tab(root)
    tab.view.setColumnWidth(0, 377)
    qtbot.waitUntil(lambda: tab.view.columnWidth(0) == 377)

    tab.set_path(child)
    qtbot.waitUntil(lambda: tab.current_path() == child)
    qtbot.waitUntil(lambda: tab.view.columnWidth(0) == 377)


def test_new_tab_preserves_current_tab_column_widths(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()

    current = panel.add_tab(root)
    current.view.setColumnWidth(0, 410)
    current.view.setColumnWidth(1, 130)
    current.view.setColumnWidth(2, 240)
    current.view.setColumnWidth(3, 190)

    new_tab = panel.add_tab(root)
    qtbot.waitUntil(lambda: new_tab.view.columnWidth(0) == 410)
    assert new_tab.view.columnWidth(1) == 130
    assert new_tab.view.columnWidth(2) == 240
    assert new_tab.view.columnWidth(3) == 190


def test_column_widths_persist_in_panel_state(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)
    tab.view.setColumnWidth(0, 333)
    tab.view.setColumnWidth(1, 140)
    tab.view.setColumnWidth(2, 220)
    tab.view.setColumnWidth(3, 180)

    state = panel.serialize_state()

    restored = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(restored)
    restored.show()
    restored.restore_state(state)

    restored_tab = restored.current_tab()
    assert restored_tab is not None
    qtbot.waitUntil(lambda: restored_tab.view.columnWidth(0) == 333)
    assert restored_tab.view.columnWidth(1) == 140
    assert restored_tab.view.columnWidth(2) == 220
    assert restored_tab.view.columnWidth(3) == 180


def test_panel_controls_keep_root_combo_minimum_width_for_visibility(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    assert panel.minimumWidth() == 0
    assert panel.root_combo.minimumWidth() == PanelWidget.ROOT_COMBO_MIN_WIDTH
    assert panel.address_edit.minimumWidth() == 0
    assert panel.tabs.minimumWidth() == 0
    assert panel.tabs.tabBar().minimumWidth() == 0
    assert panel.tabs.tabBar().elideMode() == Qt.TextElideMode.ElideRight
    assert panel.tabs.tabBar().usesScrollButtons() is False


def test_type_to_focus_shows_transient_filter_overlay(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")
    (root / "beta.txt").write_text("b", encoding="utf-8")

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)
    tab.view.setFocus()

    QTest.keyClick(tab.view, Qt.Key_A)
    qtbot.waitUntil(lambda: panel.filter_edit.isVisible())
    assert panel.filter_edit.text().lower() == "a"
    assert tab.model.nameFilters() == ["*a*"]

    QTest.keyClick(panel.filter_edit, Qt.Key_Escape)
    assert panel.filter_edit.isVisible() is False
    assert tab.model.nameFilters() == []


def test_filter_overlay_appears_in_bottom_right_of_file_list(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.resize(920, 520)
    panel.show()
    tab = panel.add_tab(root)
    tab.view.setFocus()

    QTest.keyClick(tab.view, Qt.Key_A)
    qtbot.waitUntil(lambda: panel.filter_edit.isVisible())

    overlay_rect = panel.filter_edit.geometry()
    view_top_left = tab.view.mapTo(panel, QPoint(0, 0))
    view_right = view_top_left.x() + tab.view.width()
    view_bottom = view_top_left.y() + tab.view.height()

    assert overlay_rect.right() <= view_right
    assert overlay_rect.bottom() <= view_bottom
    assert abs((view_right - overlay_rect.right()) - 8) <= 2
    assert abs((view_bottom - overlay_rect.bottom()) - 8) <= 2


def test_widget_identity_contract_for_panel_and_file_list(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    first_tab = panel.add_tab(root)
    second_tab = panel.add_tab(root)

    assert first_tab.tab_uuid != second_tab.tab_uuid
    assert panel.objectName() == widget_naming.object_name_for_id(
        widget_naming.panel_widget_id(1)
    )
    assert str(panel.property("widget_id")) == widget_naming.panel_widget_id(1)
    assert str(panel.address_edit.property("widget_alias")) == "P1.address"

    expected_file_list_id = widget_naming.file_list_widget_id(1, first_tab.tab_uuid)
    expected_file_list_alias = widget_naming.file_list_alias(1, first_tab.tab_uuid)
    assert str(first_tab.view.property("widget_id")) == expected_file_list_id
    assert str(first_tab.view.property("widget_alias")) == expected_file_list_alias


def test_widget_map_overlay_can_be_toggled(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)
    assert tab is not None

    panel.set_widget_map_enabled(True)
    qtbot.waitUntil(lambda: panel._widget_map_overlay.isVisible())

    aliases = [entry.alias for entry in panel.widget_map_entries()]
    assert any(alias.endswith(".file_list") for alias in aliases)
    assert "P1.address" in aliases

    panel.set_widget_map_enabled(False)
    assert panel._widget_map_overlay.isVisible() is False


def test_type_to_focus_does_not_show_filter_overlay_from_address_bar(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)
    assert tab.model.nameFilters() == []

    panel.address_edit.setFocus()
    QTest.keyClick(panel.address_edit, Qt.Key_A)

    qtbot.wait(50)
    assert panel.filter_edit.isVisible() is False
    assert tab.model.nameFilters() == []


def test_type_to_focus_does_not_show_filter_overlay_from_toolbar_button(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)
    assert tab.model.nameFilters() == []

    panel.back_btn.setFocus()
    QTest.keyClick(panel.back_btn, Qt.Key_A)

    qtbot.wait(50)
    assert panel.filter_edit.isVisible() is False
    assert tab.model.nameFilters() == []


def test_root_controls_fallback_when_provider_returns_empty(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    assert panel.root_buttons
    assert panel._root_paths


def test_root_controls_fallback_when_provider_raises(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    def _raising_provider(_current):
        raise RuntimeError("roots unavailable")

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=_raising_provider,
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    assert panel.root_buttons
    assert panel._root_paths


def test_root_buttons_host_can_shrink_under_narrow_width(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    roots: list[Path] = []
    for name in ["AA", "BB", "CC", "DD", "EE", "FF", "GG"]:
        path = root / name
        path.mkdir()
        roots.append(path)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [root, *roots],
    )
    qtbot.addWidget(panel)
    panel.resize(260, 180)
    panel.show()
    panel.add_tab(root)
    qtbot.waitUntil(lambda: panel.root_combo.isVisible() and panel.root_combo.width() > 0)

    assert panel.root_buttons_host.isVisible() is True
    assert panel.root_buttons
