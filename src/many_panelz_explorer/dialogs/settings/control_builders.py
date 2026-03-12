from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..settings_dialog import SettingsDialog


def build_command_controls(
    dialog: SettingsDialog,
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
    executable_edit.textChanged.connect(dialog.on_controls_changed)
    args_edit.textChanged.connect(dialog.on_controls_changed)
    executable_edit.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    args_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    host = QWidget(dialog)
    layout = QGridLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)

    exe_label = QLabel("Executable", host)
    args_label = QLabel("Args", host)
    browse_btn = QPushButton("Browse...", host)
    find_btn = QPushButton("Find", host)
    reset_btn = QPushButton("Reset", host)
    find_btn.setEnabled(bool(enable_find and discover_default_executable))

    browse_btn.clicked.connect(lambda: dialog.browse_executable(executable_edit))
    find_btn.clicked.connect(
        lambda: dialog.find_executable(
            executable_edit,
            default_executable=discover_default_executable,
        )
    )
    reset_btn.clicked.connect(
        lambda: dialog.reset_command_controls(
            executable_edit,
            args_edit,
            default_executable=default_executable,
            default_args=default_args,
        )
    )
    if test_button is not None:
        test_button.clicked.connect(on_test or (lambda: None))

    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    actions_layout.addWidget(browse_btn)
    actions_layout.addWidget(find_btn)
    actions_layout.addWidget(reset_btn)
    if test_button is not None:
        actions_layout.addWidget(test_button)

    layout.addWidget(exe_label, 0, 0)
    layout.addWidget(executable_edit, 0, 1)
    layout.addWidget(args_label, 1, 0)
    layout.addWidget(args_edit, 1, 1)
    next_row = 2
    if extended_paths_checkbox is not None:
        layout.addWidget(extended_paths_checkbox, next_row, 1)
        next_row += 1
    layout.addWidget(actions, next_row, 1)
    layout.setColumnStretch(1, 1)
    host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return host


def build_path_controls(
    dialog: SettingsDialog,
    *,
    executable_edit: QLineEdit,
    default_executable: str,
) -> QWidget:
    executable_edit.textChanged.connect(dialog.on_controls_changed)
    executable_edit.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    host = QWidget(dialog)
    layout = QGridLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)

    exe_label = QLabel("Executable", host)
    browse_btn = QPushButton("Browse...", host)
    reset_btn = QPushButton("Reset", host)
    browse_btn.clicked.connect(lambda: dialog.browse_executable(executable_edit))
    reset_btn.clicked.connect(lambda: executable_edit.setText(default_executable))
    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    actions_layout.addWidget(browse_btn)
    actions_layout.addWidget(reset_btn)

    layout.addWidget(exe_label, 0, 0)
    layout.addWidget(executable_edit, 0, 1)
    layout.addWidget(actions, 1, 1)
    layout.setColumnStretch(1, 1)
    host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return host


def build_dual_text_controls(
    dialog: SettingsDialog,
    *,
    first_label: str,
    first_edit: QLineEdit,
    second_label: str,
    second_edit: QLineEdit,
) -> QWidget:
    first_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    second_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    host = QWidget(dialog)
    layout = QGridLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    layout.addWidget(QLabel(first_label, host), 0, 0)
    layout.addWidget(first_edit, 0, 1)
    layout.addWidget(QLabel(second_label, host), 1, 0)
    layout.addWidget(second_edit, 1, 1)
    layout.setColumnStretch(1, 1)
    host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return host


def build_robocopy_controls(
    dialog: SettingsDialog,
    *,
    first_label: str,
    first_edit: QLineEdit,
    second_label: str,
    second_edit: QLineEdit,
    extended_paths_checkbox: QCheckBox,
    test_button: QPushButton,
) -> QWidget:
    host = QWidget(dialog)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(
        build_dual_text_controls(
            dialog,
            first_label=first_label,
            first_edit=first_edit,
            second_label=second_label,
            second_edit=second_edit,
        )
    )
    layout.addWidget(extended_paths_checkbox)
    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    actions_layout.addWidget(test_button)
    test_button.clicked.connect(lambda: dialog.test_backend("copy", "robocopy"))
    layout.addWidget(actions)
    return host


def build_delete_shell_controls(
    dialog: SettingsDialog,
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
    host = QWidget(dialog)
    layout = QGridLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    layout.addWidget(QLabel(first_label, host), 0, 0)
    layout.addWidget(first_edit, 0, 1)
    layout.addWidget(cmd_extended_paths_checkbox, 1, 1)
    layout.addWidget(QLabel(second_label, host), 2, 0)
    layout.addWidget(second_edit, 2, 1)
    layout.addWidget(powershell_extended_paths_checkbox, 3, 1)
    actions = QWidget(host)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(8)
    actions_layout.addStretch(1)
    actions_layout.addWidget(cmd_test_button)
    actions_layout.addWidget(powershell_test_button)
    cmd_test_button.clicked.connect(lambda: dialog.test_backend("delete", "cmd_delete"))
    powershell_test_button.clicked.connect(
        lambda: dialog.test_backend("delete", "powershell_delete")
    )
    layout.addWidget(actions, 4, 1)
    layout.setColumnStretch(1, 1)
    host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return host
