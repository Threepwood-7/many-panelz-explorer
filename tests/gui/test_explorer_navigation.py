import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtTest import QTest

from many_panelz_explorer.explorer_tab import ExplorerTab


def _make_tree(root: Path) -> tuple[Path, Path, Path]:
    a = root / "a"
    b = a / "b"
    c = root / "c"
    b.mkdir(parents=True, exist_ok=True)
    c.mkdir(parents=True, exist_ok=True)
    return a, b, c


def test_alt_history_shortcuts_and_alt_up(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    a, b, _c = _make_tree(root)

    tab = ExplorerTab(initial_path=root)
    qtbot.addWidget(tab)
    tab.show()

    tab.set_path(a)
    tab.set_path(b)
    assert tab.current_path() == b

    tab.view.setFocus()
    QTest.keyClick(tab.view, Qt.Key_Left, Qt.AltModifier)
    assert tab.current_path() == a

    QTest.keyClick(tab.view, Qt.Key_Right, Qt.AltModifier)
    assert tab.current_path() == b

    QTest.keyClick(tab.view, Qt.Key_Up, Qt.AltModifier)
    assert tab.current_path() == a


def test_lynx_arrow_navigation_uses_left_right(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    _a, _b, c = _make_tree(root)

    tab = ExplorerTab(initial_path=root)
    qtbot.addWidget(tab)
    tab.show()

    tab.set_path(root)
    qtbot.waitUntil(lambda: tab.model.index(str(c)).isValid())

    index = tab.model.index(str(c))
    assert index.isValid()
    tab.view.setCurrentIndex(index)
    tab.view.setFocus()

    QTest.keyClick(tab.view, Qt.Key_Right)
    assert tab.current_path() == c

    QTest.keyClick(tab.view, Qt.Key_Left)
    assert tab.current_path() == root


def test_left_and_backspace_go_up_one_level(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    d1 = root / "d1"
    d2 = d1 / "d2"
    d3 = d2 / "d3"
    d3.mkdir(parents=True)

    tab = ExplorerTab(initial_path=root)
    qtbot.addWidget(tab)
    tab.show()
    tab.set_path(d3)
    assert tab.current_path() == d3

    tab.view.setFocus()
    QTest.keyClick(tab.view, Qt.Key_Left)
    assert tab.current_path() == d2

    QTest.keyClick(tab.view, Qt.Key_Backspace)
    assert tab.current_path() == d1


def test_back_and_up_restore_previous_selection(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    a = root / "a"
    child = a / "child"
    other = a / "other"
    child.mkdir(parents=True)
    other.mkdir(parents=True)

    tab = ExplorerTab(initial_path=a)
    qtbot.addWidget(tab)
    tab.show()

    qtbot.waitUntil(lambda: tab.model.index(str(child)).isValid())
    child_index = tab.model.index(str(child))
    flags = QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
    tab.view.selectionModel().setCurrentIndex(child_index, flags)
    tab.view.setFocus()

    QTest.keyClick(tab.view, Qt.Key_Right)
    assert tab.current_path() == child

    QTest.keyClick(tab.view, Qt.Key_Left)
    assert tab.current_path() == a
    assert Path(tab.model.filePath(tab.view.currentIndex())) == child

    other_index = tab.model.index(str(other))
    tab.view.selectionModel().setCurrentIndex(other_index, flags)
    QTest.keyClick(tab.view, Qt.Key_Right)
    assert tab.current_path() == other

    QTest.keyClick(tab.view, Qt.Key_Left, Qt.AltModifier)
    assert tab.current_path() == a
    assert Path(tab.model.filePath(tab.view.currentIndex())) == other


def test_file_columns_format_and_directories_first(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    directory = root / "z_dir"
    directory.mkdir()
    file_path = root / "a.txt"
    file_path.write_bytes(b"x" * 1_234_567)

    tab = ExplorerTab(initial_path=root)
    qtbot.addWidget(tab)
    tab.show()

    qtbot.waitUntil(lambda: tab.model.index(str(directory)).isValid())
    qtbot.waitUntil(lambda: tab.model.index(str(file_path)).isValid())

    dir_index = tab.model.index(str(directory))
    file_index = tab.model.index(str(file_path))

    assert tab.model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Name"
    assert tab.model.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "Ext"
    assert tab.model.headerData(2, Qt.Horizontal, Qt.DisplayRole) == "Size"
    assert tab.model.headerData(3, Qt.Horizontal, Qt.DisplayRole) == "Date"

    assert tab.model.data(dir_index, Qt.DisplayRole) == "[z_dir]"
    assert tab.model.data(file_index.siblingAtColumn(1), Qt.DisplayRole) == "txt"
    assert tab.model.data(file_index.siblingAtColumn(2), Qt.DisplayRole) == "1,234,567"

    date_text = str(tab.model.data(file_index.siblingAtColumn(3), Qt.DisplayRole))
    assert len(date_text) == 16
    assert date_text[4] == "-"
    assert date_text[7] == "-"
    assert date_text[10] == " "
    assert date_text[13] == ":"

    qtbot.waitUntil(lambda: tab.model.rowCount(tab.view.rootIndex()) >= 2)
    first_index = tab.model.index(0, 0, tab.view.rootIndex())
    assert first_index.isValid()
    first_path = Path(tab.model.filePath(first_index))
    assert first_path.is_dir()


def test_parent_entry_shown_except_at_drive_root(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)

    tab = ExplorerTab(initial_path=child)
    qtbot.addWidget(tab)
    tab.show()

    qtbot.waitUntil(lambda: tab.model.rowCount(tab.view.rootIndex()) > 0)
    first_name = str(tab.model.data(tab.model.index(0, 0, tab.view.rootIndex()), Qt.DisplayRole))
    assert first_name == ".."

    drive_root = Path(child.anchor)
    tab.set_path(drive_root)
    qtbot.waitUntil(lambda: tab.model.rowCount(tab.view.rootIndex()) >= 0)
    if tab.model.rowCount(tab.view.rootIndex()) > 0:
        first_root_name = str(
            tab.model.data(tab.model.index(0, 0, tab.view.rootIndex()), Qt.DisplayRole)
        )
        assert first_root_name != ".."
