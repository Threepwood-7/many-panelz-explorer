from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from threep_commons.qt.widget_identity import assign_widget_identity

from ... import mounts, widget_naming
from ...storage_status_formatting import (
    DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE,
    StorageStatusRenderResult,
    format_storage_usage_entry,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtGui import QResizeEvent

    from ...window import ExplorerWindow


class _ElidedStatusLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_full_text(self, value: str) -> None:
        self._full_text = str(value or "")
        self.setToolTip(self._full_text if self._full_text else "")
        self._apply_elided_text()

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_elided_text()

    def _apply_elided_text(self) -> None:
        if not self._full_text:
            super().setText("")
            return
        width = max(0, self.contentsRect().width())
        elided = self.fontMetrics().elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            width,
        )
        super().setText(elided)


class WindowStatusCoordinator:
    def __init__(self, window: ExplorerWindow) -> None:
        self.window = window
        self._storage_bytes_formatter = lambda value: f"{int(value):,}"
        self._storage_label_template = DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE
        self._storage_refresh_timer = QTimer(window)
        self._storage_refresh_timer.setInterval(
            int(mounts.WINDOWS_ROOTS_CACHE_TTL_SECONDS * 1000)
        )
        self._storage_refresh_timer.timeout.connect(
            self.refresh_storage_overview_status
        )
        self._build_status_rows()

    def _build_status_rows(self) -> None:
        status_bar = self.window.statusBar()

        host = QWidget(self.window)
        rows_layout = QVBoxLayout(host)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(1)

        paths_row = QWidget(host)
        paths_row_layout = QHBoxLayout(paths_row)
        paths_row_layout.setContentsMargins(0, 0, 0, 0)
        paths_row_layout.setSpacing(8)

        self.window._source_path_label = QLabel("Source path: (none)", host)
        self.window._target_path_label = QLabel("Target path: (none)", host)
        self.window._source_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.window._target_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        paths_row_layout.addWidget(self.window._source_path_label, 1)
        paths_row_layout.addWidget(self.window._target_path_label, 1)

        storage_row = QWidget(host)
        storage_row_layout = QHBoxLayout(storage_row)
        storage_row_layout.setContentsMargins(0, 0, 0, 0)
        storage_row_layout.setSpacing(6)
        storage_label_prefix = QLabel("Storage:", storage_row)
        storage_label_prefix.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        storage_entries_host = QWidget(storage_row)
        storage_entries_layout = QHBoxLayout(storage_entries_host)
        storage_entries_layout.setContentsMargins(0, 0, 0, 0)
        storage_entries_layout.setSpacing(6)
        self.window._storage_overview_labels: list[_ElidedStatusLabel] = []
        storage_row_layout.addWidget(storage_label_prefix)
        storage_row_layout.addWidget(storage_entries_host, 1)

        rows_layout.addWidget(paths_row)
        rows_layout.addWidget(storage_row)
        status_bar.addPermanentWidget(host, 1)
        status_bar.showMessage("")

        self.window._status_rows_host = host
        self.window._status_paths_row = paths_row
        self.window._storage_overview_row = storage_row
        self.window._storage_entries_host = storage_entries_host
        self.window._storage_entries_layout = storage_entries_layout

        window_widget_id = widget_naming.window_widget_id(self.window.window_id)
        self._set_identity(host, f"{window_widget_id}:status_rows", "status.rows")
        self._set_identity(
            self.window._source_path_label,
            f"{window_widget_id}:status_source_path",
            "status.source_path",
        )
        self._set_identity(
            self.window._target_path_label,
            f"{window_widget_id}:status_target_path",
            "status.target_path",
        )
        self._set_identity(
            storage_entries_host,
            f"{window_widget_id}:status_storage_entries",
            "status.storage_entries",
        )

    def _set_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        assign_widget_identity(widget, widget_id=widget_id, widget_alias=alias)

    def update_pane_visuals(self) -> None:
        source_id = self.window._active_panel_id
        target_id = (
            self.window._resolve_target_panel_id(source_id)
            if source_id is not None
            else None
        )

        for panel_id, panel in self.window.panel_widgets.items():
            panel.set_role_visual_state(
                is_active=panel_id == source_id,
                is_target=panel_id == target_id,
            )
        self.set_persistent_path_status(source_id=source_id, target_id=target_id)
        self.refresh_storage_overview_status()

    def set_storage_overview_enabled(self, enabled: bool) -> None:
        if not enabled:
            self._storage_refresh_timer.stop()
            self.window._storage_overview_row.setVisible(False)
            self._set_storage_overview_entries([])
            return
        if not self._storage_refresh_timer.isActive():
            self._storage_refresh_timer.start()
        self.refresh_storage_overview_status()

    def set_storage_bytes_formatter(
        self,
        formatter: Callable[[int], str] | None,
    ) -> None:
        if formatter is None:
            self._storage_bytes_formatter = lambda value: f"{int(value):,}"
        else:
            self._storage_bytes_formatter = formatter
        self.refresh_storage_overview_status()

    def set_storage_label_template(self, template: str) -> None:
        self._storage_label_template = (
            str(template or "").strip() or DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE
        )
        self.refresh_storage_overview_status()

    def set_persistent_path_status(
        self, *, source_id: int | None, target_id: int | None
    ) -> None:
        source_path = self.panel_path_text(source_id)
        target_path = self.panel_path_text(target_id)

        self.window._source_path_label.setText(f"Source path: {source_path}")
        self.window._target_path_label.setText(f"Target path: {target_path}")

        self.window._source_path_label.setToolTip(
            "" if source_path == "(none)" else source_path
        )
        self.window._target_path_label.setToolTip(
            "" if target_path == "(none)" else target_path
        )

    def refresh_storage_overview_status(self) -> None:
        if not self.window._show_storage_overview_status_row:
            self.window._storage_overview_row.setVisible(False)
            self._set_storage_overview_entries([])
            return

        active_panel = self.window.active_panel()
        current_path = active_panel.current_path() if active_panel is not None else None
        entries = mounts.list_storage_usage_entries(current_path=current_path)
        if not entries:
            self.window._storage_overview_row.setVisible(False)
            self._set_storage_overview_entries([])
            return

        self._set_storage_overview_entries(
            [self._format_storage_entry(entry) for entry in entries]
        )
        self.window._storage_overview_row.setVisible(True)

    def _format_storage_entry(
        self, entry: mounts.StorageUsageEntry
    ) -> StorageStatusRenderResult:
        return format_storage_usage_entry(
            entry,
            bytes_formatter=self._format_size_value,
            label_template=self._storage_label_template,
        )

    def _format_size_value(self, value: int) -> str:
        try:
            return str(self._storage_bytes_formatter(int(value)))
        except Exception:  # pragma: no cover - defensive
            return f"{int(value):,}"

    def _set_storage_overview_entries(
        self, entries: list[StorageStatusRenderResult]
    ) -> None:
        self._ensure_storage_overview_labels(len(entries))
        for index, label in enumerate(self.window._storage_overview_labels):
            if index < len(entries):
                entry = entries[index]
                label.set_full_text(entry.label_text)
                label.setToolTip(entry.tooltip_html)
                label.setVisible(True)
            else:
                label.set_full_text("")
                label.setVisible(False)

    def _ensure_storage_overview_labels(self, count: int) -> None:
        layout = self.window._storage_entries_layout
        labels = self.window._storage_overview_labels
        window_widget_id = widget_naming.window_widget_id(self.window.window_id)
        while len(labels) < count:
            index = len(labels)
            label = _ElidedStatusLabel(self.window._storage_entries_host)
            layout.addWidget(label, 1)
            labels.append(label)
            self._set_identity(
                label,
                f"{window_widget_id}:status_storage_entry:{index}",
                f"status.storage_entry.{index}",
            )
        while len(labels) > count:
            label = labels.pop()
            layout.removeWidget(label)
            label.deleteLater()

    def panel_path_text(self, panel_id: int | None) -> str:
        if panel_id is None:
            return "(none)"
        panel = self.window.panel_widgets.get(panel_id)
        if panel is None:
            return "(none)"
        return str(panel.current_path())
