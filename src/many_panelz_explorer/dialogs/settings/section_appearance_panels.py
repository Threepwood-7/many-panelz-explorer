"""Appearance, behavior, and panel section builders for settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
)

from . import control_builders
from .section_models import FontSizeSpinBox, SubsectionEntry
from .section_structure import add_row

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def _mode_label(mode: str) -> str:
    """Return the UI label for a new-context mode."""

    if mode == "home":
        return "Home"
    if mode == "cwd":
        return "Current Working Directory"
    return "Clone Active Path"


def build_appearance_rows(
    dialog: SettingsDialog,
    *,
    panel_tint_group: SubsectionEntry,
    typography_group: SubsectionEntry,
) -> None:
    """Build appearance rows for panel tint and typography."""

    build_panel_tint_rows(dialog, panel_tint_group=panel_tint_group)
    build_typography_rows(dialog, typography_group=typography_group)


def build_panel_tint_rows(
    dialog: SettingsDialog,
    *,
    panel_tint_group: SubsectionEntry,
) -> None:
    """Build panel tint color and intensity rows."""

    dialog.active_color_button = QPushButton("Choose Color", dialog)
    dialog.active_color_button.clicked.connect(dialog.choose_active_color)
    dialog.active_color_preview = QLabel(dialog)
    dialog.active_color_preview.setFixedWidth(44)
    dialog.active_color_preview.setMinimumHeight(22)
    add_row(
        dialog,
        section=panel_tint_group,
        key="active_color",
        title="Active Panel Tint Color",
        description="Base color used for active panel tint.",
        terms="active panel tint color",
        controls=[dialog.active_color_button, dialog.active_color_preview],
    )

    dialog.active_intensity_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    dialog.active_intensity_slider.setRange(0, 100)
    dialog.active_intensity_slider.valueChanged.connect(dialog.on_controls_changed)
    dialog.active_intensity_value = QLabel(dialog)
    dialog.active_intensity_value.setMinimumWidth(44)
    add_row(
        dialog,
        section=panel_tint_group,
        key="active_intensity",
        title="Active Panel Tint Intensity",
        description="Opacity percentage for the active panel tint.",
        terms="active panel tint intensity opacity slider",
        controls=[dialog.active_intensity_slider, dialog.active_intensity_value],
    )

    dialog.target_color_button = QPushButton("Choose Color", dialog)
    dialog.target_color_button.clicked.connect(dialog.choose_target_color)
    dialog.target_color_preview = QLabel(dialog)
    dialog.target_color_preview.setFixedWidth(44)
    dialog.target_color_preview.setMinimumHeight(22)
    add_row(
        dialog,
        section=panel_tint_group,
        key="target_color",
        title="Target Panel Tint Color",
        description="Base color used for target panel tint.",
        terms="target panel tint color",
        controls=[dialog.target_color_button, dialog.target_color_preview],
    )

    dialog.target_intensity_slider = QSlider(Qt.Orientation.Horizontal, dialog)
    dialog.target_intensity_slider.setRange(0, 100)
    dialog.target_intensity_slider.valueChanged.connect(dialog.on_controls_changed)
    dialog.target_intensity_value = QLabel(dialog)
    dialog.target_intensity_value.setMinimumWidth(44)
    add_row(
        dialog,
        section=panel_tint_group,
        key="target_intensity",
        title="Target Panel Tint Intensity",
        description="Opacity percentage for the target panel tint.",
        terms="target panel tint intensity opacity slider",
        controls=[dialog.target_intensity_slider, dialog.target_intensity_value],
    )


def build_typography_rows(
    dialog: SettingsDialog,
    *,
    typography_group: SubsectionEntry,
) -> None:
    """Build app, file-list, and navigation typography rows."""

    dialog.app_font_family_combo = dialog.new_font_family_combo(
        include_base_option=True,
        base_label="System Default",
    )
    dialog.app_font_size_spin = FontSizeSpinBox(
        allow_system_value=True,
        min_size=6,
        max_size=32,
        parent=dialog,
    )
    dialog.app_font_size_spin.setSpecialValueText("System")
    dialog.app_font_size_spin.valueChanged.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=typography_group,
        key="app_font",
        title="App Font",
        description="Base font family and size used throughout the app.",
        terms="app font family size base",
        controls=[dialog.app_font_family_combo, dialog.app_font_size_spin],
    )

    dialog.file_list_use_app_font_checkbox = QCheckBox("Use app font", dialog)
    dialog.file_list_use_app_font_checkbox.toggled.connect(
        dialog.on_file_list_use_app_font_toggled
    )
    dialog.file_list_font_family_combo = dialog.new_font_family_combo(
        include_base_option=True,
        base_label="App Base",
    )
    dialog.file_list_font_size_spin = FontSizeSpinBox(
        allow_system_value=False,
        min_size=6,
        max_size=32,
        parent=dialog,
    )
    dialog.file_list_font_size_spin.valueChanged.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=typography_group,
        key="file_list_font",
        title="File List Font",
        description="Override the file list (tree view) font family and size.",
        terms="file list tree view font family size",
        controls=[
            dialog.file_list_use_app_font_checkbox,
            dialog.file_list_font_family_combo,
            dialog.file_list_font_size_spin,
        ],
    )

    dialog.navigation_use_app_font_checkbox = QCheckBox("Use app font", dialog)
    dialog.navigation_use_app_font_checkbox.toggled.connect(
        dialog.on_navigation_use_app_font_toggled
    )
    dialog.navigation_font_family_combo = dialog.new_font_family_combo(
        include_base_option=True,
        base_label="App Base",
    )
    dialog.navigation_font_size_spin = FontSizeSpinBox(
        allow_system_value=False,
        min_size=6,
        max_size=32,
        parent=dialog,
    )
    dialog.navigation_font_size_spin.valueChanged.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=typography_group,
        key="navigation_font",
        title="Navigation Toolbar Font",
        description="Override panel toolbar controls font family and size.",
        terms="navigation font toolbar family size panel",
        controls=[
            dialog.navigation_use_app_font_checkbox,
            dialog.navigation_font_family_combo,
            dialog.navigation_font_size_spin,
        ],
    )


def build_behavior_rows(
    dialog: SettingsDialog,
    *,
    context_defaults_group: SubsectionEntry,
    scan_limits_group: SubsectionEntry,
) -> None:
    """Build behavior rows for context defaults and scan limits."""

    dialog.new_context_combo = QComboBox(dialog)
    for mode in ["clone_active_path", "home", "cwd"]:
        dialog.new_context_combo.addItem(_mode_label(mode), mode)
    dialog.new_context_combo.currentIndexChanged.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=context_defaults_group,
        key="new_context_mode",
        title="New Context Mode",
        description="How new tabs/panels choose their starting path.",
        terms="new context mode clone active path home cwd",
        controls=[dialog.new_context_combo],
    )

    dialog.context_scan_cap_spin = QSpinBox(dialog)
    dialog.context_scan_cap_spin.setRange(1, 10_000)
    dialog.context_scan_cap_spin.valueChanged.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=scan_limits_group,
        key="context_scan_cap",
        title="Context Child Scan Cap",
        description=(
            "Maximum immediate child directories scanned for Context mode detection."
        ),
        terms="context detection child scan cap limit",
        controls=[dialog.context_scan_cap_spin],
    )


def build_panels_rows(
    dialog: SettingsDialog,
    *,
    visibility_group: SubsectionEntry,
    file_list_layout_group: SubsectionEntry,
    byte_display_group: SubsectionEntry,
) -> None:
    """Build panel visibility, layout, and byte-display rows."""

    build_panel_visibility_rows(dialog, visibility_group=visibility_group)
    build_panel_layout_rows(dialog, file_list_layout_group=file_list_layout_group)
    build_panel_byte_display_rows(dialog, byte_display_group=byte_display_group)


def build_panel_visibility_rows(
    dialog: SettingsDialog,
    *,
    visibility_group: SubsectionEntry,
) -> None:
    """Build panel visibility and toolbar control rows."""

    dialog.show_hidden_checkbox = QCheckBox(
        "Show hidden files by default",
        dialog,
    )
    dialog.show_hidden_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=visibility_group,
        key="show_hidden_default",
        title="Show Hidden Files",
        description="Enable hidden/system entries by default for all panels.",
        terms="hidden files default",
        controls=[dialog.show_hidden_checkbox],
    )

    dialog.show_root_dropdown_checkbox = QCheckBox(
        "Show root dropdown in each panel",
        dialog,
    )
    dialog.show_root_dropdown_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=visibility_group,
        key="show_root_dropdown",
        title="Root Dropdown",
        description="Display a root selector dropdown in panel toolbars.",
        terms="root dropdown panel toolbar",
        controls=[dialog.show_root_dropdown_checkbox],
    )

    dialog.show_refresh_button_checkbox = QCheckBox(
        "Show refresh button in each panel",
        dialog,
    )
    dialog.show_refresh_button_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=visibility_group,
        key="show_refresh_button",
        title="Refresh Button",
        description="Display the refresh button in panel toolbars.",
        terms="refresh button panel toolbar",
        controls=[dialog.show_refresh_button_checkbox],
    )

    dialog.show_root_buttons_checkbox = QCheckBox(
        "Show root buttons strip in each panel",
        dialog,
    )
    dialog.show_root_buttons_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=visibility_group,
        key="show_root_buttons",
        title="Root Buttons Strip",
        description="Display root/drive quick buttons in panel toolbars.",
        terms="root buttons strip drives panel toolbar",
        controls=[dialog.show_root_buttons_checkbox],
    )

    dialog.show_address_bar_checkbox = QCheckBox(
        "Show address textbox in each panel",
        dialog,
    )
    dialog.show_address_bar_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=visibility_group,
        key="show_address_bar",
        title="Address Textbox",
        description="Display the address bar in panel toolbars.",
        terms="address textbox bar panel toolbar",
        controls=[dialog.show_address_bar_checkbox],
    )

    dialog.show_navigation_buttons_checkbox = QCheckBox(
        "Show navigation buttons group in each panel",
        dialog,
    )
    dialog.show_navigation_buttons_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=visibility_group,
        key="show_navigation_buttons",
        title="Navigation Buttons Group",
        description="Display back, forward, up, and root buttons in panel toolbars.",
        terms="navigation buttons back forward up root panel toolbar",
        controls=[dialog.show_navigation_buttons_checkbox],
    )

    dialog.show_storage_overview_status_row_checkbox = QCheckBox(
        "Show global storage overview status row",
        dialog,
    )
    dialog.show_storage_overview_status_row_checkbox.toggled.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=visibility_group,
        key="show_storage_overview_status_row",
        title="Storage Overview Status Row",
        description=(
            "Display an always-visible storage usage row in the window status bar."
        ),
        terms="storage overview status row disk usage free total mount points",
        controls=[dialog.show_storage_overview_status_row_checkbox],
    )


def build_panel_layout_rows(
    dialog: SettingsDialog,
    *,
    file_list_layout_group: SubsectionEntry,
) -> None:
    """Build panel file-list layout rows."""

    dialog.column_width_auto_align_mode_combo = QComboBox(dialog)
    dialog.column_width_auto_align_mode_combo.addItem(
        "Current panel tabs",
        "current_panel_tabs",
    )
    dialog.column_width_auto_align_mode_combo.addItem(
        "All panels and tabs in current window",
        "current_window_panels_tabs",
    )
    dialog.column_width_auto_align_mode_combo.addItem(
        "All panels and tabs in all windows",
        "all_windows_panels_tabs",
    )
    dialog.column_width_auto_align_mode_combo.addItem("No alignment", "none")
    dialog.column_width_auto_align_mode_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=file_list_layout_group,
        key="column_width_auto_align_mode",
        title="Auto-Align Column Widths",
        description="Choose how file-list column width changes propagate.",
        terms="column width align auto-align tabs panels current window all windows",
        controls=[dialog.column_width_auto_align_mode_combo],
    )

    dialog.autofit_columns_checkbox = QCheckBox("Fit on startup and resize", dialog)
    dialog.autofit_columns_checkbox.toggled.connect(dialog.on_controls_changed)
    add_row(
        dialog,
        section=file_list_layout_group,
        key="autofit_columns",
        title="Autofit Columns",
        description=(
            "Fit all file-list columns in the current window on startup and resize."
        ),
        terms="autofit columns fit startup resize current window file list",
        controls=[dialog.autofit_columns_checkbox],
    )


def build_panel_byte_display_rows(
    dialog: SettingsDialog,
    *,
    byte_display_group: SubsectionEntry,
) -> None:
    """Build panel byte-format and status-row formatting rows."""

    build_byte_separator_row(dialog, byte_display_group=byte_display_group)
    build_file_list_byte_format_row(dialog, byte_display_group=byte_display_group)
    build_status_bar_byte_format_rows(dialog, byte_display_group=byte_display_group)
    build_properties_byte_format_row(dialog, byte_display_group=byte_display_group)


def build_byte_separator_row(
    dialog: SettingsDialog,
    *,
    byte_display_group: SubsectionEntry,
) -> None:
    """Build the global byte-separator settings row."""

    dialog.byte_thousands_separator_edit = QLineEdit(dialog)
    dialog.byte_thousands_separator_edit.setMaxLength(1)
    dialog.byte_thousands_separator_edit.setPlaceholderText(",")
    dialog.byte_thousands_separator_edit.setToolTip(
        "Thousands separator (leave empty to disable grouping)"
    )
    dialog.byte_thousands_separator_edit.textChanged.connect(dialog.on_controls_changed)

    dialog.byte_decimal_separator_edit = QLineEdit(dialog)
    dialog.byte_decimal_separator_edit.setMaxLength(1)
    dialog.byte_decimal_separator_edit.setPlaceholderText(".")
    dialog.byte_decimal_separator_edit.setToolTip("Decimal separator")
    dialog.byte_decimal_separator_edit.textChanged.connect(dialog.on_controls_changed)

    byte_separators_controls = control_builders.build_dual_text_controls(
        dialog,
        first_label="Thousands",
        first_edit=dialog.byte_thousands_separator_edit,
        second_label="Decimal",
        second_edit=dialog.byte_decimal_separator_edit,
    )
    add_row(
        dialog,
        section=byte_display_group,
        key="byte_separators",
        title="Byte Number Separators",
        description="Global separators applied to all byte display contexts.",
        terms="bytes format separators thousands decimal global",
        controls=[byte_separators_controls],
    )


def build_file_list_byte_format_row(
    dialog: SettingsDialog,
    *,
    byte_display_group: SubsectionEntry,
) -> None:
    """Build the file-list byte formatting row."""

    dialog.file_list_byte_format_mode_combo = dialog.new_byte_format_mode_combo()
    dialog.file_list_byte_custom_template_edit = QLineEdit(dialog)
    dialog.file_list_byte_custom_template_edit.setPlaceholderText("{b}")
    dialog.file_list_byte_custom_template_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=byte_display_group,
        key="file_list_byte_format",
        title="File List Size Format",
        description="How the file-list Size column displays byte values.",
        terms="file list size bytes format mode custom template",
        controls=[
            dialog.file_list_byte_format_mode_combo,
            dialog.file_list_byte_custom_template_edit,
        ],
    )


def build_status_bar_byte_format_rows(
    dialog: SettingsDialog,
    *,
    byte_display_group: SubsectionEntry,
) -> None:
    """Build the status-bar byte formatting and label template rows."""

    dialog.status_bar_byte_format_mode_combo = dialog.new_byte_format_mode_combo()
    dialog.status_bar_byte_custom_template_edit = QLineEdit(dialog)
    dialog.status_bar_byte_custom_template_edit.setPlaceholderText("{b}")
    dialog.status_bar_byte_custom_template_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=byte_display_group,
        key="status_bar_byte_format",
        title="Status Bar Storage Format",
        description="How status-bar storage used/total values are displayed.",
        terms="status bar storage bytes format mode custom template",
        controls=[
            dialog.status_bar_byte_format_mode_combo,
            dialog.status_bar_byte_custom_template_edit,
        ],
    )

    dialog.status_bar_storage_label_template_edit = QLineEdit(dialog)
    dialog.status_bar_storage_label_template_edit.setPlaceholderText(
        "{disk_root} {disk_label} {used_space}/{total_space}"
    )
    dialog.status_bar_storage_label_template_edit.setToolTip(
        "Placeholders: {disk_label} {disk_root} {root_path} {used_space} "
        "{free_space} {total_space} {used_bytes} {free_bytes} {total_bytes} "
        "{usage_percentage} {free_percentage} {usage_ratio} {free_ratio} "
        "{usage_indicator} {free_indicator}"
    )
    dialog.status_bar_storage_label_template_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=byte_display_group,
        key="status_bar_storage_label_template",
        title="Status Bar Disk Label Template",
        description=(
            "Template for each disk label in the storage status row. Use "
            "placeholders like {disk_label}, {used_space}, and {usage_indicator}."
        ),
        terms=(
            "status bar storage disk label template placeholders usage free total "
            "percentage indicator tooltip"
        ),
        controls=[dialog.status_bar_storage_label_template_edit],
    )


def build_properties_byte_format_row(
    dialog: SettingsDialog,
    *,
    byte_display_group: SubsectionEntry,
) -> None:
    """Build the Properties-dialog byte formatting row."""

    dialog.properties_byte_format_mode_combo = dialog.new_byte_format_mode_combo()
    dialog.properties_byte_custom_template_edit = QLineEdit(dialog)
    dialog.properties_byte_custom_template_edit.setPlaceholderText("{b}")
    dialog.properties_byte_custom_template_edit.textChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=byte_display_group,
        key="properties_byte_format",
        title="Properties Size Format",
        description="How file/folder size is shown in the Properties dialog.",
        terms="properties dialog bytes format mode custom template",
        controls=[
            dialog.properties_byte_format_mode_combo,
            dialog.properties_byte_custom_template_edit,
        ],
    )
