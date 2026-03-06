import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt

from many_panelz_explorer.app_controller import AppController


class _FakeWindow:
    def __init__(self, *, minimized: bool = False, on_raise=None) -> None:
        self._minimized = minimized
        self._on_raise = on_raise
        self.show_normal_calls = 0
        self.raise_calls = 0
        self.activate_calls = 0

    def windowState(self) -> Qt.WindowState:
        return Qt.WindowState.WindowMinimized if self._minimized else Qt.WindowState(0)

    def showNormal(self) -> None:
        self.show_normal_calls += 1
        self._minimized = False

    def raise_(self) -> None:
        self.raise_calls += 1
        if self._on_raise is not None:
            self._on_raise()

    def activateWindow(self) -> None:
        self.activate_calls += 1


class _FakeClosableWindow:
    def __init__(self, window_id: str) -> None:
        self.window_id = window_id
        self.saved = 0

    def save_to_settings(self) -> None:
        self.saved += 1


def test_activation_runs_single_pass_while_active(monkeypatch, tmp_path: Path) -> None:
    controller = AppController(argv=[])

    calls = 0

    def _fake_bring_all_windows_to_front(restore_minimized: bool = True) -> None:
        nonlocal calls
        calls += 1
        assert restore_minimized is True

    monkeypatch.setattr(controller, "bring_all_windows_to_front", _fake_bring_all_windows_to_front)

    controller._on_window_activated()
    controller._on_window_activated()
    controller._on_window_activated()

    assert calls == 1


def test_latch_resets_after_app_deactivation(monkeypatch, tmp_path: Path) -> None:
    controller = AppController(argv=[])

    calls = 0

    def _fake_bring_all_windows_to_front(restore_minimized: bool = True) -> None:
        nonlocal calls
        calls += 1
        assert restore_minimized is True

    monkeypatch.setattr(controller, "bring_all_windows_to_front", _fake_bring_all_windows_to_front)

    controller._on_window_activated()
    controller._on_window_activated()
    assert calls == 1

    controller._on_application_state_changed(Qt.ApplicationState.ApplicationInactive)
    controller._on_window_activated()

    assert calls == 2


def test_bring_all_windows_single_iteration_no_per_window_activate(tmp_path: Path) -> None:
    controller = AppController(argv=[])

    late_window = _FakeWindow()

    def _append_late_window() -> None:
        controller.windows.append(late_window)

    first = _FakeWindow(minimized=True, on_raise=_append_late_window)
    second = _FakeWindow(minimized=False)

    controller.windows = [first, second]  # type: ignore[assignment]
    controller.bring_all_windows_to_front(restore_minimized=True)

    assert first.show_normal_calls == 1
    assert second.show_normal_calls == 0

    assert first.raise_calls == 1
    assert second.raise_calls == 1
    assert late_window.raise_calls == 0

    assert first.activate_calls == 0
    assert second.activate_calls == 0
    assert late_window.activate_calls == 0


def test_save_session_uses_last_closed_window_when_none_open(tmp_path: Path) -> None:
    controller = AppController(argv=[])
    fake = _FakeClosableWindow("w-closed")

    controller.windows = [fake]  # type: ignore[assignment]
    controller.close_window(fake)  # type: ignore[arg-type]
    controller.save_session()

    assert fake.saved == 1
    assert controller.settings.session_window_ids() == ["w-closed"]
