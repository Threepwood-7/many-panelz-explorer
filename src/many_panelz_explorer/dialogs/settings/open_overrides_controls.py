"""File-open override controls for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def build_file_open_overrides_controls(dialog: SettingsDialog) -> QWidget:
    """Build the per-extension open override controls host."""

    host = QWidget(dialog)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(dialog.file_open_overrides_table, 1)

    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    dialog.add_override_row_btn = QPushButton("Add", actions)
    dialog.remove_override_row_btn = QPushButton("Remove", actions)
    dialog.browse_override_editor_btn = QPushButton("Browse Editor...", actions)
    dialog.browse_override_viewer_btn = QPushButton("Browse Viewer...", actions)
    dialog.add_override_row_btn.clicked.connect(dialog.add_file_open_override_row)
    dialog.remove_override_row_btn.clicked.connect(dialog.remove_file_open_override_row)
    dialog.browse_override_editor_btn.clicked.connect(
        lambda: dialog.browse_file_open_override_executable(1)
    )
    dialog.browse_override_viewer_btn.clicked.connect(
        lambda: dialog.browse_file_open_override_executable(2)
    )
    actions_layout.addWidget(dialog.add_override_row_btn)
    actions_layout.addWidget(dialog.remove_override_row_btn)
    actions_layout.addWidget(dialog.browse_override_editor_btn)
    actions_layout.addWidget(dialog.browse_override_viewer_btn)
    actions_layout.addStretch(1)
    layout.addWidget(actions)
    return host
