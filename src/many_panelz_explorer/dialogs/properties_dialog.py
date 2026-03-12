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
    from collections.abc import Callable
    from pathlib import Path


def _default_size_formatter(value: int) -> str:
    return f"{int(value):,}"


class PropertiesDialog(QDialog):
    def __init__(
        self,
        path: Path,
        parent: QWidget | None = None,
        *,
        size_formatter: Callable[[int], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Properties")
        data = compute_properties(path)
        formatter: Callable[[int], str]
        if size_formatter is not None:
            formatter = size_formatter
        else:
            formatter = _default_size_formatter
        try:
            size_value = int(data["size_bytes"])
        except (KeyError, TypeError, ValueError):
            size_value = 0
        try:
            size_text = str(formatter(size_value))
        except Exception:  # pragma: no cover - defensive
            size_text = str(size_value)

        root = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Path", QLabel(data["path"]))
        form.addRow("Type", QLabel(data["type"]))
        form.addRow("Size", QLabel(size_text))
        form.addRow("Files", QLabel(data["file_count"]))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        root.addLayout(form)
        root.addWidget(buttons)
