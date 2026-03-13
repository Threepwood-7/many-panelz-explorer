"""State helpers for file-open overrides in the settings dialog."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QTableWidgetItem

from ..._settings import normalize as settings_normalize

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def is_valid_extension(text: str) -> bool:
    """Return whether a file extension value has the expected shape."""

    value = str(text or "").strip()
    if not value:
        return False
    if not value.startswith("."):
        return False
    return len(value) > 1 and " " not in value


def normalize_extension(text: str) -> str:
    """Normalize a file extension value for storage in the table."""

    value = str(text or "").strip().lower()
    if not value:
        return ""
    if not value.startswith("."):
        value = f".{value}"
    return value


def add_file_open_override_row(dialog: SettingsDialog) -> None:
    """Append a new override row and focus it."""

    row = dialog.file_open_overrides_table.rowCount()
    dialog.file_open_overrides_table.insertRow(row)
    dialog.file_open_overrides_table.setItem(row, 0, QTableWidgetItem(".ext"))
    dialog.file_open_overrides_table.setItem(row, 1, QTableWidgetItem(""))
    dialog.file_open_overrides_table.setItem(row, 2, QTableWidgetItem(""))
    dialog.file_open_overrides_table.selectRow(row)
    dialog.on_controls_changed()


def remove_file_open_override_row(dialog: SettingsDialog) -> None:
    """Remove the currently selected override row."""

    current = dialog.file_open_overrides_table.currentRow()
    if current < 0:
        return
    dialog.file_open_overrides_table.removeRow(current)
    dialog.on_controls_changed()


def browse_file_open_override_executable(
    dialog: SettingsDialog,
    column: int,
) -> None:
    """Browse for an editor/viewer executable for the selected override row."""

    current = dialog.file_open_overrides_table.currentRow()
    if current < 0:
        return
    selected, _ = QFileDialog.getOpenFileName(
        dialog,
        "Select Executable",
        dialog.home_directory,
        "Executable Files (*.exe *.cmd *.bat);;All Files (*.*)",
    )
    if not selected:
        return
    item = dialog.file_open_overrides_table.item(current, column)
    if item is None:
        item = QTableWidgetItem("")
        dialog.file_open_overrides_table.setItem(current, column, item)
    item.setText(settings_normalize.normalize_windows_path_text(selected, fallback=""))
    dialog.on_controls_changed()


def on_file_open_overrides_item_changed(
    dialog: SettingsDialog,
    item: QTableWidgetItem,
) -> None:
    """Normalize extension edits and flag invalid override rows."""

    if item.column() == 0:
        ext = normalize_extension(item.text())
        if item.text() != ext:
            item.setText(ext)
            return
        if is_valid_extension(ext):
            item.setBackground(Qt.GlobalColor.transparent)
            item.setToolTip("")
        else:
            item.setBackground(Qt.GlobalColor.red)
            item.setToolTip("Extension must look like .txt")
    dialog.on_controls_changed()


def serialize_file_open_overrides(dialog: SettingsDialog) -> str:
    """Serialize file-open override rows to JSON."""

    payload: dict[str, dict[str, str]] = {}
    for row in range(dialog.file_open_overrides_table.rowCount()):
        ext_item = dialog.file_open_overrides_table.item(row, 0)
        editor_item = dialog.file_open_overrides_table.item(row, 1)
        viewer_item = dialog.file_open_overrides_table.item(row, 2)
        ext = normalize_extension(ext_item.text() if ext_item else "")
        if not is_valid_extension(ext):
            continue
        payload[ext] = {
            "editor": (editor_item.text() if editor_item else "").strip(),
            "viewer": (viewer_item.text() if viewer_item else "").strip(),
        }
    return json.dumps(payload, sort_keys=True)


def load_file_open_overrides(dialog: SettingsDialog, json_text: str) -> None:
    """Populate the override table from persisted JSON text."""

    dialog.file_open_overrides_table.blockSignals(True)
    try:
        dialog.file_open_overrides_table.setRowCount(0)
        try:
            raw = json.loads(str(json_text or "{}"))
        except json.JSONDecodeError:
            raw = {}
        raw_mapping = string_object_mapping(cast("object", raw))
        for ext in sorted(raw_mapping.keys(), key=str.casefold):
            value_mapping = string_object_mapping(raw_mapping.get(ext, {}))
            row = dialog.file_open_overrides_table.rowCount()
            dialog.file_open_overrides_table.insertRow(row)
            ext_item = QTableWidgetItem(normalize_extension(ext))
            editor_item = QTableWidgetItem(str(value_mapping.get("editor", "")))
            viewer_item = QTableWidgetItem(str(value_mapping.get("viewer", "")))
            dialog.file_open_overrides_table.setItem(row, 0, ext_item)
            dialog.file_open_overrides_table.setItem(row, 1, editor_item)
            dialog.file_open_overrides_table.setItem(row, 2, viewer_item)
            if is_valid_extension(ext_item.text()):
                ext_item.setBackground(Qt.GlobalColor.transparent)
                ext_item.setToolTip("")
            else:
                ext_item.setBackground(Qt.GlobalColor.red)
                ext_item.setToolTip("Extension must look like .txt")
    finally:
        dialog.file_open_overrides_table.blockSignals(False)


def string_object_mapping(value: object) -> dict[str, object]:
    """Normalize a JSON-like mapping to string keys."""

    if not isinstance(value, dict):
        return {}
    normalized: dict[str, object] = {}
    mapping = cast("dict[object, object]", value)
    for key, item in mapping.items():
        normalized[str(key)] = item
    return normalized
