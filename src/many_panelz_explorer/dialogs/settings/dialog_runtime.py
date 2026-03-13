"""Runtime behavior mixin for the settings dialog."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QLabel,
    QScrollArea,
    QTableWidgetItem,
    QTreeWidgetItem,
)

from . import (
    backend_state,
    open_overrides_state,
    preferences_flow,
    preferences_sync,
    tree_navigation,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QCheckBox, QSlider

    from ..._settings.models import UiPreferences
    from ...app_controller import AppController
    from ..settings_dialog import SettingsDialog


class SettingsDialogRuntimeMixin:
    """Provide runtime behaviors and helper seams for settings dialogs."""

    if TYPE_CHECKING:
        LIVE_PREVIEW_DEBOUNCE_MS: int
        controller: AppController
        teracopy_struct_close_checkbox: QCheckBox
        teracopy_struct_keep_open_checkbox: QCheckBox
        active_intensity_slider: QSlider
        target_intensity_slider: QSlider
        active_color_preview: QLabel
        target_color_preview: QLabel
        _active_color_hex: str
        _target_color_hex: str
        _committed_preferences: UiPreferences
        _working_preferences: UiPreferences
        _pending_live_preview: bool
        _pending_full_store_reset: bool
        _tree_sync_in_progress: bool
        _active_subsection_key: str
        _live_preview_timer: QTimer
        _no_matches_label: QLabel
        _scroll: QScrollArea
        _loading_ui: bool

    @property
    def _dialog(self) -> SettingsDialog:
        """Return ``self`` cast to the concrete dialog type for helpers."""

        return cast("SettingsDialog", self)

    def on_teracopy_struct_close_toggled(self, checked: bool) -> None:
        """Keep TeraCopy close/keep-open toggles mutually exclusive."""

        if checked and self.teracopy_struct_keep_open_checkbox.isChecked():
            with QSignalBlocker(self.teracopy_struct_keep_open_checkbox):
                self.teracopy_struct_keep_open_checkbox.setChecked(False)
        self._on_controls_changed()

    def on_teracopy_struct_keep_open_toggled(self, checked: bool) -> None:
        """Keep TeraCopy keep-open/close toggles mutually exclusive."""

        if checked and self.teracopy_struct_close_checkbox.isChecked():
            with QSignalBlocker(self.teracopy_struct_close_checkbox):
                self.teracopy_struct_close_checkbox.setChecked(False)
        self._on_controls_changed()

    def reset_robocopy_backend_defaults(self) -> None:
        """Reset Robocopy structured controls to their defaults."""

        backend_state.reset_robocopy_backend_defaults(self._dialog)

    def reset_teracopy_backend_defaults(self) -> None:
        """Reset TeraCopy structured controls to their defaults."""

        backend_state.reset_teracopy_backend_defaults(self._dialog)

    def reset_unstoppable_backend_defaults(self) -> None:
        """Reset Unstoppable Copier structured controls to their defaults."""

        backend_state.reset_unstoppable_backend_defaults(self._dialog)

    def reset_external_copymove_backend_defaults(self) -> None:
        """Reset external copy/move structured controls to their defaults."""

        backend_state.reset_external_copymove_backend_defaults(self._dialog)

    def update_backend_generated_previews(self) -> None:
        """Refresh generated preview labels for backend argument builders."""

        backend_state.update_backend_generated_previews(self._dialog)

    def add_file_open_override_row(self) -> None:
        """Append a new file-open override row."""

        open_overrides_state.add_file_open_override_row(self._dialog)

    def remove_file_open_override_row(self) -> None:
        """Remove the selected file-open override row."""

        open_overrides_state.remove_file_open_override_row(self._dialog)

    def browse_file_open_override_executable(self, column: int) -> None:
        """Browse for an editor/viewer executable in an override row."""

        open_overrides_state.browse_file_open_override_executable(self._dialog, column)

    def on_file_open_overrides_item_changed(self, item: QTableWidgetItem) -> None:
        """Normalize and validate edited override rows."""

        open_overrides_state.on_file_open_overrides_item_changed(self._dialog, item)

    @property
    def active_color_hex(self) -> str:
        """Return the active panel tint color."""

        return self._active_color_hex

    @property
    def target_color_hex(self) -> str:
        """Return the target panel tint color."""

        return self._target_color_hex

    @property
    def committed_preferences(self) -> UiPreferences:
        """Return the last applied preferences snapshot."""

        return self._committed_preferences

    @committed_preferences.setter
    def committed_preferences(self, preferences: UiPreferences) -> None:
        """Store the last applied preferences snapshot."""

        self._committed_preferences = preferences

    @property
    def working_preferences(self) -> UiPreferences:
        """Return the in-progress preferences snapshot."""

        return self._working_preferences

    @working_preferences.setter
    def working_preferences(self, preferences: UiPreferences) -> None:
        """Store the in-progress preferences snapshot."""

        self._working_preferences = preferences

    @property
    def pending_live_preview(self) -> bool:
        """Return whether a debounced preview update is pending."""

        return self._pending_live_preview

    @pending_live_preview.setter
    def pending_live_preview(self, value: bool) -> None:
        """Store whether a debounced preview update is pending."""

        self._pending_live_preview = value

    @property
    def pending_full_store_reset(self) -> bool:
        """Return whether a full settings-store reset is pending."""

        return self._pending_full_store_reset

    @pending_full_store_reset.setter
    def pending_full_store_reset(self, value: bool) -> None:
        """Store whether a full settings-store reset is pending."""

        self._pending_full_store_reset = value

    @property
    def tree_sync_in_progress(self) -> bool:
        """Return whether tree selection sync is in progress."""

        return self._tree_sync_in_progress

    @tree_sync_in_progress.setter
    def tree_sync_in_progress(self, value: bool) -> None:
        """Store whether tree selection sync is in progress."""

        self._tree_sync_in_progress = value

    @property
    def active_subsection_key(self) -> str:
        """Return the active subsection key."""

        return self._active_subsection_key

    @active_subsection_key.setter
    def active_subsection_key(self, key: str) -> None:
        """Store the active subsection key."""

        self._active_subsection_key = key

    @property
    def live_preview_timer(self) -> QTimer:
        """Return the timer that debounces live preview updates."""

        return self._live_preview_timer

    @property
    def no_matches_label(self) -> QLabel:
        """Return the label shown when search yields no matching rows."""

        return self._no_matches_label

    @property
    def scroll_area(self) -> QScrollArea:
        """Return the scroll area that hosts section content."""

        return self._scroll

    @property
    def home_directory(self) -> str:
        """Return the home directory used for browse dialogs."""

        return str(Path.home())

    def on_controls_changed(self) -> None:
        """Handle generic control changes from builder modules."""

        self._on_controls_changed()

    def apply_search_filter(self, text: str) -> None:
        """Apply a section-row search filter."""

        tree_navigation.apply_search_filter(self._dialog, text)

    def on_section_tree_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        """Handle section-tree selection changes."""

        tree_navigation.on_section_tree_changed(self._dialog, current, previous)

    def load_preferences_into_controls(self, preferences: UiPreferences) -> None:
        """Populate dialog controls from a preferences snapshot."""

        self._load_preferences_into_controls(preferences)

    def on_reset_current_section(self) -> None:
        """Reset the active section to defaults."""

        preferences_flow.on_reset_current_section(self._dialog)

    def on_reset_all_everything_stored(self) -> None:
        """Schedule a full reset of persisted settings and session data."""

        preferences_flow.on_reset_all_everything_stored(self._dialog)

    def update_reset_controls(self) -> None:
        """Refresh the reset-action UI for the active section."""

        preferences_flow.update_reset_controls(self._dialog)

    def new_font_family_combo(
        self,
        *,
        include_base_option: bool,
        base_label: str,
    ) -> QComboBox:
        """Build a font-family combo populated from system fonts."""

        combo = QComboBox(self._dialog)
        if include_base_option:
            combo.addItem(base_label, "")
        for family in QFontDatabase.families():
            combo.addItem(family, family)
        combo.currentIndexChanged.connect(self._on_controls_changed)
        return combo

    def new_byte_format_mode_combo(self) -> QComboBox:
        """Build the shared byte-format mode combo."""

        combo = QComboBox(self._dialog)
        combo.addItem("Human Readable", "human_readable")
        combo.addItem("Always MB", "always_mb")
        combo.addItem("Always MiB", "always_mib")
        combo.addItem("Bytes", "bytes")
        combo.addItem("Custom", "custom")
        combo.currentIndexChanged.connect(self._on_byte_format_mode_changed)
        return combo

    def _on_byte_format_mode_changed(self, _index: int) -> None:
        """Refresh dependent byte-format controls after mode changes."""

        preferences_sync.sync_byte_format_controls(self._dialog)
        self._on_controls_changed()

    def on_file_list_use_app_font_toggled(self, _checked: bool) -> None:
        """Refresh file-list font override controls after toggle changes."""

        preferences_sync.sync_font_override_controls(self._dialog)
        self._on_controls_changed()

    def on_navigation_use_app_font_toggled(self, _checked: bool) -> None:
        """Refresh navigation font override controls after toggle changes."""

        preferences_sync.sync_font_override_controls(self._dialog)
        self._on_controls_changed()

    def _load_panel_tint_preferences(self, preferences: UiPreferences) -> None:
        """Load active and target panel tint preferences into controls."""

        self.active_intensity_slider.setValue(
            preferences.active_panel_tint_intensity_percent
        )
        self.target_intensity_slider.setValue(
            preferences.target_panel_tint_intensity_percent
        )
        self._active_color_hex = preferences.active_panel_tint_color_hex
        self._target_color_hex = preferences.target_panel_tint_color_hex
        preferences_sync.sync_color_preview(
            self.active_color_preview,
            self._active_color_hex,
        )
        preferences_sync.sync_color_preview(
            self.target_color_preview,
            self._target_color_hex,
        )

    def _load_preferences_into_controls(self, preferences: UiPreferences) -> None:
        """Populate dialog controls from the current UI preferences."""

        self._loading_ui = True
        dialog = self._dialog
        try:
            self._working_preferences = replace(preferences)
            self._load_panel_tint_preferences(preferences)
            preferences_sync.load_panel_preferences(dialog, preferences)
            preferences_sync.load_operations_preferences(dialog, preferences)
            preferences_sync.load_typography_preferences(dialog, preferences)
            preferences_sync.sync_font_override_controls(dialog)
            preferences_sync.sync_byte_format_controls(dialog)
            self.update_backend_generated_previews()
            preferences_sync.sync_slider_value_labels(dialog)
            preferences_flow.update_reset_controls(dialog)
        finally:
            self._loading_ui = False

    def set_combo_value(self, combo: QComboBox, value: str) -> None:
        """Select the first combo row whose stored data matches the value."""

        for index in range(combo.count()):
            if str(combo.itemData(index)) == str(value):
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _on_controls_changed(self) -> None:
        """Rebuild working preferences after any control change."""

        if self._loading_ui:
            return
        dialog = self._dialog
        preferences_sync.sync_slider_value_labels(dialog)
        self._working_preferences = preferences_sync.collect_preferences_from_controls(
            dialog
        )
        self.update_backend_generated_previews()
        self._pending_live_preview = True
        self._live_preview_timer.start(self.LIVE_PREVIEW_DEBOUNCE_MS)

    def _flush_live_preview(self) -> None:
        """Apply the pending live preview to the controller."""

        if not self._pending_live_preview:
            return
        self._pending_live_preview = False
        self.controller.preview_ui_preferences(self._working_preferences)

    def choose_active_color(self) -> None:
        """Choose a new active panel tint color."""

        selected = QColorDialog.getColor(
            QColor(self._active_color_hex),
            self._dialog,
            "Active Tint Color",
        )
        if not selected.isValid():
            return
        self._active_color_hex = selected.name(QColor.NameFormat.HexRgb).upper()
        preferences_sync.sync_color_preview(
            self.active_color_preview,
            self._active_color_hex,
        )
        self._on_controls_changed()

    def choose_target_color(self) -> None:
        """Choose a new target panel tint color."""

        selected = QColorDialog.getColor(
            QColor(self._target_color_hex),
            self._dialog,
            "Target Tint Color",
        )
        if not selected.isValid():
            return
        self._target_color_hex = selected.name(QColor.NameFormat.HexRgb).upper()
        preferences_sync.sync_color_preview(
            self.target_color_preview,
            self._target_color_hex,
        )
        self._on_controls_changed()

    def _accept_with_apply(self) -> None:
        """Apply pending changes and accept the dialog."""

        self._apply_and_commit()
        self._dialog.accept()

    def _apply_and_commit(self) -> None:
        """Apply and persist the current preferences."""

        preferences_flow.apply_and_commit(self._dialog)

    def reject(self) -> None:
        """Restore committed preferences and reject the dialog."""

        preferences_flow.prepare_reject(self._dialog)
        QDialog.reject(self._dialog)
