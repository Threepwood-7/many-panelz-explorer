from __future__ import annotations

import json
import tempfile
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import widget_naming
from .._operations.discovery import (
    discover_single_companion_tool,
    resolve_companion_tool_paths,
    resolve_system_command_paths,
)
from .._operations.executors import execute_operation_request
from .._operations.types import (
    DEFAULT_RIMRAF_EXE,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_EXE,
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationRequest,
)
from .._settings.manager import SettingsManager
from .._settings.models import UiPreferences
from ..constants import APP_DISPLAY_NAME, APP_VERSION
from .settings import control_builders

if TYPE_CHECKING:
    from collections.abc import Callable

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
        self._section_tree_items: dict[str, QTreeWidgetItem] = {}
        self._tree_sync_in_progress = False

        self.setWindowTitle("Settings")
        self.resize(1180, 820)
        self.setMinimumSize(1080, 760)
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

        content_host = QWidget(self)
        content_layout = QHBoxLayout(content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        root.addWidget(content_host, 1)

        self._section_tree = QTreeWidget(content_host)
        self._section_tree.setHeaderHidden(True)
        self._section_tree.setIndentation(12)
        self._section_tree.setMinimumWidth(220)
        self._section_tree.setMaximumWidth(280)
        self._section_tree.currentItemChanged.connect(self._on_section_tree_changed)
        self._assign_identity(
            self._section_tree, "settings_dialog:section_tree", "settings.section_tree"
        )
        content_layout.addWidget(self._section_tree, 0)

        right_host = QWidget(content_host)
        right_layout = QVBoxLayout(right_host)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        content_layout.addWidget(right_host, 1)

        self._scroll = QScrollArea(right_host)
        self._scroll.setWidgetResizable(True)
        self._scroll_host = QWidget(self._scroll)
        self._scroll_layout = QVBoxLayout(self._scroll_host)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(10)
        self._scroll.setWidget(self._scroll_host)
        right_layout.addWidget(self._scroll, 1)

        self._no_matches_label = QLabel("No settings match your search.", right_host)
        self._no_matches_label.setVisible(False)
        right_layout.addWidget(self._no_matches_label)

        self._build_sections()
        if self._section_tree.topLevelItemCount() > 0:
            self._section_tree.setCurrentItem(self._section_tree.topLevelItem(0))
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
        operations_group = self._add_section(
            key="operations",
            title="Operations",
            terms="operations copy move delete queue backend",
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

        self.context_scan_cap_spin = QSpinBox(self)
        self.context_scan_cap_spin.setRange(1, 10_000)
        self.context_scan_cap_spin.valueChanged.connect(self._on_controls_changed)
        self._add_row(
            section=behavior_group,
            key="context_scan_cap",
            title="Context Child Scan Cap",
            description="Maximum immediate child directories scanned for Context mode detection.",
            terms="context detection child scan cap limit",
            controls=[self.context_scan_cap_spin],
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

        self.column_width_auto_align_mode_combo = QComboBox(self)
        self.column_width_auto_align_mode_combo.addItem(
            "All panels and tabs", "all_panels_tabs"
        )
        self.column_width_auto_align_mode_combo.addItem(
            "Current panel tabs", "current_panel_tabs"
        )
        self.column_width_auto_align_mode_combo.addItem("No alignment", "none")
        self.column_width_auto_align_mode_combo.currentIndexChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=panels_group,
            key="column_width_auto_align_mode",
            title="Auto-Align Column Widths",
            description="Choose how file-list column width changes propagate.",
            terms="column width align auto-align tabs panels",
            controls=[self.column_width_auto_align_mode_combo],
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

        self.show_storage_overview_status_row_checkbox = QCheckBox(
            "Show global storage overview status row", self
        )
        self.show_storage_overview_status_row_checkbox.toggled.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=panels_group,
            key="show_storage_overview_status_row",
            title="Storage Overview Status Row",
            description="Display an always-visible storage usage row in the window status bar.",
            terms="storage overview status row disk usage free total mount points",
            controls=[self.show_storage_overview_status_row_checkbox],
        )

        self.byte_thousands_separator_edit = QLineEdit(self)
        self.byte_thousands_separator_edit.setMaxLength(1)
        self.byte_thousands_separator_edit.setPlaceholderText(",")
        self.byte_thousands_separator_edit.setToolTip(
            "Thousands separator (leave empty to disable grouping)"
        )
        self.byte_thousands_separator_edit.textChanged.connect(self._on_controls_changed)

        self.byte_decimal_separator_edit = QLineEdit(self)
        self.byte_decimal_separator_edit.setMaxLength(1)
        self.byte_decimal_separator_edit.setPlaceholderText(".")
        self.byte_decimal_separator_edit.setToolTip("Decimal separator")
        self.byte_decimal_separator_edit.textChanged.connect(self._on_controls_changed)

        byte_separators_controls = self._build_dual_text_controls(
            first_label="Thousands",
            first_edit=self.byte_thousands_separator_edit,
            second_label="Decimal",
            second_edit=self.byte_decimal_separator_edit,
        )
        self._add_row(
            section=panels_group,
            key="byte_separators",
            title="Byte Number Separators",
            description="Global separators applied to all byte display contexts.",
            terms="bytes format separators thousands decimal global",
            controls=[byte_separators_controls],
        )

        self.file_list_byte_format_mode_combo = self._new_byte_format_mode_combo()
        self.file_list_byte_custom_template_edit = QLineEdit(self)
        self.file_list_byte_custom_template_edit.setPlaceholderText("{b}")
        self.file_list_byte_custom_template_edit.textChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=panels_group,
            key="file_list_byte_format",
            title="File List Size Format",
            description="How the file-list Size column displays byte values.",
            terms="file list size bytes format mode custom template",
            controls=[
                self.file_list_byte_format_mode_combo,
                self.file_list_byte_custom_template_edit,
            ],
        )

        self.status_bar_byte_format_mode_combo = self._new_byte_format_mode_combo()
        self.status_bar_byte_custom_template_edit = QLineEdit(self)
        self.status_bar_byte_custom_template_edit.setPlaceholderText("{b}")
        self.status_bar_byte_custom_template_edit.textChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=panels_group,
            key="status_bar_byte_format",
            title="Status Bar Storage Format",
            description="How status-bar storage used/total values are displayed.",
            terms="status bar storage bytes format mode custom template",
            controls=[
                self.status_bar_byte_format_mode_combo,
                self.status_bar_byte_custom_template_edit,
            ],
        )

        self.properties_byte_format_mode_combo = self._new_byte_format_mode_combo()
        self.properties_byte_custom_template_edit = QLineEdit(self)
        self.properties_byte_custom_template_edit.setPlaceholderText("{b}")
        self.properties_byte_custom_template_edit.textChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=panels_group,
            key="properties_byte_format",
            title="Properties Size Format",
            description="How file/folder size is shown in the Properties dialog.",
            terms="properties dialog bytes format mode custom template",
            controls=[
                self.properties_byte_format_mode_combo,
                self.properties_byte_custom_template_edit,
            ],
        )

        self.default_copy_move_backend_combo = QComboBox(self)
        self.default_copy_move_backend_combo.addItem("Python Built-in", "python_builtin")
        self.default_copy_move_backend_combo.addItem("Windows Explorer", "windows_explorer")
        self.default_copy_move_backend_combo.addItem("Robocopy", "robocopy")
        self.default_copy_move_backend_combo.addItem("TeraCopy", "teracopy")
        self.default_copy_move_backend_combo.addItem("Unstoppable Copier", "unstoppable")
        self.default_copy_move_backend_combo.addItem("External Command", "external_copymove")
        self.default_copy_move_backend_combo.currentIndexChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=operations_group,
            key="default_copy_move_backend",
            title="Default Copy/Move Backend",
            description="Backend used for copy/move when no per-run override is chosen.",
            terms="copy move backend default python explorer robocopy teracopy unstoppable external",
            controls=[self.default_copy_move_backend_combo],
        )

        self.default_delete_backend_combo = QComboBox(self)
        self.default_delete_backend_combo.addItem("Recycle Bin", "recycle_bin")
        self.default_delete_backend_combo.addItem("Permanent Native", "permanent_native")
        self.default_delete_backend_combo.addItem("cmd Delete", "cmd_delete")
        self.default_delete_backend_combo.addItem("PowerShell Delete", "powershell_delete")
        self.default_delete_backend_combo.addItem("rimraf", "rimraf")
        self.default_delete_backend_combo.addItem("External Delete", "external_delete")
        self.default_delete_backend_combo.currentIndexChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=operations_group,
            key="default_delete_backend",
            title="Default Delete Backend",
            description="Backend used for delete operations when no per-run override is chosen.",
            terms="delete backend default recycle bin permanent cmd powershell rimraf external",
            controls=[self.default_delete_backend_combo],
        )

        self.default_dispatch_mode_combo = QComboBox(self)
        self.default_dispatch_mode_combo.addItem("Queue", "queue")
        self.default_dispatch_mode_combo.addItem("Launch Now (No Wait)", "launch_now_no_wait")
        self.default_dispatch_mode_combo.addItem("Run Now (Wait)", "run_now_wait")
        self.default_dispatch_mode_combo.currentIndexChanged.connect(self._on_controls_changed)
        self._add_row(
            section=operations_group,
            key="default_operation_dispatch_mode",
            title="Default Dispatch Mode",
            description="Choose whether operations queue, launch detached, or run synchronously.",
            terms="dispatch mode queue launch wait operation",
            controls=[self.default_dispatch_mode_combo],
        )

        self.default_conflict_policy_combo = QComboBox(self)
        self.default_conflict_policy_combo.addItem("Overwrite", "overwrite")
        self.default_conflict_policy_combo.addItem("Skip", "skip")
        self.default_conflict_policy_combo.addItem("Rename", "rename")
        self.default_conflict_policy_combo.addItem("Cancel", "cancel")
        self.default_conflict_policy_combo.currentIndexChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=operations_group,
            key="default_operation_conflict_policy",
            title="Default Conflict Policy",
            description="Default name-conflict behavior for non-interactive copy/move.",
            terms="conflict policy overwrite skip rename cancel",
            controls=[self.default_conflict_policy_combo],
        )

        self.operation_shortcut_behavior_combo = QComboBox(self)
        self.operation_shortcut_behavior_combo.addItem("Direct Enqueue", "direct_enqueue")
        self.operation_shortcut_behavior_combo.addItem("Always Show Dialog", "always_dialog")
        self.operation_shortcut_behavior_combo.currentIndexChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=operations_group,
            key="operation_shortcut_behavior",
            title="Shortcut Behavior",
            description="Choose whether F5/F6/F8 use defaults directly or open a configuration dialog.",
            terms="shortcut behavior f5 f6 f8 dialog enqueue",
            controls=[self.operation_shortcut_behavior_combo],
        )

        self.operation_queue_view_mode_combo = QComboBox(self)
        self.operation_queue_view_mode_combo.addItem("Queue Dock", "dock_tab")
        self.operation_queue_view_mode_combo.addItem("Floating Window", "floating_window")
        self.operation_queue_view_mode_combo.addItem("Both", "both")
        self.operation_queue_view_mode_combo.currentIndexChanged.connect(
            self._on_controls_changed
        )
        self._add_row(
            section=operations_group,
            key="operation_queue_view_mode",
            title="Queue View Mode",
            description="Default queue presentation mode at runtime.",
            terms="queue dock floating window both",
            controls=[self.operation_queue_view_mode_combo],
        )

        self.default_editor_executable_edit = QLineEdit(self)
        default_editor_controls = self._build_path_controls(
            executable_edit=self.default_editor_executable_edit,
            default_executable=SettingsManager.DEFAULT_DEFAULT_EDITOR_EXECUTABLE,
        )
        self._add_row(
            section=operations_group,
            key="default_editor_executable",
            title="Default Editor",
            description="Default executable used for edit operations, including queue scripts.",
            terms="default editor executable open edit script",
            controls=[default_editor_controls],
        )

        self.default_viewer_executable_edit = QLineEdit(self)
        default_viewer_controls = self._build_path_controls(
            executable_edit=self.default_viewer_executable_edit,
            default_executable=SettingsManager.DEFAULT_DEFAULT_VIEWER_EXECUTABLE,
        )
        self._add_row(
            section=operations_group,
            key="default_viewer_executable",
            title="Default Viewer",
            description="Default executable used for view operations. Empty means use Default Editor.",
            terms="default viewer executable open view fallback editor",
            controls=[default_viewer_controls],
        )

        self.context_code_editor_executable_edit = QLineEdit(self)
        self.context_code_editor_args_edit = QLineEdit(self)
        context_code_editor_controls = self._build_command_controls(
            executable_edit=self.context_code_editor_executable_edit,
            args_edit=self.context_code_editor_args_edit,
            default_executable=SettingsManager.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH,
            default_args=SettingsManager.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE,
            discover_default_executable="",
            enable_find=False,
        )
        self._add_row(
            section=operations_group,
            key="context_code_editor_tool",
            title="Context Tool: Code Editor",
            description="Executable and args template for context actions using code editor.",
            terms="context tool code editor executable args template",
            controls=[context_code_editor_controls],
        )

        self.context_git_gui_executable_edit = QLineEdit(self)
        self.context_git_gui_args_edit = QLineEdit(self)
        context_git_gui_controls = self._build_command_controls(
            executable_edit=self.context_git_gui_executable_edit,
            args_edit=self.context_git_gui_args_edit,
            default_executable=SettingsManager.DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH,
            default_args=SettingsManager.DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE,
            discover_default_executable="",
            enable_find=False,
        )
        self._add_row(
            section=operations_group,
            key="context_git_gui_tool",
            title="Context Tool: Git GUI",
            description="Executable and args template for context actions using Git GUI.",
            terms="context tool git gui executable args template",
            controls=[context_git_gui_controls],
        )

        self.file_open_overrides_table = QTableWidget(0, 3, self)
        self.file_open_overrides_table.setHorizontalHeaderLabels(
            ["Extension", "Editor", "Viewer"]
        )
        self.file_open_overrides_table.horizontalHeader().setStretchLastSection(False)
        self.file_open_overrides_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.file_open_overrides_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.file_open_overrides_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.file_open_overrides_table.itemChanged.connect(
            self._on_file_open_overrides_item_changed
        )
        self.file_open_overrides_table.setMinimumHeight(150)
        overrides_controls = self._build_file_open_overrides_controls()
        self._add_row(
            section=operations_group,
            key="file_open_overrides",
            title="Per-Extension Open Overrides",
            description="Override editor/viewer executables by extension (example: .log, .json, .cmd).",
            terms="extension override editor viewer open file",
            controls=[overrides_controls],
        )

        # Per-backend extended-path toggles are shown alongside each backend command section.
        self.use_extended_paths_robocopy_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_teracopy_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_unstoppable_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_external_copymove_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_cmd_delete_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_powershell_delete_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_rimraf_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        self.use_extended_paths_external_delete_checkbox = QCheckBox(
            r"Use extended paths \\?\... as args",
            self,
        )
        for checkbox in [
            self.use_extended_paths_robocopy_checkbox,
            self.use_extended_paths_teracopy_checkbox,
            self.use_extended_paths_unstoppable_checkbox,
            self.use_extended_paths_external_copymove_checkbox,
            self.use_extended_paths_cmd_delete_checkbox,
            self.use_extended_paths_powershell_delete_checkbox,
            self.use_extended_paths_rimraf_checkbox,
            self.use_extended_paths_external_delete_checkbox,
        ]:
            checkbox.toggled.connect(self._on_controls_changed)

        self.teracopy_executable_edit = QLineEdit(self)
        self.teracopy_args_edit = QLineEdit(self)
        self.teracopy_test_btn = QPushButton("Test", self)
        teracopy_controls = self._build_command_controls(
            executable_edit=self.teracopy_executable_edit,
            args_edit=self.teracopy_args_edit,
            default_executable=SettingsManager.DEFAULT_TERACOPY_EXECUTABLE,
            default_args=SettingsManager.DEFAULT_TERACOPY_ARGS_TEMPLATE,
            discover_default_executable=DEFAULT_TERA_COPY_EXE,
            extended_paths_checkbox=self.use_extended_paths_teracopy_checkbox,
            test_button=self.teracopy_test_btn,
            on_test=lambda: self._test_backend("copy", "teracopy"),
        )
        self._add_row(
            section=operations_group,
            key="teracopy_command",
            title="TeraCopy Command",
            description='Executable and args template. Tokens: {operation} {sources} {target}',
            terms="teracopy executable args template test long path extended",
            controls=[teracopy_controls],
        )

        self.unstoppable_executable_edit = QLineEdit(self)
        self.unstoppable_args_edit = QLineEdit(self)
        self.unstoppable_test_btn = QPushButton("Test", self)
        unstoppable_controls = self._build_command_controls(
            executable_edit=self.unstoppable_executable_edit,
            args_edit=self.unstoppable_args_edit,
            default_executable=SettingsManager.DEFAULT_UNSTOPPABLE_EXECUTABLE,
            default_args=SettingsManager.DEFAULT_UNSTOPPABLE_ARGS_TEMPLATE,
            discover_default_executable=DEFAULT_UNSTOPPABLE_EXE,
            extended_paths_checkbox=self.use_extended_paths_unstoppable_checkbox,
            test_button=self.unstoppable_test_btn,
            on_test=lambda: self._test_backend("copy", "unstoppable"),
        )
        self._add_row(
            section=operations_group,
            key="unstoppable_command",
            title="Unstoppable Copier Command",
            description='Executable and args template. Tokens: {operation} {sources} {target}',
            terms="unstoppable copier executable args template test long path extended",
            controls=[unstoppable_controls],
        )

        self.generic_copymove_executable_edit = QLineEdit(self)
        self.generic_copymove_args_edit = QLineEdit(self)
        self.generic_copymove_test_btn = QPushButton("Test", self)
        generic_copymove_controls = self._build_command_controls(
            executable_edit=self.generic_copymove_executable_edit,
            args_edit=self.generic_copymove_args_edit,
            default_executable=SettingsManager.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE,
            default_args=SettingsManager.DEFAULT_GENERIC_COPYMOVE_ARGS_TEMPLATE,
            discover_default_executable="",
            enable_find=False,
            extended_paths_checkbox=self.use_extended_paths_external_copymove_checkbox,
            test_button=self.generic_copymove_test_btn,
            on_test=lambda: self._test_backend("copy", "external_copymove"),
        )
        self._add_row(
            section=operations_group,
            key="generic_copymove_command",
            title="Generic Copy/Move Command",
            description='Executable and args template. Tokens: {operation} {sources} {target}',
            terms="external generic copy move executable args template test long path extended",
            controls=[generic_copymove_controls],
        )

        self.generic_delete_executable_edit = QLineEdit(self)
        self.generic_delete_args_edit = QLineEdit(self)
        self.generic_delete_test_btn = QPushButton("Test", self)
        generic_delete_controls = self._build_command_controls(
            executable_edit=self.generic_delete_executable_edit,
            args_edit=self.generic_delete_args_edit,
            default_executable=SettingsManager.DEFAULT_GENERIC_DELETE_EXECUTABLE,
            default_args=SettingsManager.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE,
            discover_default_executable="",
            enable_find=False,
            extended_paths_checkbox=self.use_extended_paths_external_delete_checkbox,
            test_button=self.generic_delete_test_btn,
            on_test=lambda: self._test_backend("delete", "external_delete"),
        )
        self._add_row(
            section=operations_group,
            key="generic_delete_command",
            title="Generic Delete Command",
            description='Executable and args template. Tokens: {operation} {sources}',
            terms="external generic delete executable args template test long path extended",
            controls=[generic_delete_controls],
        )

        self.robocopy_copy_args_edit = QLineEdit(self)
        self.robocopy_copy_args_edit.textChanged.connect(self._on_controls_changed)
        self.robocopy_move_args_edit = QLineEdit(self)
        self.robocopy_move_args_edit.textChanged.connect(self._on_controls_changed)
        self.robocopy_test_btn = QPushButton("Test", self)
        robocopy_args_controls = self._build_robocopy_controls(
            first_label="Copy Args",
            first_edit=self.robocopy_copy_args_edit,
            second_label="Move Args",
            second_edit=self.robocopy_move_args_edit,
            extended_paths_checkbox=self.use_extended_paths_robocopy_checkbox,
            test_button=self.robocopy_test_btn,
        )
        self._add_row(
            section=operations_group,
            key="robocopy_args",
            title="Robocopy Args",
            description="Copy args and move args for robocopy backend.",
            terms="robocopy copy args move args test long path extended",
            controls=[robocopy_args_controls],
        )

        self.cmd_delete_args_edit = QLineEdit(self)
        self.cmd_delete_args_edit.textChanged.connect(self._on_controls_changed)
        self.powershell_delete_args_edit = QLineEdit(self)
        self.powershell_delete_args_edit.textChanged.connect(self._on_controls_changed)
        self.cmd_delete_test_btn = QPushButton("Test cmd", self)
        self.powershell_delete_test_btn = QPushButton("Test PowerShell", self)
        delete_shell_args_controls = self._build_delete_shell_controls(
            first_label="cmd Args",
            first_edit=self.cmd_delete_args_edit,
            second_label="PowerShell Args",
            second_edit=self.powershell_delete_args_edit,
            cmd_extended_paths_checkbox=self.use_extended_paths_cmd_delete_checkbox,
            powershell_extended_paths_checkbox=self.use_extended_paths_powershell_delete_checkbox,
            cmd_test_button=self.cmd_delete_test_btn,
            powershell_test_button=self.powershell_delete_test_btn,
        )
        self._add_row(
            section=operations_group,
            key="delete_shell_args",
            title="Shell Delete Args",
            description="Args for cmd delete and PowerShell delete backends.",
            terms="delete cmd powershell args test long path extended",
            controls=[delete_shell_args_controls],
        )

        self.rimraf_executable_edit = QLineEdit(self)
        self.rimraf_args_edit = QLineEdit(self)
        self.rimraf_test_btn = QPushButton("Test", self)
        rimraf_controls = self._build_command_controls(
            executable_edit=self.rimraf_executable_edit,
            args_edit=self.rimraf_args_edit,
            default_executable=SettingsManager.DEFAULT_RIMRAF_EXECUTABLE,
            default_args=SettingsManager.DEFAULT_RIMRAF_ARGS_TEMPLATE,
            discover_default_executable=DEFAULT_RIMRAF_EXE,
            extended_paths_checkbox=self.use_extended_paths_rimraf_checkbox,
            test_button=self.rimraf_test_btn,
            on_test=lambda: self._test_backend("delete", "rimraf"),
        )
        self._add_row(
            section=operations_group,
            key="rimraf_command",
            title="rimraf Command",
            description='Executable and extra args. Tokens: {sources}',
            terms="rimraf executable args delete test long path extended",
            controls=[rimraf_controls],
        )

        self.resolved_cmd_path_label = QLabel(self)
        self.resolved_robocopy_path_label = QLabel(self)
        self._add_row(
            section=operations_group,
            key="resolved_system_paths",
            title="Resolved System Commands",
            description="Runtime resolved command paths for shell and robocopy.",
            terms="comspec cmd robocopy windir resolved path",
            controls=[self.resolved_cmd_path_label, self.resolved_robocopy_path_label],
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
        item = QTreeWidgetItem([title])
        item.setData(0, Qt.ItemDataRole.UserRole, key)
        self._section_tree.addTopLevelItem(item)
        self._section_tree_items[key] = item
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
            if isinstance(control, QLineEdit):
                control.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )
            controls_layout.addWidget(control)
        controls_host.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
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

    def _build_command_controls(
        self,
        *,
        executable_edit: QLineEdit,
        args_edit: QLineEdit,
        default_executable: str,
        default_args: str,
        discover_default_executable: str,
        enable_find: bool = True,
        extended_paths_checkbox: QCheckBox | None = None,
        test_button: QPushButton | None = None,
        on_test: Callable[[], None] | None = None,
    ) -> QWidget:
        return control_builders.build_command_controls(
            self,
            executable_edit=executable_edit,
            args_edit=args_edit,
            default_executable=default_executable,
            default_args=default_args,
            discover_default_executable=discover_default_executable,
            enable_find=enable_find,
            extended_paths_checkbox=extended_paths_checkbox,
            test_button=test_button,
            on_test=on_test,
        )

    def _build_path_controls(
        self,
        *,
        executable_edit: QLineEdit,
        default_executable: str,
    ) -> QWidget:
        return control_builders.build_path_controls(
            self,
            executable_edit=executable_edit,
            default_executable=default_executable,
        )

    def _build_dual_text_controls(
        self,
        *,
        first_label: str,
        first_edit: QLineEdit,
        second_label: str,
        second_edit: QLineEdit,
    ) -> QWidget:
        return control_builders.build_dual_text_controls(
            self,
            first_label=first_label,
            first_edit=first_edit,
            second_label=second_label,
            second_edit=second_edit,
        )

    def _build_robocopy_controls(
        self,
        *,
        first_label: str,
        first_edit: QLineEdit,
        second_label: str,
        second_edit: QLineEdit,
        extended_paths_checkbox: QCheckBox,
        test_button: QPushButton,
    ) -> QWidget:
        return control_builders.build_robocopy_controls(
            self,
            first_label=first_label,
            first_edit=first_edit,
            second_label=second_label,
            second_edit=second_edit,
            extended_paths_checkbox=extended_paths_checkbox,
            test_button=test_button,
        )

    def _build_delete_shell_controls(
        self,
        *,
        first_label: str,
        first_edit: QLineEdit,
        second_label: str,
        second_edit: QLineEdit,
        cmd_extended_paths_checkbox: QCheckBox,
        powershell_extended_paths_checkbox: QCheckBox,
        cmd_test_button: QPushButton,
        powershell_test_button: QPushButton,
    ) -> QWidget:
        return control_builders.build_delete_shell_controls(
            self,
            first_label=first_label,
            first_edit=first_edit,
            second_label=second_label,
            second_edit=second_edit,
            cmd_extended_paths_checkbox=cmd_extended_paths_checkbox,
            powershell_extended_paths_checkbox=powershell_extended_paths_checkbox,
            cmd_test_button=cmd_test_button,
            powershell_test_button=powershell_test_button,
        )

    def _build_file_open_overrides_controls(self) -> QWidget:
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.file_open_overrides_table, 1)

        actions = QWidget(host)
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.add_override_row_btn = QPushButton("Add", actions)
        self.remove_override_row_btn = QPushButton("Remove", actions)
        self.browse_override_editor_btn = QPushButton("Browse Editor...", actions)
        self.browse_override_viewer_btn = QPushButton("Browse Viewer...", actions)
        self.add_override_row_btn.clicked.connect(self._add_file_open_override_row)
        self.remove_override_row_btn.clicked.connect(self._remove_file_open_override_row)
        self.browse_override_editor_btn.clicked.connect(
            lambda: self._browse_file_open_override_executable(1)
        )
        self.browse_override_viewer_btn.clicked.connect(
            lambda: self._browse_file_open_override_executable(2)
        )
        actions_layout.addWidget(self.add_override_row_btn)
        actions_layout.addWidget(self.remove_override_row_btn)
        actions_layout.addWidget(self.browse_override_editor_btn)
        actions_layout.addWidget(self.browse_override_viewer_btn)
        actions_layout.addStretch(1)
        layout.addWidget(actions)
        return host

    def _add_file_open_override_row(self) -> None:
        row = self.file_open_overrides_table.rowCount()
        self.file_open_overrides_table.insertRow(row)
        self.file_open_overrides_table.setItem(row, 0, QTableWidgetItem(".ext"))
        self.file_open_overrides_table.setItem(row, 1, QTableWidgetItem(""))
        self.file_open_overrides_table.setItem(row, 2, QTableWidgetItem(""))
        self.file_open_overrides_table.selectRow(row)
        self._on_controls_changed()

    def _remove_file_open_override_row(self) -> None:
        current = self.file_open_overrides_table.currentRow()
        if current < 0:
            return
        self.file_open_overrides_table.removeRow(current)
        self._on_controls_changed()

    def _browse_file_open_override_executable(self, column: int) -> None:
        current = self.file_open_overrides_table.currentRow()
        if current < 0:
            return
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable",
            str(Path.home()),
            "Executable Files (*.exe *.cmd *.bat);;All Files (*.*)",
        )
        if not selected:
            return
        item = self.file_open_overrides_table.item(current, column)
        if item is None:
            item = QTableWidgetItem("")
            self.file_open_overrides_table.setItem(current, column, item)
        item.setText(selected)
        self._on_controls_changed()

    def _is_valid_extension(self, text: str) -> bool:
        value = str(text or "").strip()
        if not value:
            return False
        if not value.startswith("."):
            return False
        return len(value) > 1 and " " not in value

    def _normalize_extension(self, text: str) -> str:
        value = str(text or "").strip().lower()
        if not value:
            return ""
        if not value.startswith("."):
            value = f".{value}"
        return value

    def _on_file_open_overrides_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            ext = self._normalize_extension(item.text())
            if item.text() != ext:
                item.setText(ext)
                return
            if self._is_valid_extension(ext):
                item.setBackground(Qt.GlobalColor.transparent)
                item.setToolTip("")
            else:
                item.setBackground(Qt.GlobalColor.red)
                item.setToolTip("Extension must look like .txt")
        self._on_controls_changed()

    def _serialize_file_open_overrides(self) -> str:
        payload: dict[str, dict[str, str]] = {}
        for row in range(self.file_open_overrides_table.rowCount()):
            ext_item = self.file_open_overrides_table.item(row, 0)
            editor_item = self.file_open_overrides_table.item(row, 1)
            viewer_item = self.file_open_overrides_table.item(row, 2)
            ext = self._normalize_extension(ext_item.text() if ext_item else "")
            if not self._is_valid_extension(ext):
                continue
            payload[ext] = {
                "editor": (editor_item.text() if editor_item else "").strip(),
                "viewer": (viewer_item.text() if viewer_item else "").strip(),
            }
        return json.dumps(payload, sort_keys=True)

    def _load_file_open_overrides(self, json_text: str) -> None:
        self.file_open_overrides_table.blockSignals(True)
        try:
            self.file_open_overrides_table.setRowCount(0)
            try:
                raw = json.loads(str(json_text or "{}"))
            except json.JSONDecodeError:
                raw = {}
            if not isinstance(raw, dict):
                return
            for ext in sorted(raw.keys(), key=str.casefold):
                value = raw.get(ext, {})
                if not isinstance(value, dict):
                    continue
                row = self.file_open_overrides_table.rowCount()
                self.file_open_overrides_table.insertRow(row)
                ext_item = QTableWidgetItem(self._normalize_extension(str(ext)))
                editor_item = QTableWidgetItem(str(value.get("editor", "")))
                viewer_item = QTableWidgetItem(str(value.get("viewer", "")))
                self.file_open_overrides_table.setItem(row, 0, ext_item)
                self.file_open_overrides_table.setItem(row, 1, editor_item)
                self.file_open_overrides_table.setItem(row, 2, viewer_item)
                if self._is_valid_extension(ext_item.text()):
                    ext_item.setBackground(Qt.GlobalColor.transparent)
                    ext_item.setToolTip("")
                else:
                    ext_item.setBackground(Qt.GlobalColor.red)
                    ext_item.setToolTip("Extension must look like .txt")
        finally:
            self.file_open_overrides_table.blockSignals(False)

    def _browse_executable(self, edit: QLineEdit) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable",
            str(Path.home()),
            "Executable Files (*.exe *.cmd *.bat);;All Files (*.*)",
        )
        if not selected:
            return
        edit.setText(selected)
        self._on_controls_changed()

    def _find_executable(
        self,
        edit: QLineEdit,
        *,
        default_executable: str,
    ) -> None:
        resolved = discover_single_companion_tool(
            configured=edit.text().strip(),
            default_executable=default_executable,
        )
        edit.setText(resolved)
        self._on_controls_changed()

    def _reset_command_controls(
        self,
        executable_edit: QLineEdit,
        args_edit: QLineEdit,
        *,
        default_executable: str,
        default_args: str,
    ) -> None:
        executable_edit.setText(default_executable)
        args_edit.setText(default_args)
        self._on_controls_changed()

    def _test_backend(self, kind: str, backend_id: str) -> None:
        self._on_controls_changed()
        root = Path(tempfile.gettempdir()) / "many_panelz_explorer_op_tests" / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=True)
        sources, target_dir = self._create_test_paths(root, kind=kind)
        request_kind = "delete" if kind == "delete" else "copy"
        request = OperationRequest(
            kind=request_kind,
            sources=tuple(sources),
            target_dir=target_dir,
            backend_id=backend_id,
            dispatch_mode="run_now_wait",
            conflict_policy=self._working_preferences.default_operation_conflict_policy,
            backend_options={},
            created_by="settings-dialog:test-backend",
        )
        artifacts_dir = root / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifacts = OperationArtifacts(
            job_dir=artifacts_dir,
            metadata_path=artifacts_dir / "job.json",
            log_path=artifacts_dir / "output.log",
        )
        result = execute_operation_request(
            request,
            wait=True,
            preferences=self._operation_execution_preferences_from_working(),
            artifacts=artifacts,
        )
        details = (
            f"Backend: {backend_id}\n"
            f"Status: {result.status}\n"
            f"Message: {result.message}\n"
            f"Processed: {result.processed_count}\n"
            f"Test root: {root}\n"
            f"Artifacts: {artifacts_dir}"
        )
        if result.status in {"succeeded", "dispatched"}:
            QMessageBox.information(self, "Backend Test Result", details)
        else:
            QMessageBox.warning(self, "Backend Test Failed", details)

    def _create_test_paths(self, root: Path, *, kind: str) -> tuple[list[Path], Path | None]:
        if kind in {"copy", "move"}:
            source_root = root / "source"
            source_root.mkdir(parents=True, exist_ok=True)
            sample_file = source_root / "sample-file.txt"
            sample_file.write_text("many-panelz test\n", encoding="utf-8")
            sample_dir = source_root / "sample-dir"
            sample_dir.mkdir(parents=True, exist_ok=True)
            (sample_dir / "nested.txt").write_text("nested\n", encoding="utf-8")
            target_dir = root / "target"
            target_dir.mkdir(parents=True, exist_ok=True)
            return [sample_file, sample_dir], target_dir

        delete_root = root / "delete-source"
        delete_root.mkdir(parents=True, exist_ok=True)
        sample_file = delete_root / "to-delete.txt"
        sample_file.write_text("delete me\n", encoding="utf-8")
        sample_dir = delete_root / "to-delete-dir"
        sample_dir.mkdir(parents=True, exist_ok=True)
        (sample_dir / "nested.txt").write_text("delete nested\n", encoding="utf-8")
        return [sample_file, sample_dir], None

    def _operation_execution_preferences_from_working(self) -> OperationExecutionPreferences:
        preferences = self._working_preferences
        resolved_cmd, resolved_robocopy = resolve_system_command_paths()
        base = OperationExecutionPreferences(
            default_copy_move_backend=preferences.default_copy_move_backend,
            default_delete_backend=preferences.default_delete_backend,
            default_dispatch_mode=preferences.default_operation_dispatch_mode,
            default_conflict_policy=preferences.default_operation_conflict_policy,
            shortcut_behavior=preferences.operation_shortcut_behavior,
            queue_view_mode=preferences.operation_queue_view_mode,
            default_editor_executable=preferences.default_editor_executable,
            default_viewer_executable=preferences.default_viewer_executable,
            file_open_overrides_json=preferences.file_open_overrides_json,
            use_extended_paths_robocopy=preferences.use_extended_paths_robocopy,
            use_extended_paths_teracopy=preferences.use_extended_paths_teracopy,
            use_extended_paths_unstoppable=preferences.use_extended_paths_unstoppable,
            use_extended_paths_external_copymove=preferences.use_extended_paths_external_copymove,
            use_extended_paths_cmd_delete=preferences.use_extended_paths_cmd_delete,
            use_extended_paths_powershell_delete=preferences.use_extended_paths_powershell_delete,
            use_extended_paths_rimraf=preferences.use_extended_paths_rimraf,
            use_extended_paths_external_delete=preferences.use_extended_paths_external_delete,
            script_editor_executable=preferences.default_editor_executable,
            teracopy_executable=preferences.teracopy_executable,
            teracopy_args_template=preferences.teracopy_args_template,
            unstoppable_executable=preferences.unstoppable_executable,
            unstoppable_args_template=preferences.unstoppable_args_template,
            generic_copymove_executable=preferences.generic_copymove_executable,
            generic_copymove_args_template=preferences.generic_copymove_args_template,
            generic_delete_executable=preferences.generic_delete_executable,
            generic_delete_args_template=preferences.generic_delete_args_template,
            robocopy_copy_args=preferences.robocopy_copy_args,
            robocopy_move_args=preferences.robocopy_move_args,
            cmd_delete_args=preferences.cmd_delete_args,
            powershell_delete_args=preferences.powershell_delete_args,
            rimraf_executable=preferences.rimraf_executable,
            rimraf_args_template=preferences.rimraf_args_template,
            resolved_cmd_path=resolved_cmd,
            resolved_robocopy_path=resolved_robocopy,
        )
        return resolve_companion_tool_paths(base)

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

    def _new_byte_format_mode_combo(self) -> QComboBox:
        combo = QComboBox(self)
        combo.addItem("Human Readable", "human_readable")
        combo.addItem("Always MB", "always_mb")
        combo.addItem("Always MiB", "always_mib")
        combo.addItem("Bytes", "bytes")
        combo.addItem("Custom", "custom")
        combo.currentIndexChanged.connect(self._on_byte_format_mode_changed)
        return combo

    def _on_byte_format_mode_changed(self, _index: int) -> None:
        self._sync_byte_format_controls()
        self._on_controls_changed()

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

    def _sync_byte_format_controls(self) -> None:
        self.file_list_byte_custom_template_edit.setEnabled(
            str(self.file_list_byte_format_mode_combo.currentData()) == "custom"
        )
        self.status_bar_byte_custom_template_edit.setEnabled(
            str(self.status_bar_byte_format_mode_combo.currentData()) == "custom"
        )
        self.properties_byte_custom_template_edit.setEnabled(
            str(self.properties_byte_format_mode_combo.currentData()) == "custom"
        )

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
            self.context_scan_cap_spin.setValue(
                preferences.context_immediate_child_scan_cap
            )
            self.show_hidden_checkbox.setChecked(preferences.show_hidden_default)
            self.show_root_dropdown_checkbox.setChecked(preferences.show_root_dropdown)
            self._set_combo_value(
                self.column_width_auto_align_mode_combo,
                preferences.column_width_auto_align_mode,
            )
            self.show_refresh_button_checkbox.setChecked(
                preferences.show_refresh_button
            )
            self.show_root_buttons_checkbox.setChecked(preferences.show_root_buttons)
            self.show_address_bar_checkbox.setChecked(preferences.show_address_bar)
            self.show_navigation_buttons_checkbox.setChecked(
                preferences.show_navigation_buttons
            )
            self.show_storage_overview_status_row_checkbox.setChecked(
                preferences.show_storage_overview_status_row
            )
            self.byte_thousands_separator_edit.setText(
                preferences.byte_thousands_separator
            )
            self.byte_decimal_separator_edit.setText(preferences.byte_decimal_separator)
            self._set_combo_value(
                self.file_list_byte_format_mode_combo,
                preferences.file_list_byte_format_mode,
            )
            self.file_list_byte_custom_template_edit.setText(
                preferences.file_list_byte_custom_template
            )
            self._set_combo_value(
                self.status_bar_byte_format_mode_combo,
                preferences.status_bar_byte_format_mode,
            )
            self.status_bar_byte_custom_template_edit.setText(
                preferences.status_bar_byte_custom_template
            )
            self._set_combo_value(
                self.properties_byte_format_mode_combo,
                preferences.properties_byte_format_mode,
            )
            self.properties_byte_custom_template_edit.setText(
                preferences.properties_byte_custom_template
            )
            self._set_combo_value(
                self.default_copy_move_backend_combo,
                preferences.default_copy_move_backend,
            )
            self._set_combo_value(
                self.default_delete_backend_combo,
                preferences.default_delete_backend,
            )
            self._set_combo_value(
                self.default_dispatch_mode_combo,
                preferences.default_operation_dispatch_mode,
            )
            self._set_combo_value(
                self.default_conflict_policy_combo,
                preferences.default_operation_conflict_policy,
            )
            self._set_combo_value(
                self.operation_shortcut_behavior_combo,
                preferences.operation_shortcut_behavior,
            )
            self._set_combo_value(
                self.operation_queue_view_mode_combo,
                preferences.operation_queue_view_mode,
            )
            self.default_editor_executable_edit.setText(
                preferences.default_editor_executable
            )
            self.default_viewer_executable_edit.setText(
                preferences.default_viewer_executable
            )
            self.context_code_editor_executable_edit.setText(
                preferences.context_tool_code_editor_exe_path
            )
            self.context_code_editor_args_edit.setText(
                preferences.context_tool_code_editor_args_template
            )
            self.context_git_gui_executable_edit.setText(
                preferences.context_tool_git_gui_exe_path
            )
            self.context_git_gui_args_edit.setText(
                preferences.context_tool_git_gui_args_template
            )
            self._load_file_open_overrides(preferences.file_open_overrides_json)
            self.use_extended_paths_robocopy_checkbox.setChecked(
                preferences.use_extended_paths_robocopy
            )
            self.use_extended_paths_teracopy_checkbox.setChecked(
                preferences.use_extended_paths_teracopy
            )
            self.use_extended_paths_unstoppable_checkbox.setChecked(
                preferences.use_extended_paths_unstoppable
            )
            self.use_extended_paths_external_copymove_checkbox.setChecked(
                preferences.use_extended_paths_external_copymove
            )
            self.use_extended_paths_cmd_delete_checkbox.setChecked(
                preferences.use_extended_paths_cmd_delete
            )
            self.use_extended_paths_powershell_delete_checkbox.setChecked(
                preferences.use_extended_paths_powershell_delete
            )
            self.use_extended_paths_rimraf_checkbox.setChecked(
                preferences.use_extended_paths_rimraf
            )
            self.use_extended_paths_external_delete_checkbox.setChecked(
                preferences.use_extended_paths_external_delete
            )
            self.teracopy_executable_edit.setText(preferences.teracopy_executable)
            self.teracopy_args_edit.setText(preferences.teracopy_args_template)
            self.unstoppable_executable_edit.setText(preferences.unstoppable_executable)
            self.unstoppable_args_edit.setText(preferences.unstoppable_args_template)
            self.generic_copymove_executable_edit.setText(
                preferences.generic_copymove_executable
            )
            self.generic_copymove_args_edit.setText(
                preferences.generic_copymove_args_template
            )
            self.generic_delete_executable_edit.setText(
                preferences.generic_delete_executable
            )
            self.generic_delete_args_edit.setText(
                preferences.generic_delete_args_template
            )
            self.robocopy_copy_args_edit.setText(preferences.robocopy_copy_args)
            self.robocopy_move_args_edit.setText(preferences.robocopy_move_args)
            self.cmd_delete_args_edit.setText(preferences.cmd_delete_args)
            self.powershell_delete_args_edit.setText(preferences.powershell_delete_args)
            self.rimraf_executable_edit.setText(preferences.rimraf_executable)
            self.rimraf_args_edit.setText(preferences.rimraf_args_template)
            resolved_cmd, resolved_robocopy = resolve_system_command_paths()
            self.resolved_cmd_path_label.setText(f"ComSpec: {resolved_cmd}")
            self.resolved_robocopy_path_label.setText(
                f"Robocopy: {resolved_robocopy}"
            )
            self.resolved_cmd_path_label.setToolTip(resolved_cmd)
            self.resolved_robocopy_path_label.setToolTip(resolved_robocopy)
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
            self._sync_byte_format_controls()
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
            column_width_auto_align_mode=str(
                self.column_width_auto_align_mode_combo.currentData()
            ),
            context_immediate_child_scan_cap=self.context_scan_cap_spin.value(),
            show_refresh_button=self.show_refresh_button_checkbox.isChecked(),
            show_root_buttons=self.show_root_buttons_checkbox.isChecked(),
            show_address_bar=self.show_address_bar_checkbox.isChecked(),
            show_navigation_buttons=self.show_navigation_buttons_checkbox.isChecked(),
            show_storage_overview_status_row=self.show_storage_overview_status_row_checkbox.isChecked(),
            byte_thousands_separator=self.byte_thousands_separator_edit.text(),
            byte_decimal_separator=self.byte_decimal_separator_edit.text(),
            file_list_byte_format_mode=str(
                self.file_list_byte_format_mode_combo.currentData()
            ),
            file_list_byte_custom_template=self.file_list_byte_custom_template_edit.text(),
            status_bar_byte_format_mode=str(
                self.status_bar_byte_format_mode_combo.currentData()
            ),
            status_bar_byte_custom_template=self.status_bar_byte_custom_template_edit.text(),
            properties_byte_format_mode=str(
                self.properties_byte_format_mode_combo.currentData()
            ),
            properties_byte_custom_template=self.properties_byte_custom_template_edit.text(),
            default_copy_move_backend=str(
                self.default_copy_move_backend_combo.currentData()
            ),
            default_delete_backend=str(self.default_delete_backend_combo.currentData()),
            default_operation_dispatch_mode=str(
                self.default_dispatch_mode_combo.currentData()
            ),
            default_operation_conflict_policy=str(
                self.default_conflict_policy_combo.currentData()
            ),
            operation_shortcut_behavior=str(
                self.operation_shortcut_behavior_combo.currentData()
            ),
            operation_queue_view_mode=str(
                self.operation_queue_view_mode_combo.currentData()
            ),
            default_editor_executable=self.default_editor_executable_edit.text().strip(),
            default_viewer_executable=self.default_viewer_executable_edit.text().strip(),
            context_tool_code_editor_exe_path=self.context_code_editor_executable_edit.text().strip(),
            context_tool_code_editor_args_template=self.context_code_editor_args_edit.text().strip(),
            context_tool_git_gui_exe_path=self.context_git_gui_executable_edit.text().strip(),
            context_tool_git_gui_args_template=self.context_git_gui_args_edit.text().strip(),
            file_open_overrides_json=self._serialize_file_open_overrides(),
            use_extended_paths_robocopy=self.use_extended_paths_robocopy_checkbox.isChecked(),
            use_extended_paths_teracopy=self.use_extended_paths_teracopy_checkbox.isChecked(),
            use_extended_paths_unstoppable=self.use_extended_paths_unstoppable_checkbox.isChecked(),
            use_extended_paths_external_copymove=self.use_extended_paths_external_copymove_checkbox.isChecked(),
            use_extended_paths_cmd_delete=self.use_extended_paths_cmd_delete_checkbox.isChecked(),
            use_extended_paths_powershell_delete=self.use_extended_paths_powershell_delete_checkbox.isChecked(),
            use_extended_paths_rimraf=self.use_extended_paths_rimraf_checkbox.isChecked(),
            use_extended_paths_external_delete=self.use_extended_paths_external_delete_checkbox.isChecked(),
            script_editor_executable=self.default_editor_executable_edit.text().strip(),
            teracopy_executable=self.teracopy_executable_edit.text().strip(),
            teracopy_args_template=self.teracopy_args_edit.text().strip(),
            unstoppable_executable=self.unstoppable_executable_edit.text().strip(),
            unstoppable_args_template=self.unstoppable_args_edit.text().strip(),
            generic_copymove_executable=self.generic_copymove_executable_edit.text().strip(),
            generic_copymove_args_template=self.generic_copymove_args_edit.text().strip(),
            generic_delete_executable=self.generic_delete_executable_edit.text().strip(),
            generic_delete_args_template=self.generic_delete_args_edit.text().strip(),
            robocopy_copy_args=self.robocopy_copy_args_edit.text().strip(),
            robocopy_move_args=self.robocopy_move_args_edit.text().strip(),
            cmd_delete_args=self.cmd_delete_args_edit.text().strip(),
            powershell_delete_args=self.powershell_delete_args_edit.text().strip(),
            rimraf_executable=self.rimraf_executable_edit.text().strip(),
            rimraf_args_template=self.rimraf_args_edit.text().strip(),
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
        self.byte_thousands_separator_edit.setText(
            SettingsManager.DEFAULT_BYTES_THOUSANDS_SEPARATOR
        )
        self.byte_decimal_separator_edit.setText(
            SettingsManager.DEFAULT_BYTES_DECIMAL_SEPARATOR
        )
        self._set_combo_value(
            self.file_list_byte_format_mode_combo,
            SettingsManager.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
        )
        self.file_list_byte_custom_template_edit.setText(
            SettingsManager.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE
        )
        self._set_combo_value(
            self.status_bar_byte_format_mode_combo,
            SettingsManager.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
        )
        self.status_bar_byte_custom_template_edit.setText(
            SettingsManager.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE
        )
        self._set_combo_value(
            self.properties_byte_format_mode_combo,
            SettingsManager.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
        )
        self.properties_byte_custom_template_edit.setText(
            SettingsManager.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE
        )
        self._sync_font_override_controls()
        self._sync_byte_format_controls()
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
        for key, section in self._sections.items():
            section_match = bool(query) and query in section.terms
            section_visible_rows = 0
            for row in section.rows:
                row_visible = (not query) or section_match or (query in row.terms)
                row.widget.setVisible(row_visible)
                if row_visible:
                    section_visible_rows += 1
            section_visible = section_visible_rows > 0
            section.group.setVisible(section_visible)
            tree_item = self._section_tree_items.get(key)
            if tree_item is not None:
                tree_item.setHidden(not section_visible)
            visible_rows += section_visible_rows
        self._no_matches_label.setVisible(bool(query) and visible_rows == 0)
        self._ensure_visible_tree_selection()

    def _ensure_visible_tree_selection(self) -> None:
        current = self._section_tree.currentItem()
        if current is not None and not current.isHidden():
            return
        for index in range(self._section_tree.topLevelItemCount()):
            item = self._section_tree.topLevelItem(index)
            if item is None or item.isHidden():
                continue
            self._tree_sync_in_progress = True
            try:
                self._section_tree.setCurrentItem(item)
            finally:
                self._tree_sync_in_progress = False
            self._scroll_to_section(str(item.data(0, Qt.ItemDataRole.UserRole)))
            return

    def _on_section_tree_changed(
        self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None
    ) -> None:
        if self._tree_sync_in_progress or current is None:
            return
        if current.isHidden():
            return
        self._scroll_to_section(str(current.data(0, Qt.ItemDataRole.UserRole)))

    def _scroll_to_section(self, section_key: str) -> None:
        section = self._sections.get(str(section_key))
        if section is None or not section.group.isVisible():
            return
        self._scroll.ensureWidgetVisible(section.group, 0, 16)

    def _assign_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        widget.setObjectName(widget_naming.object_name_for_id(widget_id))
        widget.setProperty("widget_id", widget_id)
        widget.setProperty("widget_alias", alias)
