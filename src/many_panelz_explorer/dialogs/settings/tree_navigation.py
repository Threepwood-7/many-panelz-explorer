"""Section-tree navigation helpers for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTreeWidgetItem

    from ..settings_dialog import SettingsDialog


def apply_search_filter(dialog: SettingsDialog, text: str) -> None:
    """Filter visible settings rows and keep tree selection valid."""

    query = str(text or "").strip().casefold()
    visible_rows = 0
    for section_key, section in dialog.sections.items():
        section_visible_subsections = 0
        for subsection_key in section.subsection_keys:
            subsection = dialog.subsections.get(subsection_key)
            if subsection is None:
                continue
            subsection_visible_rows = 0
            for row in subsection.rows:
                row_visible = (not query) or (query in row.terms)
                row.widget.setVisible(row_visible)
                if row_visible:
                    subsection_visible_rows += 1
            subsection.visible_row_count = subsection_visible_rows
            subsection_visible = subsection_visible_rows > 0
            subsection_item = dialog.subsection_tree_items.get(subsection_key)
            if subsection_item is not None:
                subsection_item.setHidden(not subsection_visible)
            if subsection_visible:
                section_visible_subsections += 1
            visible_rows += subsection_visible_rows
        section_visible = section_visible_subsections > 0
        section_item = dialog.section_tree_items.get(section_key)
        if section_item is not None:
            section_item.setHidden(not section_visible)
    dialog.no_matches_label.setVisible(bool(query) and visible_rows == 0)
    ensure_visible_tree_selection(dialog, persist=False)
    sync_active_subsection_visibility(dialog)
    dialog.update_reset_controls()


def restore_last_tree_selection(dialog: SettingsDialog) -> None:
    """Restore the last remembered tree selection when possible."""

    saved_subsection = str(
        dialog.controller.settings.settings_dialog_last_subsection or ""
    )
    saved_section = str(dialog.controller.settings.settings_dialog_last_section or "")
    if saved_subsection:
        item = dialog.subsection_tree_items.get(saved_subsection)
        if item is not None and not item.isHidden():
            set_current_tree_item(dialog, item, persist=False)
            return
    if saved_section and select_first_visible_subsection_for_section(
        dialog,
        saved_section,
        persist=False,
    ):
        return
    ensure_visible_tree_selection(dialog, persist=False)


def ensure_visible_tree_selection(dialog: SettingsDialog, *, persist: bool) -> None:
    """Ensure the tree has an active visible subsection selected."""

    current = cast(
        "QTreeWidgetItem | None",
        dialog.section_tree.currentItem(),
    )
    if current is not None and activate_tree_item(dialog, current, persist=persist):
        return
    item = first_visible_subsection_item(dialog)
    if item is not None:
        set_current_tree_item(dialog, item, persist=persist)


def on_section_tree_changed(
    dialog: SettingsDialog,
    current: QTreeWidgetItem | None,
    _previous: QTreeWidgetItem | None,
) -> None:
    """React to tree selection changes from the UI."""

    if dialog.tree_sync_in_progress or current is None:
        return
    activate_tree_item(dialog, current, persist=True)


def tree_item_payload(item: QTreeWidgetItem) -> tuple[str, str] | None:
    """Read the typed payload stored on a section-tree item."""

    payload = item.data(0, Qt.ItemDataRole.UserRole)
    if not isinstance(payload, (list, tuple)):
        return None
    payload_parts = tuple(cast("tuple[object, ...]", payload))
    if len(payload_parts) != 2:
        return None
    kind = str(payload_parts[0]).strip().lower()
    key = str(payload_parts[1] or "").strip()
    if kind not in {"section", "subsection"} or not key:
        return None
    return kind, key


def activate_tree_item(
    dialog: SettingsDialog,
    item: QTreeWidgetItem,
    *,
    persist: bool,
) -> bool:
    """Activate the target tree item if it is visible and valid."""

    if item.isHidden():
        return False
    payload = tree_item_payload(item)
    if payload is None:
        return False
    kind, key = payload
    if kind == "section":
        return select_first_visible_subsection_for_section(
            dialog,
            key,
            persist=persist,
        )
    return activate_subsection(dialog, key, persist=persist)


def set_current_tree_item(
    dialog: SettingsDialog,
    item: QTreeWidgetItem,
    *,
    persist: bool,
) -> bool:
    """Select a tree item and activate its subsection payload."""

    if item.isHidden():
        return False
    current = cast(
        "QTreeWidgetItem | None",
        dialog.section_tree.currentItem(),
    )
    if current is not item:
        dialog.tree_sync_in_progress = True
        try:
            dialog.section_tree.setCurrentItem(item)
        finally:
            dialog.tree_sync_in_progress = False
    return activate_tree_item(dialog, item, persist=persist)


def first_visible_subsection_item(dialog: SettingsDialog) -> QTreeWidgetItem | None:
    """Return the first visible subsection item in tree order."""

    for section_key in dialog.sections:
        section_item = dialog.section_tree_items.get(section_key)
        if section_item is None or section_item.isHidden():
            continue
        for index in range(section_item.childCount()):
            child = section_item.child(index)
            if not child.isHidden():
                return child
    return None


def select_first_visible_subsection_for_section(
    dialog: SettingsDialog,
    section_key: str,
    *,
    persist: bool,
) -> bool:
    """Select the first visible subsection beneath a section tree item."""

    section_item = dialog.section_tree_items.get(section_key)
    if section_item is None or section_item.isHidden():
        return False
    for index in range(section_item.childCount()):
        child = section_item.child(index)
        if child.isHidden():
            continue
        return set_current_tree_item(dialog, child, persist=persist)
    return False


def activate_subsection(
    dialog: SettingsDialog,
    subsection_key: str,
    *,
    persist: bool,
) -> bool:
    """Activate a subsection group and optionally persist the selection."""

    subsection = dialog.subsections.get(subsection_key)
    if subsection is None or subsection.visible_row_count <= 0:
        return False
    dialog.active_subsection_key = subsection_key
    sync_active_subsection_visibility(dialog)
    dialog.update_reset_controls()
    if persist:
        dialog.controller.settings.settings_dialog_last_section = subsection.section_key
        dialog.controller.settings.settings_dialog_last_subsection = subsection.key
    return True


def sync_active_subsection_visibility(dialog: SettingsDialog) -> None:
    """Show only the active subsection content group."""

    active_key = str(dialog.active_subsection_key or "")
    for key, subsection in dialog.subsections.items():
        subsection.group.setVisible(
            key == active_key and subsection.visible_row_count > 0
        )
    if active_key:
        dialog.scroll_area.verticalScrollBar().setValue(0)


def selected_subsection_key(dialog: SettingsDialog) -> str:
    """Return the currently selected subsection key, if any."""

    current = cast(
        "QTreeWidgetItem | None",
        dialog.section_tree.currentItem(),
    )
    if current is None:
        return ""
    payload = tree_item_payload(current)
    if payload is None:
        return ""
    kind, key = payload
    if kind != "subsection":
        return ""
    return key
