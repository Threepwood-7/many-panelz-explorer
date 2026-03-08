from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, QTimer, Qt
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import widget_naming
from ..constants import APP_DISPLAY_NAME, APP_VERSION
from ..settings import SettingsManager, UiPreferences

if TYPE_CHECKING:
    from ..app_controller import AppController


def _mode_label(mode: str) -> str:
    if mode == "home":
        return "Home"
    if mode == "cwd":
        return "Current Working Directory"
    return "Clone Active Path"


@dataclass
class _RowEntry:
    key: str
    widget: QWidget
    terms: str


@dataclass
class _SectionEntry:
    key: str
    group: QGroupBox
    terms: str
    rows: list[_RowEntry]


class _FontSizeSpinBox(QSpinBox):
    def __init__(
        self,
        *,
        allow_system_value: bool,
        min_size: int = 6,
        max_size: int = 32,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._allow_system_value = bool(allow_system_value)
        self._min_size = int(min_size)
        self._max_size = int(max_size)
        self.setRange(0 if self._allow_system_value else self._min_size, self._max_size)
        self.valueChanged.connect(self._normalize_value)

    def _normalize_value(self, value: int) -> None:
        normalized = self._normalized(value)
        if normalized == value:
            return
        with QSignalBlocker(self):
            self.setValue(normalized)

    def _normalized(self, value: int) -> int:
        size = int(value)
        if self._allow_system_value and size <= 0:
            return 0
        if size < self._min_size:
            return self._min_size
        if size > self._max_size:
            return self._max_size
        return size

    def stepBy(self, steps: int) -> None:  # noqa: N802
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


class SettingsDialog(QDialog):
    LIVE_PREVIEW_DEBOUNCE_MS = 140

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._committed_preferences = controller.current_ui_preferences()
        self._working_preferences = replace(self._committed_preferences)
        self._loading_ui = False
        self._pending_live_preview = False
        self._rows_by_key: dict[str, QWidget] = {}
        self._sections: dict[str, _SectionEntry] = {}

        self.setWindowTitle("Settings")
        self.resize(860, 680)
        self.setModal(True)
        self._assign_identity(self, "settings_dialog", "settings.dialog")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search settings...")
        self.search_edit.setClearButtonEnabled(True)
        self._assign_identity(self.search_edit, "settings_dialog:search", "settings.search")
        self.search_edit.textChanged.connect(self._apply_search_filter)
        root.addWidget(self.search_edit)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll_host = QWidget(self._scroll)
        self._scroll_layout = QVBoxLayout(self._scroll_host)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(10)
        self._scroll.setWidget(self._scroll_host)
        root.addWidget(self._scroll, 1)

        self._no_matches_label = QLabel("No settings match your search.")
        self._no_matches_label.setVisible(False)
        root.addWidget(self._no_matches_label)

        self._build_sections()
        self._load_preferences_into_controls(self._working_preferences)
        self._apply_search_filter("")

        self._live_preview_timer = QTimer(self)
        self._live_preview_timer.setSingleShot(True)
        self._live_preview_timer.timeout.connect(self._flush_live_preview)

        self._restore_defaults_button = QPushButton("Restore Appearance Defaults", self)
        self._restore_defaults_button.clicked.connect(self._restore_appearance_defaults)
        root.addWidget(self._restore_defaults_button)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._accept_with_apply)
        apply_button = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply_and_commit)
        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.clicked.connect(self.reject)
        root.addWidget(self._button_box)

    def _build_sections(self) -> None:
        appearance_group = self._add_section(
            key="appearance",
            title="Appearance",
            terms="appearance",
        )
        behavior_group = self._add_section(
            key="behavior",
            title="Behavior",
            terms="behavior",
        )
        panels_group = self._add_section(
            key="panels",
            title="Panels",
            terms="panels",
        )
        about_group = self._add_section(
            key="about",
            title="About",
            terms="about",
        )

        self.active_color_button = QPushButton("Choose Color", self)
        self.active_color_button.clicked.connect(self._choose_active_color)
        self.active_color_preview = QLabel(self)
        self.active_color_preview.setFixedWidth(44)
        self.active_color_preview.setMinimumHeight(22)
        self._add_row(
            section=appearance_group,
            key="active_color",
            title="Active Panel Tint Color",
            description="Base color used for active panel tint.",
            terms="active panel tint color",
            controls=[self.active_color_button, self.active_color_preview],
        )

        self.active_intensity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.active_intensity_slider.setRange(0, 100)
        self.active_intensity_slider.valueChanged.connect(self._on_controls_changed)
        self.active_intensity_value = QLabel(self)
        self.active_intensity_value.setMinimumWidth(44)
        self._add_row(
            section=appearance_group,
            key="active_intensity",
            title="Active Panel Tint Intensity",
            description="Opacity percentage for the active panel tint.",
            terms="active panel tint intensity opacity slider",
            controls=[self.active_intensity_slider, self.active_intensity_value],
        )

        self.target_color_button = QPushButton("Choose Color", self)
        self.target_color_button.clicked.connect(self._choose_target_color)
        self.target_color_preview = QLabel(self)
        self.target_color_preview.setFixedWidth(44)
        self.target_color_preview.setMinimumHeight(22)
        self._add_row(
            section=appearance_group,
            key="target_color",
            title="Target Panel Tint Color",
            description="Base color used for target panel tint.",
            terms="target panel tint color",
            controls=[self.target_color_button, self.target_color_preview],
        )

        self.target_intensity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.target_intensity_slider.setRange(0, 100)
        self.target_intensity_slider.valueChanged.connect(self._on_controls_changed)
        self.target_intensity_value = QLabel(self)
        self.target_intensity_value.setMinimumWidth(44)
        self._add_row(
            section=appearance_group,
            key="target_intensity",
            title="Target Panel Tint Intensity",
            description="Opacity percentage for the target panel tint.",
            terms="target panel tint intensity opacity slider",
            controls=[self.target_intensity_slider, self.target_intensity_value],
        )

        self.app_font_family_combo = self._new_font_family_combo(
            include_base_option=True,
            base_label="System Default",
        )
        self.app_font_size_spin = _FontSizeSpinBox(
            allow_system_value=True,
            min_size=6,
            max_size=32,
            parent=self,
        )
        self.app_font_size_spin.setSpecialValueText("System")
        self.app_font_size_spin.valueChanged.connect(self._on_controls_changed)
        self._add_row(
            section=appearance_group,
            key="app_font",
            title="App Font",
            description="Base font family and size used throughout the app.",
            terms="app font family size base",
            controls=[self.app_font_family_combo, self.app_font_size_spin],
        )

        self.file_list_use_app_font_checkbox = QCheckBox("Use app font", self)
        self.file_list_use_app_font_checkbox.toggled.connect(
            self._on_file_list_use_app_font_toggled
        )
        self.file_list_font_family_combo = self._new_font_family_combo(
            include_base_option=True,
            base_label="App Base",
        )
        self.file_list_font_size_spin = _FontSizeSpinBox(
            allow_system_value=False,
            min_size=6,
            max_size=32,
            parent=self,
        )
        self.file_list_font_size_spin.valueChanged.connect(self._on_controls_changed)
        self._add_row(
            section=appearance_group,
            key="file_list_font",
            title="File List Font",
            description="Override the file list (tree view) font family and size.",
            terms="file list tree view font family size",
            controls=[
                self.file_list_use_app_font_checkbox,
                self.file_list_font_family_combo,
                self.file_list_font_size_spin,
            ],
        )

        self.navigation_use_app_font_checkbox = QCheckBox("Use app font", self)
        self.navigation_use_app_font_checkbox.toggled.connect(
            self._on_navigation_use_app_font_toggled
        )
        self.navigation_font_family_combo = self._new_font_family_combo(
            include_base_option=True,
            base_label="App Base",
        )
        self.navigation_font_size_spin = _FontSizeSpinBox(
            allow_system_value=False,
            min_size=6,
            max_size=32,
            parent=self,
        )
        self.navigation_font_size_spin.valueChanged.connect(self._on_controls_changed)
        self._add_row(
            section=appearance_group,
            key="navigation_font",
            title="Navigation Toolbar Font",
            description="Override panel toolbar controls font family and size.",
            terms="navigation font toolbar family size panel",
            controls=[
                self.navigation_use_app_font_checkbox,
                self.navigation_font_family_combo,
                self.navigation_font_size_spin,
            ],
        )

        self.new_context_combo = QComboBox(self)
        for mode in ["clone_active_path", "home", "cwd"]:
            self.new_context_combo.addItem(_mode_label(mode), mode)
        self.new_context_combo.currentIndexChanged.connect(self._on_controls_changed)
        self._add_row(
            section=behavior_group,
            key="new_context_mode",
            title="New Context Mode",
            description="How new tabs/panels choose their starting path.",
            terms="new context mode clone active path home cwd",
            controls=[self.new_context_combo],
        )

        self.show_hidden_checkbox = QCheckBox("Show hidden files by default", self)
        self.show_hidden_checkbox.toggled.connect(self._on_controls_changed)
        self._add_row(
            section=panels_group,
            key="show_hidden_default",
            title="Show Hidden Files",
            description="Enable hidden/system entries by default for all panels.",
            terms="hidden files default",
            controls=[self.show_hidden_checkbox],
        )

        self.show_root_dropdown_checkbox = QCheckBox("Show root dropdown in each panel", self)
        self.show_root_dropdown_checkbox.toggled.connect(self._on_controls_changed)
        self._add_row(
            section=panels_group,
            key="show_root_dropdown",
            title="Root Dropdown",
            description="Display a root selector dropdown in panel toolbars.",
            terms="root dropdown panel toolbar",
            controls=[self.show_root_dropdown_checkbox],
        )

        self.show_refresh_button_checkbox = QCheckBox(
            "Show refresh button in each panel", self
        )
        self.show_refresh_button_checkbox.toggled.connect(self._on_controls_changed)
        self._add_row(
            section=panels_group,
            key="show_refresh_button",
            title="Refresh Button",
            description="Display the refresh button in panel toolbars.",
            terms="refresh button panel toolbar",
            controls=[self.show_refresh_button_checkbox],
        )

        self.show_root_buttons_checkbox = QCheckBox(
            "Show root buttons strip in each panel", self
        )
        self.show_root_buttons_checkbox.toggled.connect(self._on_controls_changed)
        self._add_row(
            section=panels_group,
            key="show_root_buttons",
            title="Root Buttons Strip",
            description="Display root/drive quick buttons in panel toolbars.",
            terms="root buttons strip drives panel toolbar",
            controls=[self.show_root_buttons_checkbox],
        )

        self.show_address_bar_checkbox = QCheckBox(
            "Show address textbox in each panel", self
        )
        self.show_address_bar_checkbox.toggled.connect(self._on_controls_changed)
        self._add_row(
            section=panels_group,
            key="show_address_bar",
            title="Address Textbox",
            description="Display the address bar in panel toolbars.",
            terms="address textbox bar panel toolbar",
            controls=[self.show_address_bar_checkbox],
        )

        self.show_navigation_buttons_checkbox = QCheckBox(
            "Show navigation buttons group in each panel", self
        )
        self.show_navigation_buttons_checkbox.toggled.connect(self._on_controls_changed)
        self._add_row(
            section=panels_group,
            key="show_navigation_buttons",
            title="Navigation Buttons Group",
            description="Display back, forward, up, and root buttons in panel toolbars.",
            terms="navigation buttons back forward up root panel toolbar",
            controls=[self.show_navigation_buttons_checkbox],
        )

        settings_path = Path(str(self.controller.settings.settings_path))
        self._add_row(
            section=about_group,
            key="about_name",
            title="Application",
            description=APP_DISPLAY_NAME,
            terms="application name",
            controls=[QLabel(APP_DISPLAY_NAME, self)],
        )
        self._add_row(
            section=about_group,
            key="about_version",
            title="Version",
            description=APP_VERSION,
            terms="version",
            controls=[QLabel(APP_VERSION, self)],
        )
        self._add_row(
            section=about_group,
            key="about_settings_path",
            title="Settings File",
            description=str(settings_path),
            terms=f"settings file path {settings_path}",
            controls=[QLabel(str(settings_path), self)],
        )

        self._scroll_layout.addStretch(1)

    def _add_section(self, *, key: str, title: str, terms: str) -> _SectionEntry:
        group = QGroupBox(title, self._scroll_host)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 12, 10, 10)
        group_layout.setSpacing(8)
        self._scroll_layout.addWidget(group)
        entry = _SectionEntry(key=key, group=group, terms=terms.casefold(), rows=[])
        self._sections[key] = entry
        self._assign_identity(group, f"settings_dialog:section:{key}", f"settings.section.{key}")
        return entry

    def _add_row(
        self,
        *,
        section: _SectionEntry,
        key: str,
        title: str,
        description: str,
        terms: str,
        controls: list[QWidget],
    ) -> None:
        row = QWidget(section.group)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        title_label = QLabel(title, row)
        title_label.setStyleSheet("font-weight: 600;")
        title_label.setWordWrap(True)
        row_layout.addWidget(title_label)

        description_label = QLabel(description, row)
        description_label.setWordWrap(True)
        row_layout.addWidget(description_label)

        controls_host = QWidget(row)
        controls_layout = QHBoxLayout(controls_host)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)
        for control in controls:
            controls_layout.addWidget(control)
        controls_layout.addStretch(1)
        row_layout.addWidget(controls_host)

        section.group.layout().addWidget(row)

        entry = _RowEntry(
            key=key,
            widget=row,
            terms=f"{title} {description} {terms}".casefold(),
        )
        section.rows.append(entry)
        self._rows_by_key[key] = row
        self._assign_identity(row, f"settings_dialog:row:{key}", f"settings.row.{key}")

    def _new_font_family_combo(
        self, *, include_base_option: bool, base_label: str
    ) -> QComboBox:
        combo = QComboBox(self)
        if include_base_option:
            combo.addItem(base_label, "")
        for family in QFontDatabase.families():
            combo.addItem(family, family)
        combo.currentIndexChanged.connect(self._on_controls_changed)
        return combo

    def _on_file_list_use_app_font_toggled(self, _checked: bool) -> None:
        self._sync_font_override_controls()
        self._on_controls_changed()

    def _on_navigation_use_app_font_toggled(self, _checked: bool) -> None:
        self._sync_font_override_controls()
        self._on_controls_changed()

    def _sync_font_override_controls(self) -> None:
        file_list_override_enabled = not self.file_list_use_app_font_checkbox.isChecked()
        self.file_list_font_family_combo.setEnabled(file_list_override_enabled)
        self.file_list_font_size_spin.setEnabled(file_list_override_enabled)

        navigation_override_enabled = (
            not self.navigation_use_app_font_checkbox.isChecked()
        )
        self.navigation_font_family_combo.setEnabled(navigation_override_enabled)
        self.navigation_font_size_spin.setEnabled(navigation_override_enabled)

    def _load_preferences_into_controls(self, preferences: UiPreferences) -> None:
        self._loading_ui = True
        try:
            self._working_preferences = replace(preferences)

            self.active_intensity_slider.setValue(
                preferences.active_panel_tint_intensity_percent
            )
            self.target_intensity_slider.setValue(
                preferences.target_panel_tint_intensity_percent
            )

            self._active_color_hex = preferences.active_panel_tint_color_hex
            self._target_color_hex = preferences.target_panel_tint_color_hex
            self._sync_color_preview(self.active_color_preview, self._active_color_hex)
            self._sync_color_preview(self.target_color_preview, self._target_color_hex)

            self._set_combo_value(
                self.new_context_combo, preferences.new_context_mode
            )
            self.show_hidden_checkbox.setChecked(preferences.show_hidden_default)
            self.show_root_dropdown_checkbox.setChecked(preferences.show_root_dropdown)
            self.show_refresh_button_checkbox.setChecked(
                preferences.show_refresh_button
            )
            self.show_root_buttons_checkbox.setChecked(preferences.show_root_buttons)
            self.show_address_bar_checkbox.setChecked(preferences.show_address_bar)
            self.show_navigation_buttons_checkbox.setChecked(
                preferences.show_navigation_buttons
            )
            self._set_combo_value(self.app_font_family_combo, preferences.app_font_family)
            self.app_font_size_spin.setValue(preferences.app_font_size_pt)
            self.file_list_use_app_font_checkbox.setChecked(
                preferences.file_list_use_app_font
            )
            self._set_combo_value(
                self.file_list_font_family_combo, preferences.file_list_font_family
            )
            self.file_list_font_size_spin.setValue(preferences.file_list_font_size_pt)
            self.navigation_use_app_font_checkbox.setChecked(
                preferences.navigation_use_app_font
            )
            self._set_combo_value(
                self.navigation_font_family_combo, preferences.navigation_font_family
            )
            self.navigation_font_size_spin.setValue(
                preferences.navigation_font_size_pt
            )
            self._sync_font_override_controls()
            self._sync_slider_value_labels()
        finally:
            self._loading_ui = False

    def _sync_slider_value_labels(self) -> None:
        self.active_intensity_value.setText(f"{self.active_intensity_slider.value()}%")
        self.target_intensity_value.setText(f"{self.target_intensity_slider.value()}%")

    def _sync_color_preview(self, target: QLabel, color_hex: str) -> None:
        target.setStyleSheet(f"background: {color_hex}; border: 1px solid #777;")
        target.setText(color_hex)
        target.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if str(combo.itemData(index)) == str(value):
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _on_controls_changed(self) -> None:
        if self._loading_ui:
            return
        self._sync_slider_value_labels()
        self._working_preferences = UiPreferences(
            new_context_mode=str(self.new_context_combo.currentData()),
            show_hidden_default=self.show_hidden_checkbox.isChecked(),
            show_root_dropdown=self.show_root_dropdown_checkbox.isChecked(),
            show_refresh_button=self.show_refresh_button_checkbox.isChecked(),
            show_root_buttons=self.show_root_buttons_checkbox.isChecked(),
            show_address_bar=self.show_address_bar_checkbox.isChecked(),
            show_navigation_buttons=self.show_navigation_buttons_checkbox.isChecked(),
            app_font_family=str(self.app_font_family_combo.currentData() or ""),
            app_font_size_pt=self.app_font_size_spin.value(),
            file_list_use_app_font=self.file_list_use_app_font_checkbox.isChecked(),
            file_list_font_family=str(
                self.file_list_font_family_combo.currentData() or ""
            ),
            file_list_font_size_pt=self.file_list_font_size_spin.value(),
            navigation_use_app_font=self.navigation_use_app_font_checkbox.isChecked(),
            navigation_font_family=str(
                self.navigation_font_family_combo.currentData() or ""
            ),
            navigation_font_size_pt=self.navigation_font_size_spin.value(),
            active_panel_tint_color_hex=self._active_color_hex,
            active_panel_tint_intensity_percent=self.active_intensity_slider.value(),
            target_panel_tint_color_hex=self._target_color_hex,
            target_panel_tint_intensity_percent=self.target_intensity_slider.value(),
        )
        self._pending_live_preview = True
        self._live_preview_timer.start(self.LIVE_PREVIEW_DEBOUNCE_MS)

    def _flush_live_preview(self) -> None:
        if not self._pending_live_preview:
            return
        self._pending_live_preview = False
        self.controller.preview_ui_preferences(self._working_preferences)

    def _choose_active_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self._active_color_hex), self, "Active Tint Color")
        if not selected.isValid():
            return
        self._active_color_hex = selected.name(QColor.NameFormat.HexRgb).upper()
        self._sync_color_preview(self.active_color_preview, self._active_color_hex)
        self._on_controls_changed()

    def _choose_target_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self._target_color_hex), self, "Target Tint Color")
        if not selected.isValid():
            return
        self._target_color_hex = selected.name(QColor.NameFormat.HexRgb).upper()
        self._sync_color_preview(self.target_color_preview, self._target_color_hex)
        self._on_controls_changed()

    def _restore_appearance_defaults(self) -> None:
        self._active_color_hex = SettingsManager.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX
        self._target_color_hex = SettingsManager.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX
        self._sync_color_preview(self.active_color_preview, self._active_color_hex)
        self._sync_color_preview(self.target_color_preview, self._target_color_hex)
        self._set_combo_value(
            self.app_font_family_combo, SettingsManager.DEFAULT_APP_FONT_FAMILY
        )
        self.app_font_size_spin.setValue(SettingsManager.DEFAULT_APP_FONT_SIZE_PT)
        self.file_list_use_app_font_checkbox.setChecked(
            SettingsManager.DEFAULT_FILE_LIST_USE_APP_FONT
        )
        self._set_combo_value(
            self.file_list_font_family_combo,
            SettingsManager.DEFAULT_FILE_LIST_FONT_FAMILY,
        )
        self.file_list_font_size_spin.setValue(
            SettingsManager.DEFAULT_FILE_LIST_FONT_SIZE_PT
        )
        self.navigation_use_app_font_checkbox.setChecked(
            SettingsManager.DEFAULT_NAVIGATION_USE_APP_FONT
        )
        self._set_combo_value(
            self.navigation_font_family_combo,
            SettingsManager.DEFAULT_NAVIGATION_FONT_FAMILY,
        )
        self.navigation_font_size_spin.setValue(
            SettingsManager.DEFAULT_NAVIGATION_FONT_SIZE_PT
        )
        self._sync_font_override_controls()
        self.active_intensity_slider.setValue(
            SettingsManager.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT
        )
        self.target_intensity_slider.setValue(
            SettingsManager.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT
        )
        self._on_controls_changed()

    def _accept_with_apply(self) -> None:
        self._apply_and_commit()
        self.accept()

    def _apply_and_commit(self) -> None:
        self._on_controls_changed()
        self._live_preview_timer.stop()
        self._pending_live_preview = False
        self.controller.apply_ui_preferences(self._working_preferences)
        self._committed_preferences = replace(self._working_preferences)

    def reject(self) -> None:
        self._live_preview_timer.stop()
        self._pending_live_preview = False
        self.controller.preview_ui_preferences(self._committed_preferences)
        super().reject()

    def _apply_search_filter(self, text: str) -> None:
        query = str(text or "").strip().casefold()
        visible_rows = 0
        for section in self._sections.values():
            section_match = bool(query) and query in section.terms
            section_visible_rows = 0
            for row in section.rows:
                row_visible = (not query) or section_match or (query in row.terms)
                row.widget.setVisible(row_visible)
                if row_visible:
                    section_visible_rows += 1
            section_visible = section_visible_rows > 0
            section.group.setVisible(section_visible)
            visible_rows += section_visible_rows
        self._no_matches_label.setVisible(bool(query) and visible_rows == 0)

    def _assign_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        widget.setObjectName(widget_naming.object_name_for_id(widget_id))
        widget.setProperty("widget_id", widget_id)
        widget.setProperty("widget_alias", alias)
