"""Models and small widgets for settings-section construction."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QGroupBox, QSpinBox, QWidget


@dataclass
class RowEntry:
    """Describe one searchable settings row."""

    key: str
    widget: QWidget
    terms: str


@dataclass
class SectionEntry:
    """Describe one top-level settings section."""

    key: str
    title: str
    terms: str
    subsection_keys: list[str]


@dataclass
class SubsectionEntry:
    """Describe one subsection group and its rows."""

    key: str
    section_key: str
    title: str
    group: QGroupBox
    terms: str
    rows: list[RowEntry]
    visible_row_count: int = 0


class FontSizeSpinBox(QSpinBox):
    """Spin box that optionally exposes a zero-valued system default."""

    def __init__(
        self,
        *,
        allow_system_value: bool,
        min_size: int = 6,
        max_size: int = 32,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the constrained font-size control."""

        super().__init__(parent)
        self._allow_system_value = bool(allow_system_value)
        self._min_size = int(min_size)
        self._max_size = int(max_size)
        self.setRange(0 if self._allow_system_value else self._min_size, self._max_size)
        self.valueChanged.connect(self._normalize_value)

    def _normalize_value(self, value: int) -> None:
        """Clamp manual edits back into the supported range."""

        normalized = self._normalized(value)
        if normalized == value:
            return
        with QSignalBlocker(self):
            self.setValue(normalized)

    def _normalized(self, value: int) -> int:
        """Return the normalized value for the current mode."""

        size = int(value)
        if self._allow_system_value and size <= 0:
            return 0
        if size < self._min_size:
            return self._min_size
        if size > self._max_size:
            return self._max_size
        return size

    def stepBy(self, steps: int) -> None:
        """Preserve the zero-valued system option when stepping."""

        if not self._allow_system_value:
            super().stepBy(steps)
            return

        current = self.value()
        if current in {1, 2, 3, 4, 5}:
            with QSignalBlocker(self):
                self.setValue(self._min_size if steps >= 0 else 0)
            return
        if current == 0 and steps > 0:
            with QSignalBlocker(self):
                self.setValue(self._min_size)
            if steps > 1:
                super().stepBy(steps - 1)
            return
        if current == self._min_size and steps < 0:
            with QSignalBlocker(self):
                self.setValue(0)
            if steps < -1:
                super().stepBy(steps + 1)
            return
        super().stepBy(steps)
