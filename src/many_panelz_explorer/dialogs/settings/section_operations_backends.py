"""Backend command section builders for settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QCheckBox, QLineEdit, QPushButton

from ..._operations.types import DEFAULT_RIMRAF_EXE
from ..._settings.manager import SettingsManager
from . import (
    backend_actions,
    backend_cards_external,
    backend_cards_transfer,
    control_builders,
)
from .section_structure import add_row

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog
    from .section_models import SubsectionEntry


def build_operation_backend_rows(
    dialog: SettingsDialog,
    *,
    backend_commands_group: SubsectionEntry,
    backend_args_group: SubsectionEntry,
) -> None:
    """Build backend command, args, and extended-path rows."""

    build_backend_extended_path_checkboxes(dialog)
    build_copy_move_backend_rows(
        dialog,
        backend_commands_group=backend_commands_group,
        backend_args_group=backend_args_group,
    )
    build_delete_backend_rows(
        dialog,
        backend_commands_group=backend_commands_group,
        backend_args_group=backend_args_group,
    )


def build_backend_extended_path_checkboxes(dialog: SettingsDialog) -> None:
    """Create shared extended-path checkboxes for backend controls."""

    dialog.use_extended_paths_robocopy_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_teracopy_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_unstoppable_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_external_copymove_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_cmd_delete_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_powershell_delete_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_rimraf_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    dialog.use_extended_paths_external_delete_checkbox = QCheckBox(
        r"Use extended paths \\?\... as args",
        dialog,
    )
    for checkbox in [
        dialog.use_extended_paths_robocopy_checkbox,
        dialog.use_extended_paths_teracopy_checkbox,
        dialog.use_extended_paths_unstoppable_checkbox,
        dialog.use_extended_paths_external_copymove_checkbox,
        dialog.use_extended_paths_cmd_delete_checkbox,
        dialog.use_extended_paths_powershell_delete_checkbox,
        dialog.use_extended_paths_rimraf_checkbox,
        dialog.use_extended_paths_external_delete_checkbox,
    ]:
        checkbox.toggled.connect(dialog.on_controls_changed)


def build_copy_move_backend_rows(
    dialog: SettingsDialog,
    *,
    backend_commands_group: SubsectionEntry,
    backend_args_group: SubsectionEntry,
) -> None:
    """Build copy/move backend command and robocopy rows."""

    dialog.teracopy_executable_edit = QLineEdit(dialog)
    dialog.teracopy_test_btn = QPushButton("Test", dialog)
    dialog.teracopy_reset_backend_btn = QPushButton(
        "Reset Backend Defaults",
        dialog,
    )
    teracopy_controls = backend_cards_transfer.build_teracopy_settings_card(dialog)
    add_row(
        dialog,
        section=backend_commands_group,
        key="teracopy_command",
        title="TeraCopy Command",
        description=(
            "Structured options for TeraCopy behavior with generated args preview."
        ),
        terms=(
            "teracopy executable behavior conflict close verify no sound "
            "generated preview extra args template test long path extended"
        ),
        controls=[teracopy_controls],
    )

    dialog.unstoppable_executable_edit = QLineEdit(dialog)
    dialog.unstoppable_test_btn = QPushButton("Test", dialog)
    dialog.unstoppable_reset_backend_btn = QPushButton(
        "Reset Backend Defaults",
        dialog,
    )
    unstoppable_controls = backend_cards_external.build_unstoppable_settings_card(
        dialog
    )
    add_row(
        dialog,
        section=backend_commands_group,
        key="unstoppable_command",
        title="Unstoppable Copier Command",
        description=(
            "Structured toggles for documented Unstoppable switches with "
            "generated preview."
        ),
        terms=(
            "unstoppable copier executable switches defaults attributes owner "
            "time overwrite subfolders resume damaged generated preview extra "
            "args template test long path extended"
        ),
        controls=[unstoppable_controls],
    )

    dialog.generic_copymove_executable_edit = QLineEdit(dialog)
    dialog.generic_copymove_test_btn = QPushButton("Test", dialog)
    dialog.external_copymove_reset_backend_btn = QPushButton(
        "Reset Backend Defaults",
        dialog,
    )
    generic_copymove_controls = (
        backend_cards_external.build_external_copymove_settings_card(dialog)
    )
    add_row(
        dialog,
        section=backend_commands_group,
        key="generic_copymove_command",
        title="Generic Copy/Move Command",
        description=(
            "Structured template composer for external copy/move backend with "
            "generated preview."
        ),
        terms=(
            "external generic copy move executable structured placeholders "
            "operation sources target generated preview extra args template "
            "test long path extended"
        ),
        controls=[generic_copymove_controls],
    )

    dialog.robocopy_test_btn = QPushButton("Test", dialog)
    dialog.robocopy_reset_backend_btn = QPushButton(
        "Reset Backend Defaults",
        dialog,
    )
    robocopy_args_controls = backend_cards_transfer.build_robocopy_settings_card(dialog)
    add_row(
        dialog,
        section=backend_args_group,
        key="robocopy_args",
        title="Robocopy Configuration",
        description=(
            "Structured Robocopy options with checkboxes/spinners and generated "
            "copy/move preview."
        ),
        terms=(
            "robocopy checkboxes spinners retry wait multithread suppress logs "
            "generated preview extra args test long path extended"
        ),
        controls=[robocopy_args_controls],
    )


def build_delete_backend_rows(
    dialog: SettingsDialog,
    *,
    backend_commands_group: SubsectionEntry,
    backend_args_group: SubsectionEntry,
) -> None:
    """Build delete backend command and shell-args rows."""

    dialog.generic_delete_executable_edit = QLineEdit(dialog)
    dialog.generic_delete_args_edit = QLineEdit(dialog)
    dialog.generic_delete_test_btn = QPushButton("Test", dialog)
    generic_delete_controls = control_builders.build_command_controls(
        dialog,
        executable_edit=dialog.generic_delete_executable_edit,
        args_edit=dialog.generic_delete_args_edit,
        default_executable=SettingsManager.DEFAULT_GENERIC_DELETE_EXECUTABLE,
        default_args=SettingsManager.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE,
        discover_default_executable="",
        enable_find=False,
        extended_paths_checkbox=dialog.use_extended_paths_external_delete_checkbox,
        test_button=dialog.generic_delete_test_btn,
        on_test=lambda: backend_actions.test_backend(
            dialog,
            "delete",
            "external_delete",
        ),
    )
    add_row(
        dialog,
        section=backend_commands_group,
        key="generic_delete_command",
        title="Generic Delete Command",
        description="Executable and args template. Tokens: {operation} {sources}",
        terms=(
            "external generic delete executable args template test long path extended"
        ),
        controls=[generic_delete_controls],
    )

    dialog.cmd_delete_args_edit = QLineEdit(dialog)
    dialog.cmd_delete_args_edit.textChanged.connect(dialog.on_controls_changed)
    dialog.powershell_delete_args_edit = QLineEdit(dialog)
    dialog.powershell_delete_args_edit.textChanged.connect(dialog.on_controls_changed)
    dialog.cmd_delete_test_btn = QPushButton("Test cmd", dialog)
    dialog.powershell_delete_test_btn = QPushButton("Test PowerShell", dialog)
    delete_shell_args_controls = control_builders.build_delete_shell_controls(
        dialog,
        first_label="cmd Args",
        first_edit=dialog.cmd_delete_args_edit,
        second_label="PowerShell Args",
        second_edit=dialog.powershell_delete_args_edit,
        cmd_extended_paths_checkbox=dialog.use_extended_paths_cmd_delete_checkbox,
        powershell_extended_paths_checkbox=dialog.use_extended_paths_powershell_delete_checkbox,
        cmd_test_button=dialog.cmd_delete_test_btn,
        powershell_test_button=dialog.powershell_delete_test_btn,
    )
    add_row(
        dialog,
        section=backend_args_group,
        key="delete_shell_args",
        title="Shell Delete Args",
        description="Args for cmd delete and PowerShell delete backends.",
        terms="delete cmd powershell args test long path extended",
        controls=[delete_shell_args_controls],
    )

    dialog.rimraf_executable_edit = QLineEdit(dialog)
    dialog.rimraf_args_edit = QLineEdit(dialog)
    dialog.rimraf_test_btn = QPushButton("Test", dialog)
    rimraf_controls = control_builders.build_command_controls(
        dialog,
        executable_edit=dialog.rimraf_executable_edit,
        args_edit=dialog.rimraf_args_edit,
        default_executable=SettingsManager.DEFAULT_RIMRAF_EXECUTABLE,
        default_args=SettingsManager.DEFAULT_RIMRAF_ARGS_TEMPLATE,
        discover_default_executable=DEFAULT_RIMRAF_EXE,
        extended_paths_checkbox=dialog.use_extended_paths_rimraf_checkbox,
        test_button=dialog.rimraf_test_btn,
        on_test=lambda: backend_actions.test_backend(dialog, "delete", "rimraf"),
    )
    add_row(
        dialog,
        section=backend_commands_group,
        key="rimraf_command",
        title="rimraf Command",
        description="Executable and extra args. Tokens: {sources}",
        terms="rimraf executable args delete test long path extended",
        controls=[rimraf_controls],
    )
