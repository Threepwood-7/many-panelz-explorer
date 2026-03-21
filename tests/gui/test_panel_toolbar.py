import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle, QStyleOptionTab, QTabBar
from threep_commons.qt.widget_identity import object_name_for_id

from many_panelz_explorer import widget_naming
from many_panelz_explorer.panel_widget import PanelWidget


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


def _action_for_root(menu, target: Path):
    for action in menu.actions():
        if _norm(action.toolTip()) == _norm(target):
            return action
    raise AssertionError(f"menu root not found: {target}")


def _horizontal_side_text_dark_pixel_count(tab_bar: QTabBar, index: int) -> int:
    """Return the number of dark pixels inside one horizontal side-tab label."""

    option = QStyleOptionTab()
    tab_bar.initStyleOption(option, index)
    option.text = tab_bar.tabText(index)
    if option.shape == QTabBar.Shape.RoundedWest:
        option.shape = QTabBar.Shape.RoundedNorth
    elif option.shape == QTabBar.Shape.TriangularWest:
        option.shape = QTabBar.Shape.TriangularNorth
    elif option.shape == QTabBar.Shape.RoundedEast:
        option.shape = QTabBar.Shape.RoundedNorth
    elif option.shape == QTabBar.Shape.TriangularEast:
        option.shape = QTabBar.Shape.TriangularNorth
    text_rect = tab_bar.style().subElementRect(
        QStyle.SubElement.SE_TabBarTabText,
        option,
        tab_bar,
    )
    text_rect = text_rect.adjusted(2, 2, -2, -2)
    pixmap = QPixmap(tab_bar.size())
    tab_bar.render(pixmap)
    image = pixmap.toImage()
    dark_pixels = 0
    for x_pos in range(text_rect.left(), text_rect.right() + 1):
        for y_pos in range(text_rect.top(), text_rect.bottom() + 1):
            if image.pixelColor(x_pos, y_pos).value() < 200:
                dark_pixels += 1
    return dark_pixels


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
    tab.navigation.set_path(a)
    tab.navigation.set_path(b)
    assert tab.navigation.path == b

    panel.back_btn.click()
    assert tab.navigation.path == a

    panel.forward_btn.click()
    assert tab.navigation.path == b

    panel.up_btn.click()
    assert tab.navigation.path == a

    panel.refresh_btn.click()
    assert tab.navigation.path == a


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
    assert panel.current_tab().navigation.path == root


def test_address_submission_normalizes_windows_slashes(qtbot, tmp_path: Path) -> None:
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

    panel.address_edit.setText(str(child).replace("\\", "/"))
    panel.address_edit.returnPressed.emit()

    qtbot.waitUntil(lambda: tab.navigation.path == child)
    assert panel.address_edit.text() == str(child)


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
        lambda: len(panel.address_completion_model.stringList()) >= 2,
        timeout=2000,
    )
    suggestions = panel.address_completion_model.stringList()
    assert _norm(alpha) in {_norm(item) for item in suggestions}
    assert _norm(alpine) in {_norm(item) for item in suggestions}
    assert panel.address_completer.popup().isVisible() is True


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
    suggestions_hidden_off = panel.address_completion_model.stringList()
    assert _norm(hidden) not in {_norm(item) for item in suggestions_hidden_off}

    panel.set_show_hidden(True)
    panel.address_edit.selectAll()
    QTest.keyClicks(panel.address_edit, ".hid")
    qtbot.waitUntil(
        lambda: (
            _norm(hidden)
            in {_norm(item) for item in panel.address_completion_model.stringList()}
        ),
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
        lambda: (
            _norm(alpha)
            in {_norm(item) for item in panel.address_completion_model.stringList()}
        ),
        timeout=2000,
    )

    panel.address_edit.completer().activated.emit(str(alpha))
    assert _norm(panel.address_edit.text()) == _norm(alpha)

    panel.address_edit.returnPressed.emit()
    assert tab.navigation.path == alpha


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

    assert tab_a.navigation.path == root
    assert tab_c.navigation.path == c


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

    tab.navigation.set_path(a)
    tab.navigation.set_path(b)
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
    panel_with_dropdown.root_combo.activated.emit(index)
    assert panel_with_dropdown.current_tab() is not None
    assert panel_with_dropdown.current_tab().navigation.path == a


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


def test_blank_tab_bar_double_click_duplicates_active_tab(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    root.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.resize(900, 300)
    panel.show()
    panel.add_tab(root)

    tab_bar = panel.tabs.tabBar()
    qtbot.waitUntil(lambda: panel.tabs.width() > tab_bar.geometry().right() + 12)
    blank_point = QPoint(panel.tabs.width() - 6, tab_bar.geometry().center().y())

    QTest.mouseDClick(panel.tabs, Qt.LeftButton, Qt.NoModifier, blank_point)

    assert panel.tab_count() == 2
    assert panel.current_tab() is not None
    assert panel.current_tab().navigation.path == root


@pytest.mark.parametrize(
    "tab_position_mode",
    ["left_horizontal", "right_horizontal"],
)
def test_horizontal_side_tabs_render_correctly_without_tab_switch(
    qtbot,
    tmp_path: Path,
    tab_position_mode: str,
) -> None:
    root = tmp_path / "root"
    first = root / "H06T90"
    second = root / "H16T00"
    first.mkdir(parents=True)
    second.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.resize(900, 300)
    panel.show()
    panel.add_tab(first)
    panel.add_tab(second)

    panel.presentation_coordinator.apply_tab_position(
        tab_position_mode=tab_position_mode,
        default_tab_position="top",
    )

    tab_bar = panel.tabs.tabBar()
    qtbot.waitUntil(
        lambda: all(
            tab_bar.tabRect(index).width() > tab_bar.tabRect(index).height()
            for index in range(tab_bar.count())
        )
    )

    assert all(
        tab_bar.tabSizeHint(index).width() > tab_bar.tabSizeHint(index).height()
        for index in range(tab_bar.count())
    )
    assert all(
        tab_bar.tabRect(index).width() > tab_bar.tabRect(index).height()
        for index in range(tab_bar.count())
    )
    qtbot.waitUntil(
        lambda: all(
            tab_bar.tabButton(index, QTabBar.ButtonPosition.RightSide).x()
            >= tab_bar.tabRect(index).right()
            - tab_bar.tabButton(index, QTabBar.ButtonPosition.RightSide).width()
            - 6
            for index in range(tab_bar.count())
        )
    )
    current_index = tab_bar.currentIndex()
    qtbot.waitUntil(
        lambda: _horizontal_side_text_dark_pixel_count(tab_bar, current_index) > 40
    )


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

    qtbot.waitUntil(
        lambda: panel.root_combo.isVisible() and panel.root_combo.width() > 0
    )
    assert panel.refresh_btn.isVisible() is True
    assert panel.root_buttons_host.isVisible() is True
    assert panel.address_edit.isVisible() is True
    assert panel.back_btn.isVisible() is True

    panel.presentation_coordinator.apply_toolbar_visibility(
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

    panel.presentation_coordinator.apply_toolbar_visibility(
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

    panel.presentation_coordinator.apply_toolbar_visibility(
        show_refresh_button=True,
        show_root_buttons=True,
        show_root_dropdown=True,
        show_address_bar=True,
        show_navigation_buttons=True,
    )
    qtbot.waitUntil(
        lambda: panel.root_combo.isVisible() and panel.root_combo.width() > 0
    )
    assert panel.refresh_btn.isVisible() is True
    assert panel.root_buttons_host.isVisible() is True
    assert panel.address_edit.isVisible() is True
    assert panel.back_btn.isVisible() is True


def test_tab_close_buttons_visibility_can_be_toggled(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.add_tab(root)

    assert panel.tabs.tabsClosable() is True

    panel.presentation_coordinator.apply_tab_close_button_visibility(
        show_tab_close_buttons=False
    )
    assert panel.tabs.tabsClosable() is False

    panel.presentation_coordinator.apply_tab_close_button_visibility(
        show_tab_close_buttons=True
    )
    assert panel.tabs.tabsClosable() is True


def test_windows_mountpoint_uses_last_segment_and_tooltip(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    mount = root / "M" / "HDD01"
    mount.mkdir(parents=True)

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
    assert str(panel.root_combo.itemData(0, Qt.ToolTipRole)).endswith("HDD01")


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
    tab.navigation.set_path(a)
    tab.navigation.set_path(b)

    panel.address_edit.setFocus()
    QTest.keyClick(panel.address_edit, Qt.Key_Down, Qt.AltModifier)

    qtbot.waitUntil(lambda: panel._history_menu is not None)
    labels = [action.text() for action in panel._history_menu.actions()]
    assert any(str(b) in text for text in labels)
    assert any(str(a) in text for text in labels)
    assert any(str(root) in text for text in labels)


def test_root_picker_menu_uses_top_left_anchor_and_numbered_actions(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "root"
    source = root / "source"
    target = root / "target"
    archive = root / "archive"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    archive.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [source, target, archive],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(source)

    popup_point = panel.navigation_coordinator.root_picker_popup_point()
    assert popup_point == tab.mapToGlobal(tab.rect().topLeft())

    panel.navigation_coordinator.show_root_picker_menu()
    menu = panel.take_root_picker_menu()
    assert menu is not None

    actions = menu.actions()
    assert [action.text() for action in actions] == [
        "&1 archive",
        "&2 source",
        "&3 target",
    ]
    assert all(action.isCheckable() for action in actions)
    assert [action.isChecked() for action in actions] == [False, True, False]
    action_group = actions[0].actionGroup()
    assert action_group is not None
    assert action_group.isExclusive() is True
    assert all(action.actionGroup() is action_group for action in actions)


def test_overlapping_roots_mark_only_most_specific_match_active(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "workspace"
    mount = root / "M" / "HDD01"
    mount.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [root, mount],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)

    tab.navigation.set_path(mount)
    qtbot.waitUntil(lambda: tab.navigation.path == mount)
    qtbot.waitUntil(lambda: _button_for_root(panel, mount).isChecked() is True)

    assert _button_for_root(panel, root).isChecked() is False
    assert _button_for_root(panel, mount).isChecked() is True
    assert panel.root_combo.currentIndex() == _index_for_root(panel, mount)

    panel.navigation_coordinator.show_root_picker_menu()
    menu = panel.take_root_picker_menu()
    assert menu is not None

    assert _action_for_root(menu, root).isChecked() is False
    assert _action_for_root(menu, mount).isChecked() is True


def test_deepest_matching_root_wins_when_multiple_roots_overlap(
    qtbot, tmp_path: Path
) -> None:
    root = tmp_path / "workspace"
    mount = root / "M" / "HDD01"
    project = mount / "projects"
    current = project / "demo"
    current.mkdir(parents=True)

    panel = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        show_root_dropdown=True,
        roots_provider=lambda _current: [root, mount, project],
    )
    qtbot.addWidget(panel)
    panel.show()
    tab = panel.add_tab(root)

    tab.navigation.set_path(current)
    qtbot.waitUntil(lambda: tab.navigation.path == current)
    qtbot.waitUntil(lambda: _button_for_root(panel, project).isChecked() is True)

    assert _button_for_root(panel, root).isChecked() is False
    assert _button_for_root(panel, mount).isChecked() is False
    assert _button_for_root(panel, project).isChecked() is True
    assert panel.root_combo.currentIndex() == _index_for_root(panel, project)

    panel.navigation_coordinator.show_root_picker_menu()
    menu = panel.take_root_picker_menu()
    assert menu is not None

    assert _action_for_root(menu, root).isChecked() is False
    assert _action_for_root(menu, mount).isChecked() is False
    assert _action_for_root(menu, project).isChecked() is True


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

    tab.navigation.set_path(child)
    qtbot.waitUntil(lambda: tab.navigation.path == child)
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

    state = panel.state_coordinator.serialize_state()

    restored = PanelWidget(
        panel_id=1,
        default_path=root,
        show_hidden=True,
        roots_provider=lambda _current: [root],
    )
    qtbot.addWidget(restored)
    restored.show()
    restored.state_coordinator.restore_state(state)

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


def test_widget_identity_contract_for_panel_and_file_list(
    qtbot, tmp_path: Path
) -> None:
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
    assert panel.objectName() == object_name_for_id(widget_naming.panel_widget_id(1))
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

    panel.widget_map_coordinator.set_enabled(True)
    qtbot.waitUntil(panel.widget_map_coordinator.overlay_visible)

    aliases = [entry.alias for entry in panel.widget_map_coordinator.entries()]
    assert any(alias.endswith(".file_list") for alias in aliases)
    assert "P1.address" in aliases

    panel.widget_map_coordinator.set_enabled(False)
    assert panel.widget_map_coordinator.overlay_visible() is False


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


def test_root_buttons_host_can_shrink_under_narrow_width(qtbot, tmp_path: Path) -> None:
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
    qtbot.waitUntil(
        lambda: panel.root_combo.isVisible() and panel.root_combo.width() > 0
    )

    assert panel.root_buttons_host.isVisible() is True
    assert panel.root_buttons
