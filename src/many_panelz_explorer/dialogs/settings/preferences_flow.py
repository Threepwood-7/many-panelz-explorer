"""Apply/reset flow helpers for the settings dialog."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from ..._settings.models import UiPreferences
from . import tree_navigation

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def active_section_key(dialog: SettingsDialog) -> str:
    """Return the section key for the active subsection selection."""

    subsection_key = tree_navigation.selected_subsection_key(dialog)
    subsection = dialog.subsections.get(subsection_key)
    if subsection is None:
        return ""
    return subsection.section_key


def resettable_fields_for_section(
    dialog: SettingsDialog,
    section_key: str,
) -> tuple[str, ...]:
    """Return the settings fields that belong to a resettable section."""

    return dialog.RESETTABLE_FIELDS_BY_SECTION.get(section_key, ())


def apply_defaults_for_section(dialog: SettingsDialog, section_key: str) -> None:
    """Apply default values for one logical settings section."""

    field_names = resettable_fields_for_section(dialog, section_key)
    if not field_names:
        return
    defaults = UiPreferences()
    updates = {field_name: getattr(defaults, field_name) for field_name in field_names}
    updated_preferences = replace(dialog.working_preferences, **updates)
    dialog.load_preferences_into_controls(updated_preferences)
    dialog.on_controls_changed()
    update_reset_controls(dialog)


def on_reset_current_section(dialog: SettingsDialog) -> None:
    """Reset only the currently selected section to defaults."""

    section_key = active_section_key(dialog)
    if not section_key:
        return
    if not resettable_fields_for_section(dialog, section_key):
        return
    dialog.pending_full_store_reset = False
    apply_defaults_for_section(dialog, section_key)


def on_reset_all_everything_stored(dialog: SettingsDialog) -> None:
    """Schedule a full settings-store reset after user confirmation."""

    decision = QMessageBox.warning(
        dialog,
        "Reset Everything Stored",
        (
            "Schedule full reset of all stored settings and session data?\n\n"
            "Apply/OK will clear the entire settings store, then persist current "
            "defaults. Cancel keeps existing persisted settings unchanged."
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if decision != QMessageBox.StandardButton.Yes:
        return
    dialog.pending_full_store_reset = True
    dialog.load_preferences_into_controls(UiPreferences())
    dialog.on_controls_changed()
    update_reset_controls(dialog)


def update_reset_controls(dialog: SettingsDialog) -> None:
    """Refresh the reset affordances for the active section."""

    section_key = active_section_key(dialog)
    section_entry = dialog.sections.get(section_key)
    section_text = section_entry.title if section_entry is not None else "(none)"
    dialog.reset_section_context_label.setText(f"Current Section: {section_text}")
    section_fields = resettable_fields_for_section(dialog, section_key)
    dialog.reset_section_button.setEnabled(bool(section_fields))
    dialog.reset_pending_label.setVisible(dialog.pending_full_store_reset)
    if dialog.pending_full_store_reset:
        dialog.reset_pending_label.setText(
            "Full reset is scheduled. Apply/OK will clear all stored "
            "settings and session data."
        )
        return
    dialog.reset_pending_label.setText("")


def apply_and_commit(dialog: SettingsDialog) -> None:
    """Commit the current working preferences and clear pending preview state."""

    dialog.on_controls_changed()
    dialog.live_preview_timer.stop()
    dialog.pending_live_preview = False
    if dialog.pending_full_store_reset:
        dialog.controller.settings.clear_all()
    dialog.controller.apply_ui_preferences(dialog.working_preferences)
    dialog.committed_preferences = replace(dialog.working_preferences)
    dialog.pending_full_store_reset = False
    update_reset_controls(dialog)


def prepare_reject(dialog: SettingsDialog) -> None:
    """Restore committed preferences before the dialog is closed."""

    dialog.live_preview_timer.stop()
    dialog.pending_live_preview = False
    dialog.pending_full_store_reset = False
    dialog.controller.preview_ui_preferences(dialog.committed_preferences)
    update_reset_controls(dialog)
