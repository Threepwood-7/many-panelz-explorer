"""Preferences dialog for UI and operation backend settings."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast

from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)
from threep_commons.qt.widget_identity import assign_widget_identity

from .settings import (
    FontSizeSpinBox,
    SectionEntry,
    SubsectionEntry,
    build_sections,
    tree_navigation,
)
from .settings.dialog_runtime import SettingsDialogRuntimeMixin

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent, QShowEvent
    from PySide6.QtWidgets import QTreeWidgetItem

    from ..app_controller import AppController


class _DialogGeometryPayload(TypedDict):
    """Typed settings payload for persisted settings-dialog bounds."""

    x: int
    y: int
    width: int
    height: int


def _dialog_geometry_payload(value: object) -> _DialogGeometryPayload | None:
    """Normalize a raw settings value into dialog position and size data."""

    if not isinstance(value, dict):
        return None
    raw_mapping = cast("dict[object, object]", value)
    normalized: dict[str, object] = {}
    for raw_key, raw_value in raw_mapping.items():
        normalized[str(raw_key)] = raw_value
    x = normalized.get("x")
    y = normalized.get("y")
    width = normalized.get("width")
    height = normalized.get("height")
    if not isinstance(x, int):
        return None
    if not isinstance(y, int):
        return None
    if not isinstance(width, int):
        return None
    if not isinstance(height, int):
        return None
    payload: _DialogGeometryPayload = {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }
    return payload


class SettingsDialog(SettingsDialogRuntimeMixin, QDialog):
    """Edit persisted UI, panel, and operation preferences."""

    LIVE_PREVIEW_DEBOUNCE_MS = 140
    WINDOW_ID: ClassVar[str] = "settings_dialog"
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
            "show_tab_close_buttons",
            "show_storage_overview_status_row",
            "column_width_auto_align_mode",
            "autofit_columns",
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
            "default_terminal_launcher",
            "comspec_terminal_executable",
            "comspec_terminal_open_args_template",
            "comspec_terminal_command_args_template",
            "comspec_terminal_startup_position",
            "pwsh_terminal_executable",
            "pwsh_terminal_open_args_template",
            "pwsh_terminal_command_args_template",
            "pwsh_terminal_startup_position",
            "powershell5_terminal_executable",
            "powershell5_terminal_open_args_template",
            "powershell5_terminal_command_args_template",
            "powershell5_terminal_startup_position",
            "context_tool_code_editor_exe_path",
            "context_tool_code_editor_args_template",
            "context_tool_git_gui_exe_path",
            "context_tool_git_gui_args_template",
            "total_commander_executable",
            "total_commander_source_args_template",
            "total_commander_source_target_args_template",
            "double_commander_executable",
            "double_commander_source_args_template",
            "double_commander_source_target_args_template",
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
        autofit_columns_checkbox: QCheckBox
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
        comspec_terminal_command_args_edit: QLineEdit
        comspec_terminal_executable_edit: QLineEdit
        comspec_terminal_open_args_edit: QLineEdit
        comspec_terminal_startup_position_combo: QComboBox
        default_conflict_policy_combo: QComboBox
        default_copy_move_backend_combo: QComboBox
        default_delete_backend_combo: QComboBox
        default_dispatch_mode_combo: QComboBox
        default_editor_executable_edit: QLineEdit
        default_terminal_launcher_combo: QComboBox
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
        powershell5_terminal_command_args_edit: QLineEdit
        powershell5_terminal_executable_edit: QLineEdit
        powershell5_terminal_open_args_edit: QLineEdit
        powershell5_terminal_startup_position_combo: QComboBox
        powershell_delete_args_edit: QLineEdit
        powershell_delete_test_btn: QPushButton
        properties_byte_custom_template_edit: QLineEdit
        properties_byte_format_mode_combo: QComboBox
        pwsh_terminal_command_args_edit: QLineEdit
        pwsh_terminal_executable_edit: QLineEdit
        pwsh_terminal_open_args_edit: QLineEdit
        pwsh_terminal_startup_position_combo: QComboBox
        remove_override_row_btn: QPushButton
        resolved_comspec_terminal_path_label: QLabel
        resolved_cmd_path_label: QLabel
        resolved_powershell5_terminal_path_label: QLabel
        resolved_pwsh_terminal_path_label: QLabel
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
        show_tab_close_buttons_checkbox: QCheckBox
        show_storage_overview_status_row_checkbox: QCheckBox
        status_bar_byte_custom_template_edit: QLineEdit
        status_bar_byte_format_mode_combo: QComboBox
        status_bar_storage_label_template_edit: QLineEdit
        target_color_button: QPushButton
        target_color_preview: QLabel
        target_intensity_slider: QSlider
        target_intensity_value: QLabel
        total_commander_executable_edit: QLineEdit
        total_commander_source_args_edit: QLineEdit
        total_commander_source_target_args_edit: QLineEdit
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
        double_commander_executable_edit: QLineEdit
        double_commander_source_args_edit: QLineEdit
        double_commander_source_target_args_edit: QLineEdit
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
        _did_restore_window_geometry: bool

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
        self._did_restore_window_geometry = False

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

    def assign_identity(self, widget: QWidget, widget_id: str, alias: str) -> None:
        """Assign deterministic identity metadata to a dialog widget."""

        assign_widget_identity(widget, widget_id=widget_id, widget_alias=alias)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist dialog geometry when the settings window closes."""

        self._save_window_geometry()
        super().closeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        """Restore persisted dialog geometry after the dialog first appears."""

        super().showEvent(event)
        if self._did_restore_window_geometry:
            return
        self._did_restore_window_geometry = True
        QTimer.singleShot(0, self._restore_window_geometry)

    def _window_geometry_key(self) -> str:
        """Return the settings key used for settings-dialog geometry."""

        return self.controller.settings.window_key(self.WINDOW_ID, "geometry")

    def _restore_window_geometry(self) -> None:
        """Restore the previously persisted dialog geometry when available."""

        geometry_key = self._window_geometry_key()
        geometry_payload = _dialog_geometry_payload(
            self.controller.settings.get_json(geometry_key, None)
        )
        if geometry_payload is not None:
            self.resize(geometry_payload["width"], geometry_payload["height"])
            self.move(geometry_payload["x"], geometry_payload["y"])
            return
        geometry = self.controller.settings.value(geometry_key, None)
        if isinstance(geometry, QByteArray) and not geometry.isEmpty():
            self.restoreGeometry(geometry)

    def _save_window_geometry(self) -> None:
        """Persist the current dialog geometry into the shared settings store."""

        self.controller.settings.set_json(
            self._window_geometry_key(),
            {
                "x": int(self.x()),
                "y": int(self.y()),
                "width": int(self.width()),
                "height": int(self.height()),
            },
        )
