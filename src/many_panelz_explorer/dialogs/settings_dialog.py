"""Preferences dialog for UI and operation backend settings."""

from __future__ import annotations

import json
import tempfile
import uuid
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from threep_commons.qt.widget_identity import assign_widget_identity

from .._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    resolve_copy_move_backend_args,
)
from .._operations.discovery import (
    discover_single_companion_tool,
    resolve_companion_tool_paths,
    resolve_system_command_paths,
)
from .._operations.executors import execute_operation_request
from .._operations.types import (
    OperationArtifacts,
    OperationExecutionPreferences,
    OperationKind,
    OperationRequest,
)
from .._settings import normalize as settings_normalize
from .settings import (
    FontSizeSpinBox,
    SectionEntry,
    SubsectionEntry,
    backend_cards_external,
    backend_cards_transfer,
    backend_state,
    build_sections,
    control_builders,
    open_overrides_controls,
    preferences_flow,
    preferences_sync,
    tree_navigation,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .._settings.models import UiPreferences
    from ..app_controller import AppController


def _string_object_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, object] = {}
    mapping = cast("dict[object, object]", value)
    for key, item in mapping.items():
        normalized[str(key)] = item
    return normalized


class SettingsDialog(QDialog):
    """Edit persisted UI, panel, and operation preferences."""

    LIVE_PREVIEW_DEBOUNCE_MS = 140
    RESETTABLE_FIELDS_BY_SECTION: ClassVar[dict[str, tuple[str, ...]]] = {
        "appearance": (
            "active_panel_tint_color_hex",
            "active_panel_tint_intensity_percent",
            "target_panel_tint_color_hex",
            "target_panel_tint_intensity_percent",
            "app_font_family",
            "app_font_size_pt",
            "file_list_use_app_font",
            "file_list_font_family",
            "file_list_font_size_pt",
            "navigation_use_app_font",
            "navigation_font_family",
            "navigation_font_size_pt",
        ),
        "behavior": (
            "new_context_mode",
            "context_immediate_child_scan_cap",
        ),
        "panels": (
            "show_hidden_default",
            "show_root_dropdown",
            "show_refresh_button",
            "show_root_buttons",
            "show_address_bar",
            "show_navigation_buttons",
            "show_storage_overview_status_row",
            "column_width_auto_align_mode",
            "byte_thousands_separator",
            "byte_decimal_separator",
            "file_list_byte_format_mode",
            "file_list_byte_custom_template",
            "status_bar_byte_format_mode",
            "status_bar_byte_custom_template",
            "status_bar_storage_label_template",
            "properties_byte_format_mode",
            "properties_byte_custom_template",
        ),
        "operations": (
            "default_copy_move_backend",
            "default_delete_backend",
            "default_operation_dispatch_mode",
            "default_operation_conflict_policy",
            "operation_shortcut_behavior",
            "operation_queue_view_mode",
            "default_editor_executable",
            "default_viewer_executable",
            "context_tool_code_editor_exe_path",
            "context_tool_code_editor_args_template",
            "context_tool_git_gui_exe_path",
            "context_tool_git_gui_args_template",
            "file_open_overrides_json",
            "teracopy_executable",
            "use_extended_paths_teracopy",
            "unstoppable_executable",
            "use_extended_paths_unstoppable",
            "generic_copymove_executable",
            "use_extended_paths_external_copymove",
            "generic_delete_executable",
            "generic_delete_args_template",
            "use_extended_paths_external_delete",
            "rimraf_executable",
            "rimraf_args_template",
            "use_extended_paths_rimraf",
            "robocopy_structured_options",
            "teracopy_structured_options",
            "unstoppable_structured_options",
            "external_copymove_structured_options",
            "use_extended_paths_robocopy",
            "cmd_delete_args",
            "powershell_delete_args",
            "use_extended_paths_cmd_delete",
            "use_extended_paths_powershell_delete",
        ),
    }

    if TYPE_CHECKING:
        add_override_row_btn: QPushButton
        active_color_button: QPushButton
        active_color_preview: QLabel
        active_intensity_slider: QSlider
        active_intensity_value: QLabel
        app_font_family_combo: QComboBox
        app_font_size_spin: FontSizeSpinBox
        byte_decimal_separator_edit: QLineEdit
        byte_thousands_separator_edit: QLineEdit
        browse_override_editor_btn: QPushButton
        browse_override_viewer_btn: QPushButton
        cmd_delete_args_edit: QLineEdit
        cmd_delete_test_btn: QPushButton
        column_width_auto_align_mode_combo: QComboBox
        context_code_editor_args_edit: QLineEdit
        context_code_editor_executable_edit: QLineEdit
        context_git_gui_args_edit: QLineEdit
        context_git_gui_executable_edit: QLineEdit
        context_scan_cap_spin: QSpinBox
        default_conflict_policy_combo: QComboBox
        default_copy_move_backend_combo: QComboBox
        default_delete_backend_combo: QComboBox
        default_dispatch_mode_combo: QComboBox
        default_editor_executable_edit: QLineEdit
        default_viewer_executable_edit: QLineEdit
        external_copymove_preview_label: QLabel
        external_copymove_reset_backend_btn: QPushButton
        external_copymove_struct_extra_args_edit: QLineEdit
        external_copymove_struct_include_operation_checkbox: QCheckBox
        external_copymove_struct_include_sources_checkbox: QCheckBox
        external_copymove_struct_include_target_checkbox: QCheckBox
        file_list_byte_custom_template_edit: QLineEdit
        file_list_byte_format_mode_combo: QComboBox
        file_list_font_family_combo: QComboBox
        file_list_font_size_spin: FontSizeSpinBox
        file_list_use_app_font_checkbox: QCheckBox
        file_open_overrides_table: QTableWidget
        generic_copymove_executable_edit: QLineEdit
        generic_copymove_test_btn: QPushButton
        generic_delete_args_edit: QLineEdit
        generic_delete_executable_edit: QLineEdit
        generic_delete_test_btn: QPushButton
        navigation_font_family_combo: QComboBox
        navigation_font_size_spin: FontSizeSpinBox
        navigation_use_app_font_checkbox: QCheckBox
        new_context_combo: QComboBox
        operation_queue_view_mode_combo: QComboBox
        operation_shortcut_behavior_combo: QComboBox
        powershell_delete_args_edit: QLineEdit
        powershell_delete_test_btn: QPushButton
        properties_byte_custom_template_edit: QLineEdit
        properties_byte_format_mode_combo: QComboBox
        remove_override_row_btn: QPushButton
        resolved_cmd_path_label: QLabel
        resolved_robocopy_path_label: QLabel
        rimraf_args_edit: QLineEdit
        rimraf_executable_edit: QLineEdit
        rimraf_test_btn: QPushButton
        robocopy_preview_label: QLabel
        robocopy_reset_backend_btn: QPushButton
        robocopy_struct_backup_checkbox: QCheckBox
        robocopy_struct_extra_args_edit: QLineEdit
        robocopy_struct_include_subdirs_checkbox: QCheckBox
        robocopy_struct_list_only_checkbox: QCheckBox
        robocopy_struct_mirror_checkbox: QCheckBox
        robocopy_struct_move_checkbox: QCheckBox
        robocopy_struct_multithread_checkbox: QCheckBox
        robocopy_struct_multithread_spin: QSpinBox
        robocopy_struct_quiet_checkbox: QCheckBox
        robocopy_struct_restartable_checkbox: QCheckBox
        robocopy_struct_retry_spin: QSpinBox
        robocopy_struct_wait_spin: QSpinBox
        robocopy_test_btn: QPushButton
        show_address_bar_checkbox: QCheckBox
        show_hidden_checkbox: QCheckBox
        show_navigation_buttons_checkbox: QCheckBox
        show_refresh_button_checkbox: QCheckBox
        show_root_buttons_checkbox: QCheckBox
        show_root_dropdown_checkbox: QCheckBox
        show_storage_overview_status_row_checkbox: QCheckBox
        status_bar_byte_custom_template_edit: QLineEdit
        status_bar_byte_format_mode_combo: QComboBox
        status_bar_storage_label_template_edit: QLineEdit
        target_color_button: QPushButton
        target_color_preview: QLabel
        target_intensity_slider: QSlider
        target_intensity_value: QLabel
        teracopy_executable_edit: QLineEdit
        teracopy_preview_label: QLabel
        teracopy_reset_backend_btn: QPushButton
        teracopy_struct_close_checkbox: QCheckBox
        teracopy_struct_conflict_combo: QComboBox
        teracopy_struct_extra_args_edit: QLineEdit
        teracopy_struct_keep_open_checkbox: QCheckBox
        teracopy_struct_no_sound_checkbox: QCheckBox
        teracopy_struct_verify_checkbox: QCheckBox
        teracopy_test_btn: QPushButton
        unstoppable_executable_edit: QLineEdit
        unstoppable_preview_label: QLabel
        unstoppable_reset_backend_btn: QPushButton
        unstoppable_struct_copy_empty_folders_checkbox: QCheckBox
        unstoppable_struct_copy_newer_checkbox: QCheckBox
        unstoppable_struct_defaults_checkbox: QCheckBox
        unstoppable_struct_eta_checkbox: QCheckBox
        unstoppable_struct_extra_args_edit: QLineEdit
        unstoppable_struct_include_subdirs_checkbox: QCheckBox
        unstoppable_struct_keep_attributes_checkbox: QCheckBox
        unstoppable_struct_keep_owner_checkbox: QCheckBox
        unstoppable_struct_keep_time_checkbox: QCheckBox
        unstoppable_struct_overwrite_checkbox: QCheckBox
        unstoppable_struct_overwrite_readonly_checkbox: QCheckBox
        unstoppable_struct_power_down_checkbox: QCheckBox
        unstoppable_struct_resume_checkbox: QCheckBox
        unstoppable_struct_skip_damaged_checkbox: QCheckBox
        unstoppable_struct_undamaged_first_checkbox: QCheckBox
        unstoppable_test_btn: QPushButton
        use_extended_paths_cmd_delete_checkbox: QCheckBox
        use_extended_paths_external_copymove_checkbox: QCheckBox
        use_extended_paths_external_delete_checkbox: QCheckBox
        use_extended_paths_powershell_delete_checkbox: QCheckBox
        use_extended_paths_rimraf_checkbox: QCheckBox
        use_extended_paths_robocopy_checkbox: QCheckBox
        use_extended_paths_teracopy_checkbox: QCheckBox
        use_extended_paths_unstoppable_checkbox: QCheckBox
        row_widgets_by_key: dict[str, QWidget]
        row_subsection_keys: dict[str, str]
        scroll_host: QWidget
        scroll_layout: QVBoxLayout
        section_tree: QTreeWidget
        section_tree_items: dict[str, QTreeWidgetItem]
        sections: dict[str, SectionEntry]
        subsection_tree_items: dict[str, QTreeWidgetItem]
        subsections: dict[str, SubsectionEntry]

    def __init__(
        self, controller: AppController, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self._initialize_dialog_state()
        self._configure_dialog_window()
        root = self._build_dialog_layout()
        build_sections(self)
        self._load_preferences_into_controls(self._working_preferences)
        self.apply_search_filter("")
        tree_navigation.restore_last_tree_selection(self)
        self._build_live_preview_and_buttons(root)

    def _initialize_dialog_state(self) -> None:
        """Initialize dialog state before building widgets."""

        controller = self.controller
        self.controller = controller
        self._committed_preferences = controller.current_ui_preferences()
        self._working_preferences = replace(self._committed_preferences)
        self._loading_ui = False
        self._pending_live_preview = False
        self._rows_by_key: dict[str, QWidget] = {}
        self._sections: dict[str, SectionEntry] = {}
        self._subsections: dict[str, SubsectionEntry] = {}
        self._section_tree_items: dict[str, QTreeWidgetItem] = {}
        self._subsection_tree_items: dict[str, QTreeWidgetItem] = {}
        self._row_subsection_keys: dict[str, str] = {}
        self.row_widgets_by_key = self._rows_by_key
        self.sections = self._sections
        self.subsections = self._subsections
        self.section_tree_items = self._section_tree_items
        self.subsection_tree_items = self._subsection_tree_items
        self.row_subsection_keys = self._row_subsection_keys
        self._active_subsection_key = ""
        self._tree_sync_in_progress = False
        self._pending_full_store_reset = False

    def _configure_dialog_window(self) -> None:
        """Apply the top-level dialog window configuration."""

        self.setWindowTitle("Settings")
        self.resize(1180, 820)
        self.setMinimumSize(1080, 760)
        self.setModal(True)
        self.assign_identity(self, "settings_dialog", "settings.dialog")

    def _build_dialog_layout(self) -> QVBoxLayout:
        """Build the top-level dialog layout and content scaffold."""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        self._build_search_bar(root)
        self._build_content_host(root)
        return root

    def _build_search_bar(self, root: QVBoxLayout) -> None:
        """Build the settings search input."""

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search settings...")
        self.search_edit.setClearButtonEnabled(True)
        self.assign_identity(
            self.search_edit, "settings_dialog:search", "settings.search"
        )
        self.search_edit.textChanged.connect(self.apply_search_filter)
        root.addWidget(self.search_edit)

    def _build_content_host(self, root: QVBoxLayout) -> None:
        """Build the split content area with tree navigation and right pane."""

        content_host = QWidget(self)
        content_layout = QHBoxLayout(content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        root.addWidget(content_host, 1)
        self._build_section_tree(content_layout, content_host)
        self._build_right_content(content_layout, content_host)

    def _build_section_tree(
        self,
        content_layout: QHBoxLayout,
        content_host: QWidget,
    ) -> None:
        """Build the left-side section tree."""

        self._section_tree = QTreeWidget(content_host)
        self.section_tree = self._section_tree
        self._section_tree.setHeaderHidden(True)
        self._section_tree.setIndentation(12)
        self._section_tree.setMinimumWidth(220)
        self._section_tree.setMaximumWidth(280)
        self._section_tree.currentItemChanged.connect(self.on_section_tree_changed)
        self.assign_identity(
            self._section_tree, "settings_dialog:section_tree", "settings.section_tree"
        )
        content_layout.addWidget(self._section_tree, 0)

    def _build_right_content(
        self,
        content_layout: QHBoxLayout,
        content_host: QWidget,
    ) -> None:
        """Build the right-side content stack."""

        right_host = QWidget(content_host)
        right_layout = QVBoxLayout(right_host)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        content_layout.addWidget(right_host, 1)
        self._build_reset_actions_bar(right_layout, right_host)
        self._build_scroll_host(right_layout, right_host)
        self._no_matches_label = QLabel("No settings match your search.", right_host)
        self._no_matches_label.setVisible(False)
        right_layout.addWidget(self._no_matches_label)

    def _build_reset_actions_bar(
        self,
        right_layout: QVBoxLayout,
        right_host: QWidget,
    ) -> None:
        """Build the reset actions bar shown above the section content."""

        self._reset_actions_bar = QWidget(right_host)
        reset_bar_layout = QVBoxLayout(self._reset_actions_bar)
        reset_bar_layout.setContentsMargins(0, 0, 0, 0)
        reset_bar_layout.setSpacing(4)
        self.assign_identity(
            self._reset_actions_bar,
            "settings_dialog:reset_context_bar",
            "settings.reset.context_bar",
        )

        reset_top_row = QWidget(self._reset_actions_bar)
        reset_top_layout = QHBoxLayout(reset_top_row)
        reset_top_layout.setContentsMargins(0, 0, 0, 0)
        reset_top_layout.setSpacing(8)

        self.reset_section_context_label = QLabel(self._reset_actions_bar)
        self.assign_identity(
            self.reset_section_context_label,
            "settings_dialog:reset_context_label",
            "settings.reset.context_label",
        )
        self.reset_section_button = QPushButton(
            "Reset Section", self._reset_actions_bar
        )
        self.reset_section_button.clicked.connect(self.on_reset_current_section)
        self.assign_identity(
            self.reset_section_button,
            "settings_dialog:reset_section_button",
            "settings.reset.section_button",
        )
        self.reset_all_button = QPushButton(
            "Reset Everything Stored", self._reset_actions_bar
        )
        self.reset_all_button.clicked.connect(self.on_reset_all_everything_stored)
        self.assign_identity(
            self.reset_all_button,
            "settings_dialog:reset_everything_button",
            "settings.reset.everything_button",
        )
        reset_top_layout.addWidget(self.reset_section_context_label, 1)
        reset_top_layout.addWidget(self.reset_section_button)
        reset_top_layout.addWidget(self.reset_all_button)
        reset_bar_layout.addWidget(reset_top_row)

        self.reset_pending_label = QLabel(self._reset_actions_bar)
        self.reset_pending_label.setWordWrap(True)
        self.reset_pending_label.setStyleSheet("color: #B25F00;")
        self.assign_identity(
            self.reset_pending_label,
            "settings_dialog:reset_pending_label",
            "settings.reset.pending_label",
        )
        reset_bar_layout.addWidget(self.reset_pending_label)
        right_layout.addWidget(self._reset_actions_bar, 0)

    def _build_scroll_host(
        self,
        right_layout: QVBoxLayout,
        right_host: QWidget,
    ) -> None:
        """Build the scrollable settings content host."""

        self._scroll = QScrollArea(right_host)
        self._scroll.setWidgetResizable(True)
        self._scroll_host = QWidget(self._scroll)
        self.scroll_host = self._scroll_host
        self._scroll_layout = QVBoxLayout(self._scroll_host)
        self.scroll_layout = self._scroll_layout
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(10)
        self._scroll.setWidget(self._scroll_host)
        right_layout.addWidget(self._scroll, 1)

    def _build_live_preview_and_buttons(self, root: QVBoxLayout) -> None:
        """Build the preview timer and dialog button box."""

        self._live_preview_timer = QTimer(self)
        self._live_preview_timer.setSingleShot(True)
        self._live_preview_timer.timeout.connect(self._flush_live_preview)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._accept_with_apply)
        apply_button = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        apply_button.clicked.connect(self._apply_and_commit)
        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(self._button_box)

    def build_command_controls(
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

    def build_path_controls(
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

    def build_dual_text_controls(
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

    def build_delete_shell_controls(
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

    def build_backend_executable_controls(
        self,
        *,
        executable_edit: QLineEdit,
        default_executable: str,
        discover_default_executable: str,
        enable_find: bool = True,
    ) -> QWidget:
        executable_edit.textChanged.connect(self._on_controls_changed)
        host = QWidget(self)
        layout = QGridLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.addWidget(QLabel("Executable", host), 0, 0)
        layout.addWidget(executable_edit, 0, 1)

        actions = QWidget(host)
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        browse_btn = QPushButton("Browse...", actions)
        find_btn = QPushButton("Find", actions)
        find_btn.setEnabled(bool(enable_find and discover_default_executable))
        reset_btn = QPushButton("Reset", actions)
        browse_btn.clicked.connect(lambda: self._browse_executable(executable_edit))
        find_btn.clicked.connect(
            lambda: self._find_executable(
                executable_edit,
                default_executable=discover_default_executable,
            )
        )
        reset_btn.clicked.connect(lambda: executable_edit.setText(default_executable))
        actions_layout.addStretch(1)
        actions_layout.addWidget(browse_btn)
        actions_layout.addWidget(find_btn)
        actions_layout.addWidget(reset_btn)
        layout.addWidget(actions, 1, 1)
        layout.setColumnStretch(1, 1)
        return host

    def build_preview_label(self) -> QLabel:
        label = QLabel(self)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setStyleSheet("color: #444;")
        return label

    def build_robocopy_settings_card(self) -> QWidget:
        return backend_cards_transfer.build_robocopy_settings_card(self)

    def build_teracopy_settings_card(self) -> QWidget:
        return backend_cards_transfer.build_teracopy_settings_card(self)

    def build_unstoppable_settings_card(self) -> QWidget:
        return backend_cards_external.build_unstoppable_settings_card(self)

    def build_external_copymove_settings_card(self) -> QWidget:
        return backend_cards_external.build_external_copymove_settings_card(self)

    def on_teracopy_struct_close_toggled(self, checked: bool) -> None:
        if checked and self.teracopy_struct_keep_open_checkbox.isChecked():
            with QSignalBlocker(self.teracopy_struct_keep_open_checkbox):
                self.teracopy_struct_keep_open_checkbox.setChecked(False)
        self._on_controls_changed()

    def on_teracopy_struct_keep_open_toggled(self, checked: bool) -> None:
        if checked and self.teracopy_struct_close_checkbox.isChecked():
            with QSignalBlocker(self.teracopy_struct_close_checkbox):
                self.teracopy_struct_close_checkbox.setChecked(False)
        self._on_controls_changed()

    def _robocopy_structured_options_from_controls(self) -> RobocopyBackendOptions:
        return backend_state.robocopy_structured_options_from_controls(self)

    def _teracopy_structured_options_from_controls(self) -> TeraCopyBackendOptions:
        return backend_state.teracopy_structured_options_from_controls(self)

    def _unstoppable_structured_options_from_controls(
        self,
    ) -> UnstoppableBackendOptions:
        return backend_state.unstoppable_structured_options_from_controls(self)

    def _external_copymove_structured_options_from_controls(
        self,
    ) -> ExternalCopyMoveBackendOptions:
        return backend_state.external_copymove_structured_options_from_controls(self)

    def _apply_robocopy_structured_options_to_controls(
        self, options: RobocopyBackendOptions
    ) -> None:
        backend_state.apply_robocopy_structured_options_to_controls(self, options)

    def _apply_teracopy_structured_options_to_controls(
        self, options: TeraCopyBackendOptions
    ) -> None:
        backend_state.apply_teracopy_structured_options_to_controls(self, options)

    def _apply_unstoppable_structured_options_to_controls(
        self, options: UnstoppableBackendOptions
    ) -> None:
        backend_state.apply_unstoppable_structured_options_to_controls(self, options)

    def _apply_external_copymove_structured_options_to_controls(
        self, options: ExternalCopyMoveBackendOptions
    ) -> None:
        backend_state.apply_external_copymove_structured_options_to_controls(
            self,
            options,
        )

    def reset_robocopy_backend_defaults(self) -> None:
        backend_state.reset_robocopy_backend_defaults(self)

    def reset_teracopy_backend_defaults(self) -> None:
        backend_state.reset_teracopy_backend_defaults(self)

    def reset_unstoppable_backend_defaults(self) -> None:
        backend_state.reset_unstoppable_backend_defaults(self)

    def reset_external_copymove_backend_defaults(self) -> None:
        backend_state.reset_external_copymove_backend_defaults(self)

    def update_backend_generated_previews(self) -> None:
        backend_state.update_backend_generated_previews(self)

    def build_file_open_overrides_controls(self) -> QWidget:
        return open_overrides_controls.build_file_open_overrides_controls(self)

    def add_file_open_override_row(self) -> None:
        row = self.file_open_overrides_table.rowCount()
        self.file_open_overrides_table.insertRow(row)
        self.file_open_overrides_table.setItem(row, 0, QTableWidgetItem(".ext"))
        self.file_open_overrides_table.setItem(row, 1, QTableWidgetItem(""))
        self.file_open_overrides_table.setItem(row, 2, QTableWidgetItem(""))
        self.file_open_overrides_table.selectRow(row)
        self._on_controls_changed()

    def remove_file_open_override_row(self) -> None:
        current = self.file_open_overrides_table.currentRow()
        if current < 0:
            return
        self.file_open_overrides_table.removeRow(current)
        self._on_controls_changed()

    def browse_file_open_override_executable(self, column: int) -> None:
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
        item.setText(
            settings_normalize.normalize_windows_path_text(selected, fallback="")
        )
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

    def on_file_open_overrides_item_changed(self, item: QTableWidgetItem) -> None:
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
            raw_mapping = _string_object_mapping(cast("object", raw))
            for ext in sorted(raw_mapping.keys(), key=str.casefold):
                value_mapping = _string_object_mapping(raw_mapping.get(ext, {}))
                row = self.file_open_overrides_table.rowCount()
                self.file_open_overrides_table.insertRow(row)
                ext_item = QTableWidgetItem(self._normalize_extension(ext))
                editor_item = QTableWidgetItem(str(value_mapping.get("editor", "")))
                viewer_item = QTableWidgetItem(str(value_mapping.get("viewer", "")))
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

    @property
    def active_color_hex(self) -> str:
        return self._active_color_hex

    @property
    def target_color_hex(self) -> str:
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

    def on_controls_changed(self) -> None:
        self._on_controls_changed()

    def apply_search_filter(self, text: str) -> None:
        """Apply a section-row search filter."""

        tree_navigation.apply_search_filter(self, text)

    def on_section_tree_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        """Handle section-tree selection changes."""

        tree_navigation.on_section_tree_changed(self, current, previous)

    def load_preferences_into_controls(self, preferences: UiPreferences) -> None:
        """Populate dialog controls from a preferences snapshot."""

        self._load_preferences_into_controls(preferences)

    def load_file_open_overrides(self, json_text: str) -> None:
        self._load_file_open_overrides(json_text)

    def on_reset_current_section(self) -> None:
        """Reset the active section to defaults."""

        preferences_flow.on_reset_current_section(self)

    def on_reset_all_everything_stored(self) -> None:
        """Schedule a full reset of persisted settings and session data."""

        preferences_flow.on_reset_all_everything_stored(self)

    def browse_executable(self, edit: QLineEdit) -> None:
        self._browse_executable(edit)

    def find_executable(self, edit: QLineEdit, *, default_executable: str) -> None:
        self._find_executable(edit, default_executable=default_executable)

    def reset_command_controls(
        self,
        executable_edit: QLineEdit,
        args_edit: QLineEdit,
        *,
        default_executable: str,
        default_args: str,
    ) -> None:
        self._reset_command_controls(
            executable_edit,
            args_edit,
            default_executable=default_executable,
            default_args=default_args,
        )

    def test_backend(self, kind: OperationKind, backend_id: str) -> None:
        self._test_backend(kind, backend_id)

    def update_reset_controls(self) -> None:
        """Refresh the reset-action UI for the active section."""

        preferences_flow.update_reset_controls(self)

    def robocopy_structured_options_from_controls(self) -> RobocopyBackendOptions:
        return self._robocopy_structured_options_from_controls()

    def teracopy_structured_options_from_controls(self) -> TeraCopyBackendOptions:
        return self._teracopy_structured_options_from_controls()

    def unstoppable_structured_options_from_controls(
        self,
    ) -> UnstoppableBackendOptions:
        return self._unstoppable_structured_options_from_controls()

    def external_copymove_structured_options_from_controls(
        self,
    ) -> ExternalCopyMoveBackendOptions:
        return self._external_copymove_structured_options_from_controls()

    def apply_robocopy_structured_options_to_controls(
        self, options: RobocopyBackendOptions
    ) -> None:
        self._apply_robocopy_structured_options_to_controls(options)

    def apply_teracopy_structured_options_to_controls(
        self, options: TeraCopyBackendOptions
    ) -> None:
        self._apply_teracopy_structured_options_to_controls(options)

    def apply_unstoppable_structured_options_to_controls(
        self, options: UnstoppableBackendOptions
    ) -> None:
        self._apply_unstoppable_structured_options_to_controls(options)

    def apply_external_copymove_structured_options_to_controls(
        self, options: ExternalCopyMoveBackendOptions
    ) -> None:
        self._apply_external_copymove_structured_options_to_controls(options)

    def serialize_file_open_overrides(self) -> str:
        return self._serialize_file_open_overrides()

    def _browse_executable(self, edit: QLineEdit) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable",
            str(Path.home()),
            "Executable Files (*.exe *.cmd *.bat);;All Files (*.*)",
        )
        if not selected:
            return
        edit.setText(
            settings_normalize.normalize_windows_path_text(selected, fallback="")
        )
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

    def _test_backend(self, kind: OperationKind, backend_id: str) -> None:
        self._on_controls_changed()
        root = (
            Path(tempfile.gettempdir())
            / "many_panelz_explorer_op_tests"
            / uuid.uuid4().hex
        )
        root.mkdir(parents=True, exist_ok=True)
        sources, target_dir = self._create_test_paths(root, kind=kind)
        request_kind: OperationKind = "delete" if kind == "delete" else "copy"
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

    def _create_test_paths(
        self, root: Path, *, kind: OperationKind
    ) -> tuple[list[Path], Path | None]:
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

    def _operation_execution_preferences_from_working(
        self,
    ) -> OperationExecutionPreferences:
        preferences = self._working_preferences
        resolved_cmd, resolved_robocopy = resolve_system_command_paths()
        resolved_copy_move = resolve_copy_move_backend_args(
            robocopy_options=preferences.robocopy_structured_options,
            teracopy_options=preferences.teracopy_structured_options,
            unstoppable_options=preferences.unstoppable_structured_options,
            external_copymove_options=preferences.external_copymove_structured_options,
        )
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
            teracopy_executable=preferences.teracopy_executable,
            teracopy_args_template=resolved_copy_move.teracopy_args_template,
            unstoppable_executable=preferences.unstoppable_executable,
            unstoppable_args_template=resolved_copy_move.unstoppable_args_template,
            generic_copymove_executable=preferences.generic_copymove_executable,
            generic_copymove_args_template=resolved_copy_move.external_copymove_args_template,
            generic_delete_executable=preferences.generic_delete_executable,
            generic_delete_args_template=preferences.generic_delete_args_template,
            robocopy_copy_args=resolved_copy_move.robocopy_copy_args,
            robocopy_move_args=resolved_copy_move.robocopy_move_args,
            cmd_delete_args=preferences.cmd_delete_args,
            powershell_delete_args=preferences.powershell_delete_args,
            rimraf_executable=preferences.rimraf_executable,
            rimraf_args_template=preferences.rimraf_args_template,
            resolved_cmd_path=resolved_cmd,
            resolved_robocopy_path=resolved_robocopy,
        )
        return resolve_companion_tool_paths(base)

    def new_font_family_combo(
        self, *, include_base_option: bool, base_label: str
    ) -> QComboBox:
        combo = QComboBox(self)
        if include_base_option:
            combo.addItem(base_label, "")
        for family in QFontDatabase.families():
            combo.addItem(family, family)
        combo.currentIndexChanged.connect(self._on_controls_changed)
        return combo

    def new_byte_format_mode_combo(self) -> QComboBox:
        combo = QComboBox(self)
        combo.addItem("Human Readable", "human_readable")
        combo.addItem("Always MB", "always_mb")
        combo.addItem("Always MiB", "always_mib")
        combo.addItem("Bytes", "bytes")
        combo.addItem("Custom", "custom")
        combo.currentIndexChanged.connect(self._on_byte_format_mode_changed)
        return combo

    def _on_byte_format_mode_changed(self, _index: int) -> None:
        preferences_sync.sync_byte_format_controls(self)
        self._on_controls_changed()

    def on_file_list_use_app_font_toggled(self, _checked: bool) -> None:
        preferences_sync.sync_font_override_controls(self)
        self._on_controls_changed()

    def on_navigation_use_app_font_toggled(self, _checked: bool) -> None:
        preferences_sync.sync_font_override_controls(self)
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
        try:
            self._working_preferences = replace(preferences)
            self._load_panel_tint_preferences(preferences)
            preferences_sync.load_panel_preferences(self, preferences)
            preferences_sync.load_operations_preferences(self, preferences)
            preferences_sync.load_typography_preferences(self, preferences)
            preferences_sync.sync_font_override_controls(self)
            preferences_sync.sync_byte_format_controls(self)
            self.update_backend_generated_previews()
            preferences_sync.sync_slider_value_labels(self)
            preferences_flow.update_reset_controls(self)
        finally:
            self._loading_ui = False

    def set_combo_value(self, combo: QComboBox, value: str) -> None:
        self._set_combo_value(combo, value)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if str(combo.itemData(index)) == str(value):
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _on_controls_changed(self) -> None:
        if self._loading_ui:
            return
        preferences_sync.sync_slider_value_labels(self)
        self._working_preferences = preferences_sync.collect_preferences_from_controls(
            self
        )
        self.update_backend_generated_previews()
        self._pending_live_preview = True
        self._live_preview_timer.start(self.LIVE_PREVIEW_DEBOUNCE_MS)

    def _flush_live_preview(self) -> None:
        if not self._pending_live_preview:
            return
        self._pending_live_preview = False
        self.controller.preview_ui_preferences(self._working_preferences)

    def choose_active_color(self) -> None:
        selected = QColorDialog.getColor(
            QColor(self._active_color_hex), self, "Active Tint Color"
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
        selected = QColorDialog.getColor(
            QColor(self._target_color_hex), self, "Target Tint Color"
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
        self._apply_and_commit()
        self.accept()

    def _apply_and_commit(self) -> None:
        preferences_flow.apply_and_commit(self)

    def reject(self) -> None:
        preferences_flow.prepare_reject(self)
        super().reject()

    def assign_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        assign_widget_identity(widget, widget_id=widget_id, widget_alias=alias)
