"""Widget-map overlay coordination for a panel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget
from threep_commons.qt.widget_identity import assign_widget_identity

from ... import widget_naming

if TYPE_CHECKING:
    from ...explorer_tab import ExplorerTab
    from ...panel_widget import PanelWidget


@dataclass(frozen=True)
class PanelWidgetMapEntry:
    """Describe one widget-map overlay target."""

    widget: QWidget
    alias: str
    widget_id: str


class _PanelWidgetMapOverlay(QWidget):
    """Paint widget bounds and aliases over the owning panel."""

    def __init__(self, owner: PanelWidget) -> None:
        super().__init__(owner)
        self._owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()

    def refresh(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        self.raise_()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        _ = event
        entries = self._owner.widget_map_coordinator.entries()
        if not entries:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        text_flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        for entry in entries:
            widget = entry.widget
            if not widget.isVisible():
                continue
            top_left = widget.mapTo(self, QPoint(0, 0))
            rect = QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)
            if rect.width() <= 2 or rect.height() <= 2:
                continue

            color = QColor("#22c55e")
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            label = entry.alias
            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(label) + 12
            text_height = metrics.height() + 8

            label_x = rect.left() + 2
            label_y = rect.top() - text_height - 2
            if label_y < 2:
                label_y = rect.top() + 2
            if label_x + text_width > self.width() - 2:
                label_x = max(2, self.width() - text_width - 2)

            label_rect = QRect(label_x, label_y, text_width, text_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 190))
            painter.drawRoundedRect(label_rect, 4, 4)
            painter.setPen(QColor("#f8fafc"))
            painter.drawText(label_rect.adjusted(6, 0, -6, 0), int(text_flags), label)


class PanelWidgetMapCoordinator:
    """Own widget identity assignment and overlay refresh for a panel."""

    def __init__(self, panel: PanelWidget) -> None:
        self.panel = panel
        self._enabled = False
        self._overlay = _PanelWidgetMapOverlay(panel)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.sync_overlay()

    def enabled(self) -> bool:
        return self._enabled

    def overlay_visible(self) -> bool:
        """Return whether the overlay widget is currently visible."""

        return self._overlay.isVisible()

    def entries(self) -> list[PanelWidgetMapEntry]:
        widgets: list[QWidget] = [
            self.panel.tabs,
            self.panel.tabs.tabBar(),
            self.panel.group_picker_combo,
            self.panel.new_group_btn,
            self.panel.root_combo,
            self.panel.address_edit,
            self.panel.refresh_btn,
            self.panel.back_btn,
            self.panel.forward_btn,
            self.panel.up_btn,
            self.panel.root_btn,
            self.panel.filter_edit,
        ]
        tab = self.panel.current_tab()
        if tab is not None:
            widgets.extend([tab, tab.view])

        entries: list[PanelWidgetMapEntry] = []
        for widget in widgets:
            entry = self._entry_for_widget(widget)
            if entry is not None:
                entries.append(entry)
        return entries

    def assign_tab_identity(self, tab: ExplorerTab) -> None:
        tab_id = widget_naming.tab_widget_id(self.panel.panel_id, tab.tab_uuid)
        tab_alias = widget_naming.tab_alias(self.panel.panel_id, tab.tab_uuid)
        assign_widget_identity(tab, widget_id=tab_id, widget_alias=tab_alias)
        assign_widget_identity(
            tab.view,
            widget_id=widget_naming.file_list_widget_id(
                self.panel.panel_id, tab.tab_uuid
            ),
            widget_alias=widget_naming.file_list_alias(
                self.panel.panel_id, tab.tab_uuid
            ),
        )

    def sync_overlay(self) -> None:
        if not self._enabled:
            self._overlay.hide()
            return
        self._overlay.show()
        self._overlay.refresh()

    def _entry_for_widget(self, widget: QWidget) -> PanelWidgetMapEntry | None:
        widget_id = str(widget.property("widget_id") or "").strip()
        alias = str(widget.property("widget_alias") or "").strip()
        if not widget_id or not alias:
            return None
        return PanelWidgetMapEntry(widget=widget, alias=alias, widget_id=widget_id)
