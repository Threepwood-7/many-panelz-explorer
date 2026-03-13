from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QEvent

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from many_panelz_explorer._context.scripts import RunnableScript
from many_panelz_explorer._operations.queue_manager import OperationQueueManager
from many_panelz_explorer._operations.types import OperationExecutionPreferences
from many_panelz_explorer._settings.manager import SettingsManager
from many_panelz_explorer.operation_queue_widgets import OperationQueueTableModel
from many_panelz_explorer.window import ExplorerWindow

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class _ControllerStub:
    def __init__(self) -> None:
        self.operation_queue_manager = OperationQueueManager(
            preferences=OperationExecutionPreferences()
        )
        self.operation_queue_model = OperationQueueTableModel(
            self.operation_queue_manager
        )

    def close_window(self, _window: ExplorerWindow) -> None:
        return

    def broadcast_column_widths(self, *_args, **_kwargs) -> None:
        return

    def show_queue_floating_window(self):
        return None


def _test_roots_provider(tmp_path: Path) -> Callable[[Path | None], list[Path]]:
    root = tmp_path / "roots"
    root.mkdir(parents=True, exist_ok=True)
    return lambda _current: [root]


def _write_git_marker(root: Path) -> None:
    git_dir = root / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = git@github.com:acme/demo.git\n',
        encoding="utf-8",
    )


def test_context_menu_hidden_without_modes(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-hidden",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    panel.current_tab().navigation.set_path(empty_dir)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is False)


def test_context_menu_shows_python_mode(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-python",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    py_root = tmp_path / "py-root"
    py_root.mkdir()
    (py_root / "pyproject.toml").write_text(
        "[project]\nname='demo'\n", encoding="utf-8"
    )
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    panel.current_tab().navigation.set_path(py_root)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is True)

    texts = [action.text() for action in window.context_menu.actions()]
    assert "Python Project" in texts


def test_context_menu_tracks_current_and_child_roots(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-grouping",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    root = tmp_path / "node-parent"
    root.mkdir()
    (root / "package.json").write_text(
        '{"name":"parent","scripts":{"build":"echo parent"}}',
        encoding="utf-8",
    )
    child = root / "child-node"
    child.mkdir()
    (child / "package.json").write_text(
        '{"name":"child","scripts":{"dev":"echo child"}}',
        encoding="utf-8",
    )
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    panel.current_tab().navigation.set_path(root)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is True)

    controller = window.context_menu_controller
    assert controller is not None
    node_states = [key for key in controller._script_menu_states if key[0] == "node"]
    assert len(node_states) == 2


def test_context_scripts_load_lazily(qtbot, tmp_path: Path, monkeypatch) -> None:
    def _slow_scripts(_root: Path, *, runner: str) -> list[RunnableScript]:
        time.sleep(0.2)
        return [RunnableScript(label="dev", command=f"{runner} run dev")]

    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.parse_node_runnable_scripts",
        _slow_scripts,
    )

    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-scripts",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    root = tmp_path / "node-scripts"
    root.mkdir()
    (root / "package.json").write_text(
        '{"name":"node-scripts","scripts":{"dev":"vite","test":"vitest"}}',
        encoding="utf-8",
    )
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    panel.current_tab().navigation.set_path(root)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is True)

    controller = window.context_menu_controller
    assert controller is not None
    node_state_keys = [
        key for key in controller._script_menu_states if key[0] == "node"
    ]
    assert node_state_keys
    key = node_state_keys[0]
    controller._on_scripts_menu_about_to_show(key)
    state = controller._script_menu_states[key]
    loading = [action.text() for action in state.menu.actions()]
    assert loading == ["Loading..."]
    assert state.menu.actions()[0].isEnabled() is False
    qtbot.waitUntil(
        lambda: bool(controller._script_menu_states[key].loaded),
        timeout=5000,
    )
    populated = [action.text() for action in state.menu.actions()]
    assert "Run: dev" in populated
    assert "Loading..." not in populated


def test_context_menu_rebuilds_on_tab_switch(qtbot, tmp_path: Path) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-tab-switch",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    plain = tmp_path / "plain"
    plain.mkdir()
    py_root = tmp_path / "py-root"
    py_root.mkdir()
    (py_root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    first_tab = panel.current_tab()
    assert first_tab is not None
    first_tab.navigation.set_path(plain)
    second_tab = panel.add_tab(py_root)
    assert second_tab is not None
    panel.tabs.setCurrentWidget(first_tab)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is False)
    panel.tabs.setCurrentWidget(second_tab)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is True)


def test_context_menu_disables_missing_tools_with_hints(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-missing-tools",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    _write_git_marker(root)

    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    panel.current_tab().navigation.set_path(root)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is True)
    controller = window.context_menu_controller
    assert controller is not None
    controller.rebuild()
    monkeypatch.setattr(controller, "rebuild", lambda: None)

    python_root = next(
        menu
        for menu in controller._owned_menus
        if any(
            action.text() == "Open project root in Code Editor"
            for action in menu.actions()
        )
    )
    py_actions = {action.text(): action for action in python_root.actions()}
    py_editor = py_actions["Open project root in Code Editor"]
    assert py_editor.isEnabled() is False
    assert "Configure this tool path in Settings." in py_editor.toolTip()

    git_root = next(
        menu
        for menu in controller._owned_menus
        if any(action.text() == "Open in Git GUI" for action in menu.actions())
    )
    git_actions = {action.text(): action for action in git_root.actions()}
    git_gui = git_actions["Open in Git GUI"]
    assert git_gui.isEnabled() is False
    assert "Configure this tool path in Settings." in git_gui.toolTip()


def test_context_menu_rebuilds_on_window_activation(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-window-activation",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    window.show()

    py_root = tmp_path / "py-root-activation"
    py_root.mkdir()
    (py_root / "pyproject.toml").write_text(
        "[project]\nname='demo'\n", encoding="utf-8"
    )
    panel = window.panels_coordinator.active_panel()
    assert panel is not None
    panel.current_tab().navigation.set_path(py_root)
    qtbot.waitUntil(lambda: window.menu_context_action.isVisible() is True)

    controller = window.context_menu_controller
    assert controller is not None
    calls = {"count": 0}
    original_rebuild = controller.rebuild

    def _counted_rebuild() -> None:
        calls["count"] += 1
        original_rebuild()

    monkeypatch.setattr(controller, "rebuild", _counted_rebuild)
    window.event(QEvent(QEvent.Type.WindowActivate))
    assert calls["count"] >= 1


def test_context_terminal_command_uses_explicit_sh_fallback(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-terminal-fallback",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    controller = window.context_menu_controller
    assert controller is not None

    recorded: list[dict[str, object]] = []

    def _record_popen(args: object, **kwargs: object) -> None:
        recorded.append({"args": args, "kwargs": kwargs})
        return None

    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.os.name",
        "posix",
    )
    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.shutil.which",
        lambda name: None,
    )
    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.subprocess.Popen",
        _record_popen,
    )

    controller._open_terminal(tmp_path, command="printf hello")

    assert len(recorded) == 1
    assert recorded[0]["args"] == ["sh", "-lc", "printf hello"]
    assert str(recorded[0]["kwargs"]["cwd"]) == str(tmp_path).replace("\\", "/")


def test_context_terminal_command_splits_x_terminal_arguments(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    settings = SettingsManager()
    window = ExplorerWindow(
        controller=_ControllerStub(),
        settings=settings,
        window_id="context-terminal-emulator",
        roots_provider=_test_roots_provider(tmp_path),
    )
    qtbot.addWidget(window)
    controller = window.context_menu_controller
    assert controller is not None

    recorded: list[object] = []

    def _record_popen(args: object, **_kwargs: object) -> None:
        recorded.append(args)
        return None

    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.os.name",
        "posix",
    )
    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.shutil.which",
        lambda name: (
            "/usr/bin/x-terminal-emulator" if name == "x-terminal-emulator" else None
        ),
    )
    monkeypatch.setattr(
        "many_panelz_explorer._context.menu_controller.subprocess.Popen",
        _record_popen,
    )

    controller._open_terminal(tmp_path, command="echo hi")

    assert recorded == [
        [
            "x-terminal-emulator",
            "--working-directory",
            str(tmp_path).replace("\\", "/"),
            "-e",
            "sh",
            "-lc",
            "echo hi; exec sh",
        ]
    ]
