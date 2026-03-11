import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer.dialogs.operation_dialog import OperationDialog
from many_panelz_explorer._settings.models import UiPreferences


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
