"""General operations and about section builders for settings."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
)

from ..._settings.manager import SettingsManager
from ...constants import APP_DISPLAY_NAME, APP_VERSION
from . import control_builders, open_overrides_controls
from .section_structure import add_row

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog
    from .section_models import SubsectionEntry


def build_operations_rows(
    dialog: SettingsDialog,
    *,
    defaults_queue_group: SubsectionEntry,
    open_tools_group: SubsectionEntry,
    backend_commands_group: SubsectionEntry,
    backend_args_group: SubsectionEntry,
    diagnostics_group: SubsectionEntry,
) -> None:
    """Build operation backend, tools, and diagnostics rows."""

    from . import section_operations_backends

    build_operation_defaults_rows(
        dialog,
        defaults_queue_group=defaults_queue_group,
    )
    build_operation_open_tools_rows(
        dialog,
        open_tools_group=open_tools_group,
    )
    section_operations_backends.build_operation_backend_rows(
        dialog,
        backend_commands_group=backend_commands_group,
        backend_args_group=backend_args_group,
    )
    build_operation_diagnostics_rows(
        dialog,
        diagnostics_group=diagnostics_group,
    )


def build_operation_defaults_rows(
    dialog: SettingsDialog,
    *,
    defaults_queue_group: SubsectionEntry,
) -> None:
    """Build default backend, dispatch, and queue preference rows."""

    build_operation_backend_default_rows(
        dialog,
        defaults_queue_group=defaults_queue_group,
    )
    build_operation_dispatch_rows(
        dialog,
        defaults_queue_group=defaults_queue_group,
    )


def build_operation_backend_default_rows(
    dialog: SettingsDialog,
    *,
    defaults_queue_group: SubsectionEntry,
) -> None:
    """Build default backend selector rows for copy/move and delete."""

    dialog.default_copy_move_backend_combo = QComboBox(dialog)
    dialog.default_copy_move_backend_combo.addItem(
        "Python Built-in",
        "python_builtin",
    )
    dialog.default_copy_move_backend_combo.addItem(
        "Windows Explorer",
        "windows_explorer",
    )
    dialog.default_copy_move_backend_combo.addItem("Robocopy", "robocopy")
    dialog.default_copy_move_backend_combo.addItem("TeraCopy", "teracopy")
    dialog.default_copy_move_backend_combo.addItem(
        "Unstoppable Copier",
        "unstoppable",
    )
    dialog.default_copy_move_backend_combo.addItem(
        "External Command",
        "external_copymove",
    )
    dialog.default_copy_move_backend_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=defaults_queue_group,
        key="default_copy_move_backend",
        title="Default Copy/Move Backend",
        description="Backend used for copy/move when no per-run override is chosen.",
        terms=(
            "copy move backend default python explorer robocopy teracopy "
            "unstoppable external"
        ),
        controls=[dialog.default_copy_move_backend_combo],
    )

    dialog.default_delete_backend_combo = QComboBox(dialog)
    dialog.default_delete_backend_combo.addItem("Recycle Bin", "recycle_bin")
    dialog.default_delete_backend_combo.addItem(
        "Permanent Native",
        "permanent_native",
    )
    dialog.default_delete_backend_combo.addItem("cmd Delete", "cmd_delete")
    dialog.default_delete_backend_combo.addItem(
        "PowerShell Delete",
        "powershell_delete",
    )
    dialog.default_delete_backend_combo.addItem("rimraf", "rimraf")
    dialog.default_delete_backend_combo.addItem("External Delete", "external_delete")
    dialog.default_delete_backend_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=defaults_queue_group,
        key="default_delete_backend",
        title="Default Delete Backend",
        description=(
            "Backend used for delete operations when no per-run override is chosen."
        ),
        terms=(
            "delete backend default recycle bin permanent cmd powershell "
            "rimraf external"
        ),
        controls=[dialog.default_delete_backend_combo],
    )


def build_operation_dispatch_rows(
    dialog: SettingsDialog,
    *,
    defaults_queue_group: SubsectionEntry,
) -> None:
    """Build dispatch, conflict, shortcut, and queue view rows."""

    dialog.default_dispatch_mode_combo = QComboBox(dialog)
    dialog.default_dispatch_mode_combo.addItem("Queue", "queue")
    dialog.default_dispatch_mode_combo.addItem(
        "Launch Now (No Wait)",
        "launch_now_no_wait",
    )
    dialog.default_dispatch_mode_combo.addItem("Run Now (Wait)", "run_now_wait")
    dialog.default_dispatch_mode_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=defaults_queue_group,
        key="default_operation_dispatch_mode",
        title="Default Dispatch Mode",
        description=(
            "Choose whether operations queue, launch detached, or run synchronously."
        ),
        terms="dispatch mode queue launch wait operation",
        controls=[dialog.default_dispatch_mode_combo],
    )

    dialog.default_conflict_policy_combo = QComboBox(dialog)
    dialog.default_conflict_policy_combo.addItem("Overwrite", "overwrite")
    dialog.default_conflict_policy_combo.addItem("Skip", "skip")
    dialog.default_conflict_policy_combo.addItem("Rename", "rename")
    dialog.default_conflict_policy_combo.addItem("Cancel", "cancel")
    dialog.default_conflict_policy_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=defaults_queue_group,
        key="default_operation_conflict_policy",
        title="Default Conflict Policy",
        description="Default name-conflict behavior for non-interactive copy/move.",
        terms="conflict policy overwrite skip rename cancel",
        controls=[dialog.default_conflict_policy_combo],
    )

    dialog.operation_shortcut_behavior_combo = QComboBox(dialog)
    dialog.operation_shortcut_behavior_combo.addItem(
        "Direct Enqueue",
        "direct_enqueue",
    )
    dialog.operation_shortcut_behavior_combo.addItem(
        "Always Show Dialog",
        "always_dialog",
    )
    dialog.operation_shortcut_behavior_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=defaults_queue_group,
        key="operation_shortcut_behavior",
        title="Shortcut Behavior",
        description=(
            "Choose whether F5/F6/F8 use defaults directly or open a "
            "configuration dialog."
        ),
        terms="shortcut behavior f5 f6 f8 dialog enqueue",
        controls=[dialog.operation_shortcut_behavior_combo],
    )

    dialog.operation_queue_view_mode_combo = QComboBox(dialog)
    dialog.operation_queue_view_mode_combo.addItem("Queue Dock", "dock_tab")
    dialog.operation_queue_view_mode_combo.addItem(
        "Floating Window",
        "floating_window",
    )
    dialog.operation_queue_view_mode_combo.addItem("Both", "both")
    dialog.operation_queue_view_mode_combo.currentIndexChanged.connect(
        dialog.on_controls_changed
    )
    add_row(
        dialog,
        section=defaults_queue_group,
        key="operation_queue_view_mode",
        title="Queue View Mode",
        description="Default queue presentation mode at runtime.",
        terms="queue dock floating window both",
        controls=[dialog.operation_queue_view_mode_combo],
    )


def build_operation_open_tools_rows(
    dialog: SettingsDialog,
    *,
    open_tools_group: SubsectionEntry,
) -> None:
    """Build default open-tool and extension-override rows."""

    build_default_open_tool_rows(
        dialog,
        open_tools_group=open_tools_group,
    )
    build_context_tool_rows(
        dialog,
        open_tools_group=open_tools_group,
    )
    build_file_open_override_rows(
        dialog,
        open_tools_group=open_tools_group,
    )


def build_default_open_tool_rows(
    dialog: SettingsDialog,
    *,
    open_tools_group: SubsectionEntry,
) -> None:
    """Build rows for the default editor and viewer executables."""

    dialog.default_editor_executable_edit = QLineEdit(dialog)
    default_editor_controls = control_builders.build_path_controls(
        dialog,
        executable_edit=dialog.default_editor_executable_edit,
        default_executable=SettingsManager.DEFAULT_DEFAULT_EDITOR_EXECUTABLE,
    )
    add_row(
        dialog,
        section=open_tools_group,
        key="default_editor_executable",
        title="Default Editor",
        description=(
            "Default executable used for edit operations, including queue scripts."
        ),
        terms="default editor executable open edit script",
        controls=[default_editor_controls],
    )

    dialog.default_viewer_executable_edit = QLineEdit(dialog)
    default_viewer_controls = control_builders.build_path_controls(
        dialog,
        executable_edit=dialog.default_viewer_executable_edit,
        default_executable=SettingsManager.DEFAULT_DEFAULT_VIEWER_EXECUTABLE,
    )
    add_row(
        dialog,
        section=open_tools_group,
        key="default_viewer_executable",
        title="Default Viewer",
        description=(
            "Default executable used for view operations. Empty means use "
            "Default Editor."
        ),
        terms="default viewer executable open view fallback editor",
        controls=[default_viewer_controls],
    )


def build_context_tool_rows(
    dialog: SettingsDialog,
    *,
    open_tools_group: SubsectionEntry,
) -> None:
    """Build rows for code-editor and Git GUI context tools."""

    dialog.context_code_editor_executable_edit = QLineEdit(dialog)
    dialog.context_code_editor_args_edit = QLineEdit(dialog)
    context_code_editor_controls = control_builders.build_command_controls(
        dialog,
        executable_edit=dialog.context_code_editor_executable_edit,
        args_edit=dialog.context_code_editor_args_edit,
        default_executable=SettingsManager.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH,
        default_args=SettingsManager.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE,
        discover_default_executable="",
        enable_find=False,
    )
    add_row(
        dialog,
        section=open_tools_group,
        key="context_code_editor_tool",
        title="Context Tool: Code Editor",
        description=(
            "Executable and args template for context actions using code editor."
        ),
        terms="context tool code editor executable args template",
        controls=[context_code_editor_controls],
    )

    dialog.context_git_gui_executable_edit = QLineEdit(dialog)
    dialog.context_git_gui_args_edit = QLineEdit(dialog)
    context_git_gui_controls = control_builders.build_command_controls(
        dialog,
        executable_edit=dialog.context_git_gui_executable_edit,
        args_edit=dialog.context_git_gui_args_edit,
        default_executable=SettingsManager.DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH,
        default_args=SettingsManager.DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE,
        discover_default_executable="",
        enable_find=False,
    )
    add_row(
        dialog,
        section=open_tools_group,
        key="context_git_gui_tool",
        title="Context Tool: Git GUI",
        description="Executable and args template for context actions using Git GUI.",
        terms="context tool git gui executable args template",
        controls=[context_git_gui_controls],
    )


def build_file_open_override_rows(
    dialog: SettingsDialog,
    *,
    open_tools_group: SubsectionEntry,
) -> None:
    """Build rows for per-extension editor and viewer overrides."""

    dialog.file_open_overrides_table = QTableWidget(0, 3, dialog)
    dialog.file_open_overrides_table.setHorizontalHeaderLabels(
        ["Extension", "Editor", "Viewer"]
    )
    dialog.file_open_overrides_table.horizontalHeader().setStretchLastSection(False)
    dialog.file_open_overrides_table.horizontalHeader().setSectionResizeMode(
        0,
        QHeaderView.ResizeMode.ResizeToContents,
    )
    dialog.file_open_overrides_table.horizontalHeader().setSectionResizeMode(
        1,
        QHeaderView.ResizeMode.Stretch,
    )
    dialog.file_open_overrides_table.horizontalHeader().setSectionResizeMode(
        2,
        QHeaderView.ResizeMode.Stretch,
    )
    dialog.file_open_overrides_table.itemChanged.connect(
        dialog.on_file_open_overrides_item_changed
    )
    dialog.file_open_overrides_table.setMinimumHeight(150)
    overrides_controls = open_overrides_controls.build_file_open_overrides_controls(
        dialog
    )
    add_row(
        dialog,
        section=open_tools_group,
        key="file_open_overrides",
        title="Per-Extension Open Overrides",
        description=(
            "Override editor/viewer executables by extension "
            "(example: .log, .json, .cmd)."
        ),
        terms="extension override editor viewer open file",
        controls=[overrides_controls],
    )


def build_operation_diagnostics_rows(
    dialog: SettingsDialog,
    *,
    diagnostics_group: SubsectionEntry,
) -> None:
    """Build read-only diagnostics rows for resolved tool paths."""

    dialog.resolved_cmd_path_label = QLabel(dialog)
    dialog.resolved_robocopy_path_label = QLabel(dialog)
    add_row(
        dialog,
        section=diagnostics_group,
        key="resolved_system_paths",
        title="Resolved System Commands",
        description="Runtime resolved command paths for shell and robocopy.",
        terms="comspec cmd robocopy windir resolved path",
        controls=[
            dialog.resolved_cmd_path_label,
            dialog.resolved_robocopy_path_label,
        ],
    )


def build_about_rows(
    dialog: SettingsDialog,
    *,
    application_info_group: SubsectionEntry,
) -> None:
    """Build about rows for static application metadata."""

    settings_path = Path(str(dialog.controller.settings.settings_path))
    add_row(
        dialog,
        section=application_info_group,
        key="about_name",
        title="Application",
        description=APP_DISPLAY_NAME,
        terms="application name",
        controls=[QLabel(APP_DISPLAY_NAME, dialog)],
    )
    add_row(
        dialog,
        section=application_info_group,
        key="about_version",
        title="Version",
        description=APP_VERSION,
        terms="version",
        controls=[QLabel(APP_VERSION, dialog)],
    )
    add_row(
        dialog,
        section=application_info_group,
        key="about_settings_path",
        title="Settings File",
        description=str(settings_path),
        terms=f"settings file path {settings_path}",
        controls=[QLabel(str(settings_path), dialog)],
    )
