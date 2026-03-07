import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

import many_panelz_explorer.panel_widget as panel_widget_module
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

    first_tab.view.setColumnWidth(0, 420)
    qtbot.waitUntil(lambda: second_tab.view.columnWidth(0) == 420)

    second_tab.view.setColumnWidth(2, 260)
    qtbot.waitUntil(lambda: first_tab.view.columnWidth(2) == 260)


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
