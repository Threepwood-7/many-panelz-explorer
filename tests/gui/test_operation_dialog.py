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
