from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..file_ops import compute_properties

if TYPE_CHECKING:
    from pathlib import Path


class PropertiesDialog(QDialog):
    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Properties")
        data = compute_properties(path)

        root = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Path", QLabel(data["path"]))
        form.addRow("Type", QLabel(data["type"]))
        form.addRow("Size (bytes)", QLabel(data["size_bytes"]))
        form.addRow("Files", QLabel(data["file_count"]))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        root.addLayout(form)
        root.addWidget(buttons)
