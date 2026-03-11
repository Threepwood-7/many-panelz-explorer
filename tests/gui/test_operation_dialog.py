import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
)
from many_panelz_explorer._settings.models import UiPreferences
from many_panelz_explorer.dialogs.operation_dialog import OperationDialog


def test_operation_dialog_has_no_test_backend_action(qtbot) -> None:
    dialog = OperationDialog(
        kind="copy",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    button_texts = [button.text() for button in dialog.buttons.buttons()]
    assert "Test Backend" not in button_texts
    assert not hasattr(dialog, "test_backend_btn")


def test_collect_backend_options_does_not_include_use_extended_paths(qtbot) -> None:
    dialog = OperationDialog(
        kind="copy",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(use_extended_paths_robocopy=True),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._set_combo_data(dialog.backend_combo, "robocopy")
    dialog._sync_backend_options_visibility()
    options = dialog._collect_backend_options()
    assert "use_extended_paths" not in options


def test_robocopy_defaults_are_verbose(qtbot) -> None:
    dialog = OperationDialog(
        kind="copy",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._set_combo_data(dialog.backend_combo, "robocopy")
    dialog._sync_backend_options_visibility()
    options = dialog._collect_backend_options()
    args = options.get("robocopy_args", "")
    assert "/E" in args
    assert "/R:0" in args
    assert "/W:0" in args
    assert "/NFL" not in args
    assert "/NDL" not in args
    assert "/NP" not in args


def test_robocopy_collects_spinner_and_checkbox_values(qtbot) -> None:
    dialog = OperationDialog(
        kind="copy",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._set_combo_data(dialog.backend_combo, "robocopy")
    dialog._sync_backend_options_visibility()
    dialog.robocopy_retry_spin.setValue(3)
    dialog.robocopy_wait_spin.setValue(7)
    dialog.robocopy_multithread_checkbox.setChecked(True)
    dialog.robocopy_multithread_spin.setValue(16)
    dialog.robocopy_quiet_checkbox.setChecked(True)
    dialog.robocopy_extra_args_edit.setText("/XO")

    options = dialog._collect_backend_options()
    args = options.get("robocopy_args", "")
    assert "/R:3" in args
    assert "/W:7" in args
    assert "/MT:16" in args
    assert "/NFL" in args
    assert "/XO" in args


def test_teracopy_collects_structured_options(qtbot) -> None:
    dialog = OperationDialog(
        kind="copy",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._set_combo_data(dialog.backend_combo, "teracopy")
    dialog._sync_backend_options_visibility()
    dialog.teracopy_close_checkbox.setChecked(True)
    dialog._set_combo_data(dialog.teracopy_conflict_combo, "/SkipAll")
    dialog.teracopy_extra_args_edit.setText("/NoSound")

    options = dialog._collect_backend_options()
    extra = options.get("extra_args", "")
    assert "/Close" in extra
    assert "/SkipAll" in extra
    assert "/NoSound" in extra
    assert "/NoClose" not in extra


def test_unstoppable_collects_documented_switches(qtbot) -> None:
    dialog = OperationDialog(
        kind="copy",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._set_combo_data(dialog.backend_combo, "unstoppable")
    dialog._sync_backend_options_visibility()
    dialog.unstoppable_skip_damaged_checkbox.setChecked(True)
    dialog.unstoppable_keep_owner_checkbox.setChecked(False)
    dialog.unstoppable_extra_args_edit.setText("+x")

    options = dialog._collect_backend_options()
    extra = options.get("extra_args", "")
    tokens = set(extra.split())
    assert "+d" in tokens
    assert "+a" in tokens
    assert "-o" in tokens
    assert "+s" in tokens
    assert "-m" in tokens
    assert "+x" in tokens


def test_operation_dialog_loads_structured_backend_preferences(qtbot) -> None:
    dialog = OperationDialog(
        kind="move",
        sources=[],
        target_dir=None,
        preferences=UiPreferences(
            robocopy_structured_options=RobocopyBackendOptions(
                include_subdirectories=False,
                mirror_target=True,
                move_files_for_move=False,
                restartable_mode=True,
                backup_mode=True,
                list_only=True,
                suppress_logs=True,
                retry_count=9,
                wait_seconds=3,
                use_multithreading=True,
                multithread_count=12,
                extra_args="/XO",
            ),
            teracopy_structured_options=TeraCopyBackendOptions(
                close_on_finish=True,
                keep_open=False,
                verify_after_copy=True,
                no_sound=True,
                conflict_mode="/SkipAll",
                extra_args="/NoHistory",
            ),
            unstoppable_structured_options=UnstoppableBackendOptions(
                use_defaults=False,
                keep_attributes=False,
                keep_owner=False,
                keep_time=False,
                overwrite_existing=False,
                include_subfolders=False,
                recover_and_resume=True,
                copy_newer_only=True,
                skip_damaged=True,
                undamaged_first=True,
                overwrite_readonly=True,
                copy_empty_folders=True,
                show_eta=True,
                power_down_when_done=True,
                extra_args="+x",
            ),
            external_copymove_structured_options=ExternalCopyMoveBackendOptions(
                extra_args="--fast",
            ),
        ),
    )
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.robocopy_include_subdirs_checkbox.isChecked() is False
    assert dialog.robocopy_mirror_checkbox.isChecked() is True
    assert dialog.robocopy_move_checkbox.isChecked() is False
    assert dialog.robocopy_restartable_checkbox.isChecked() is True
    assert dialog.robocopy_backup_mode_checkbox.isChecked() is True
    assert dialog.robocopy_list_only_checkbox.isChecked() is True
    assert dialog.robocopy_quiet_checkbox.isChecked() is True
    assert dialog.robocopy_retry_spin.value() == 9
    assert dialog.robocopy_wait_spin.value() == 3
    assert dialog.robocopy_multithread_checkbox.isChecked() is True
    assert dialog.robocopy_multithread_spin.value() == 12
    assert dialog.robocopy_extra_args_edit.text() == "/XO"

    assert dialog.teracopy_close_checkbox.isChecked() is True
    assert dialog.teracopy_no_close_checkbox.isChecked() is False
    assert str(dialog.teracopy_conflict_combo.currentData()) == "/SkipAll"
    assert dialog.teracopy_extra_args_edit.text() == "/Verify /NoSound /NoHistory"

    assert dialog.unstoppable_defaults_checkbox.isChecked() is False
    assert dialog.unstoppable_keep_attributes_checkbox.isChecked() is False
    assert dialog.unstoppable_keep_owner_checkbox.isChecked() is False
    assert dialog.unstoppable_keep_time_checkbox.isChecked() is False
    assert dialog.unstoppable_overwrite_checkbox.isChecked() is False
    assert dialog.unstoppable_include_subdirs_checkbox.isChecked() is False
    assert dialog.unstoppable_resume_checkbox.isChecked() is True
    assert dialog.unstoppable_copy_newer_checkbox.isChecked() is True
    assert dialog.unstoppable_skip_damaged_checkbox.isChecked() is True
    assert dialog.unstoppable_undamaged_first_checkbox.isChecked() is True
    assert dialog.unstoppable_overwrite_readonly_checkbox.isChecked() is True
    assert dialog.unstoppable_copy_empty_folders_checkbox.isChecked() is True
    assert dialog.unstoppable_eta_checkbox.isChecked() is True
    assert dialog.unstoppable_power_down_checkbox.isChecked() is True
    assert dialog.unstoppable_extra_args_edit.text() == "+x"

    assert dialog.external_extra_args_edit.text() == "--fast"
