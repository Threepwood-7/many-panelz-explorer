from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from .detector import (
    ContextDetectionResult,
    ContextDetector,
    GitContextRoot,
    NodeContextRoot,
    PythonContextRoot,
)
from .scripts import (
    RunnableScript,
    parse_node_runnable_scripts,
    parse_python_runnable_scripts,
)
from .tool_registry import ContextTool, ContextToolRegistry, expand_tool_args

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtGui import QAction

    from ..window import ExplorerWindow


@dataclass
class _ScriptMenuState:
    menu: QMenu
    mode_key: str
    root_path: Path
    runner: str
    loaded: bool = False
    loading: bool = False
    scripts: list[RunnableScript] | None = None
    error: str | None = None


class _ScriptLoaderSignals(QObject):
    loaded = Signal(str, str, str, object, object)


class _AsyncScriptLoader:
    _executor = ThreadPoolExecutor(
        max_workers=2, thread_name_prefix="mpe-context-scripts"
    )

    def __init__(self, parent: QObject) -> None:
        self.signals = _ScriptLoaderSignals(parent)
        self._pending: set[tuple[str, str, str]] = set()

    def load(self, mode_key: str, root_path: Path, runner: str = "") -> None:
        key = (str(mode_key), str(root_path), str(runner))
        if key in self._pending:
            return
        self._pending.add(key)

        def _done(future: Future[list[RunnableScript]]) -> None:
            self._pending.discard(key)
            try:
                scripts = future.result()
                error: str | None = None
            except Exception as exc:  # pragma: no cover - defensive worker path
                scripts = []
                error = str(exc)
            self.signals.loaded.emit(key[0], key[1], key[2], scripts, error)

        future = self._executor.submit(self._load_scripts, key[0], Path(key[1]), key[2])
        future.add_done_callback(_done)

    def _load_scripts(
        self, mode_key: str, root_path: Path, runner: str
    ) -> list[RunnableScript]:
        if mode_key == "python":
            return parse_python_runnable_scripts(root_path)
        if mode_key == "node":
            return parse_node_runnable_scripts(root_path, runner=runner or "npm")
        return []


class ContextMenuController(QObject):
    def __init__(self, window: ExplorerWindow, menu: QMenu) -> None:
        super().__init__(window)
        self._window = window
        self._menu = menu
        self._script_loader = _AsyncScriptLoader(self)
        self._script_loader.signals.loaded.connect(self._on_scripts_loaded)
        self._script_menu_states: dict[tuple[str, str, str], _ScriptMenuState] = {}
        self._last_rebuild_signature: tuple[str, int, str, str, str, str] | None = None
        self._owned_menus: list[QMenu] = []

    def rebuild(self) -> None:
        active_path = self._active_path()
        if active_path is None:
            self._menu.clear()
            self._menu.menuAction().setVisible(False)
            self._script_menu_states = {}
            self._owned_menus = []
            self._last_rebuild_signature = None
            return

        preferences = self._window.settings.ui_preferences()
        signature = (
            str(active_path),
            int(preferences.context_immediate_child_scan_cap),
            str(preferences.context_tool_code_editor_exe_path),
            str(preferences.context_tool_code_editor_args_template),
            str(preferences.context_tool_git_gui_exe_path),
            str(preferences.context_tool_git_gui_args_template),
        )
        if signature == self._last_rebuild_signature:
            return
        detector = ContextDetector(
            immediate_child_scan_cap=preferences.context_immediate_child_scan_cap
        )
        detected = detector.detect(active_path)
        self._rebuild_menu_from_detection(
            detected=detected,
            tools=ContextToolRegistry(preferences),
        )
        self._last_rebuild_signature = signature

    def _active_path(self) -> Path | None:
        panel = self._window.active_panel()
        if panel is None:
            return None
        return panel.current_path()

    def _rebuild_menu_from_detection(
        self,
        *,
        detected: ContextDetectionResult,
        tools: ContextToolRegistry,
    ) -> None:
        self._menu.clear()
        self._script_menu_states = {}
        self._owned_menus = []
        if not detected.has_any:
            self._menu.menuAction().setVisible(False)
            return
        self._menu.menuAction().setVisible(True)

        if detected.python_roots:
            mode_menu = self._track_menu(self._menu.addMenu("Python Project"))
            self._populate_python_mode(mode_menu, detected.python_roots, tools)
        if detected.git_roots:
            mode_menu = self._track_menu(self._menu.addMenu("Git Repository"))
            self._populate_git_mode(mode_menu, detected.git_roots, tools)
        if detected.node_roots:
            mode_menu = self._track_menu(self._menu.addMenu("Node / JS / TS Project"))
            self._populate_node_mode(mode_menu, detected.node_roots, tools)

    def _populate_python_mode(
        self,
        mode_menu: QMenu,
        roots: list[PythonContextRoot],
        tools: ContextToolRegistry,
    ) -> None:
        for root in roots:
            root_menu = self._track_menu(
                mode_menu.addMenu(self._root_label(root.root_path))
            )
            version = root.python_version or "unknown"
            version_action = root_menu.addAction(f"Python: {version}")
            version_action.setEnabled(False)
            self._add_tool_action(
                root_menu,
                label="Open project root in Code Editor",
                tool=tools.resolve("code_editor"),
                folder=root.root_path,
                project_root=root.root_path,
            )
            terminal_action = root_menu.addAction("Open terminal here")
            terminal_action.triggered.connect(
                lambda _checked=False, path=root.root_path: self._open_terminal(
                    path, python_project=True
                )
            )
            if root.pyproject_path is not None:
                self._add_tool_action(
                    root_menu,
                    label="Open pyproject.toml in Code Editor",
                    tool=tools.resolve("code_editor"),
                    folder=root.root_path,
                    file=root.pyproject_path,
                    project_root=root.root_path,
                    args_template_override="{file}",
                )
            scripts_menu = self._track_menu(root_menu.addMenu("Runnable Scripts"))
            key = self._script_key("python", root.root_path, "")
            self._script_menu_states[key] = _ScriptMenuState(
                menu=scripts_menu,
                mode_key="python",
                root_path=root.root_path,
                runner="",
            )
            scripts_menu.aboutToShow.connect(self._scripts_menu_callback(key))

    def _populate_git_mode(
        self,
        mode_menu: QMenu,
        roots: list[GitContextRoot],
        tools: ContextToolRegistry,
    ) -> None:
        for root in roots:
            root_menu = self._track_menu(
                mode_menu.addMenu(self._root_label(root.root_path))
            )
            branch = root.branch or "(unknown)"
            branch_action = root_menu.addAction(f"Branch: {branch}")
            branch_action.setEnabled(False)
            self._add_tool_action(
                root_menu,
                label="Open in Git GUI",
                tool=tools.resolve("git_gui"),
                folder=root.root_path,
                project_root=root.root_path,
            )
            terminal_action = root_menu.addAction("Open terminal here")
            terminal_action.triggered.connect(
                lambda _checked=False, path=root.root_path: self._open_terminal(path)
            )
            copy_action = root_menu.addAction("Copy remote origin URL")
            if root.remote_origin_url:
                copy_action.triggered.connect(
                    lambda _checked=False, url=root.remote_origin_url: self._copy_text(
                        url
                    )
                )
            else:
                copy_action.setEnabled(False)
                copy_action.setToolTip("No origin remote URL found.")
            open_remote_action = root_menu.addAction("Open remote URL in browser")
            if root.remote_origin_web_url:
                open_remote_action.triggered.connect(
                    lambda _checked=False, url=root.remote_origin_web_url: (
                        webbrowser.open(url)
                    )
                )
            else:
                open_remote_action.setEnabled(False)
                open_remote_action.setToolTip(
                    "Remote URL missing or not a supported host "
                    "(GitHub/GitLab/Bitbucket)."
                )

    def _populate_node_mode(
        self,
        mode_menu: QMenu,
        roots: list[NodeContextRoot],
        tools: ContextToolRegistry,
    ) -> None:
        for root in roots:
            root_menu = self._track_menu(
                mode_menu.addMenu(self._root_label(root.root_path))
            )
            self._add_tool_action(
                root_menu,
                label="Open project root in Code Editor",
                tool=tools.resolve("code_editor"),
                folder=root.root_path,
                project_root=root.root_path,
            )
            terminal_action = root_menu.addAction("Open terminal here")
            terminal_action.triggered.connect(
                lambda _checked=False, path=root.root_path: self._open_terminal(path)
            )
            if root.package_json_path is not None:
                self._add_tool_action(
                    root_menu,
                    label="Open package.json in Code Editor",
                    tool=tools.resolve("code_editor"),
                    folder=root.root_path,
                    file=root.package_json_path,
                    project_root=root.root_path,
                    args_template_override="{file}",
                )
            scripts_menu = self._track_menu(root_menu.addMenu("Runnable Scripts"))
            key = self._script_key("node", root.root_path, root.runner)
            self._script_menu_states[key] = _ScriptMenuState(
                menu=scripts_menu,
                mode_key="node",
                root_path=root.root_path,
                runner=root.runner,
            )
            scripts_menu.aboutToShow.connect(self._scripts_menu_callback(key))

    def _on_scripts_menu_about_to_show(self, key: tuple[str, str, str]) -> None:
        state = self._script_menu_states.get(key)
        if state is None:
            return
        if state.loaded:
            self._populate_scripts_menu(state)
            return
        state.loading = True
        state.menu.clear()
        loading_action = state.menu.addAction("Loading...")
        loading_action.setEnabled(False)
        self._script_loader.load(
            state.mode_key,
            state.root_path,
            state.runner,
        )

    def _on_scripts_loaded(
        self,
        mode_key: str,
        root_path_text: str,
        runner: str,
        scripts_obj: object,
        error_obj: object,
    ) -> None:
        key = self._script_key(mode_key, Path(root_path_text), runner)
        state = self._script_menu_states.get(key)
        if state is None:
            return
        state.loading = False
        state.loaded = True
        state.error = str(error_obj) if error_obj else None
        state.scripts = list(cast("list[RunnableScript]", scripts_obj))
        self._populate_scripts_menu(state)

    def _populate_scripts_menu(self, state: _ScriptMenuState) -> None:
        state.menu.clear()
        if state.error:
            failed = state.menu.addAction(f"Failed to load scripts: {state.error}")
            failed.setEnabled(False)
            return
        scripts = state.scripts or []
        if not scripts:
            empty = state.menu.addAction("(No runnable scripts)")
            empty.setEnabled(False)
            return
        for entry in scripts:
            action = state.menu.addAction(f"Run: {entry.label}")
            action.setToolTip(entry.command)
            action.triggered.connect(
                self._script_trigger_callback(
                    mode=state.mode_key,
                    root_path=state.root_path,
                    command=entry.command,
                )
            )

    def _script_trigger_callback(
        self,
        *,
        mode: str,
        root_path: Path,
        command: str,
    ) -> Callable[[bool], None]:
        def _trigger(_checked: bool = False) -> None:
            self._run_script(mode, root_path, command)

        return _trigger

    def _run_script(self, mode: str, root_path: Path, command: str) -> None:
        resolved_command = str(command).strip()
        if not resolved_command:
            return
        python_project = mode == "python"
        if python_project:
            resolved_command = self._python_command_with_fallbacks(
                root_path, resolved_command
            )
        self._open_terminal(
            root_path, command=resolved_command, python_project=python_project
        )

    def _add_tool_action(
        self,
        menu: QMenu,
        *,
        label: str,
        tool: ContextTool,
        folder: Path | None = None,
        file: Path | None = None,
        files: list[Path] | None = None,
        project_root: Path | None = None,
        args_template_override: str | None = None,
    ) -> QAction:
        action = menu.addAction(label)
        if not tool.is_available:
            hint = (
                f"{tool.label} unavailable. "
                f"{tool.error or 'Configure tool path in Settings.'}"
            )
            action.setEnabled(False)
            action.setToolTip(hint)
            action.setStatusTip(hint)
            return action

        args_template = (
            str(args_template_override)
            if args_template_override is not None
            else str(tool.args_template or "")
        )

        def _launch() -> None:
            executable = str(tool.resolved_executable or "").strip()
            if not executable:
                return
            args = expand_tool_args(
                args_template,
                folder=folder,
                file=file,
                files=files,
                project_root=project_root,
            )
            try:
                subprocess.Popen([executable, *args])
            except Exception as exc:  # pragma: no cover - UI error path
                QMessageBox.critical(self._window, "Context Action Failed", str(exc))

        action.triggered.connect(_launch)
        return action

    def _copy_text(self, value: str) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(str(value or ""))
        self._window.statusBar().showMessage("Copied remote URL to clipboard.", 1800)

    def _scripts_menu_callback(self, key: tuple[str, str, str]) -> Callable[[], None]:
        def _show_scripts_menu() -> None:
            self._on_scripts_menu_about_to_show(key)

        return _show_scripts_menu

    def _open_terminal(
        self,
        root_path: Path,
        *,
        command: str | None = None,
        python_project: bool = False,
    ) -> None:
        path = Path(root_path)
        if os.name == "nt":
            parts = [f"Set-Location -LiteralPath {self._powershell_quote(str(path))}"]
            if python_project:
                activate_path = path / ".venv" / "Scripts" / "Activate.ps1"
                if activate_path.is_file():
                    parts.append(f". {self._powershell_quote(str(activate_path))}")
            if command:
                parts.append(str(command))
            joined = "; ".join(part for part in parts if part)
            try:
                subprocess.Popen(["powershell", "-NoExit", "-Command", joined])
            except Exception as exc:  # pragma: no cover - UI error path
                QMessageBox.critical(self._window, "Context Action Failed", str(exc))
            return

        if command:
            if shutil.which("x-terminal-emulator"):
                subprocess.Popen(
                    [
                        "x-terminal-emulator",
                        "--working-directory",
                        str(path),
                        "-e",
                        f"sh -lc '{command}; exec sh'",
                    ]
                )
                return
            subprocess.Popen(command, shell=True, cwd=path)
            return

        if shutil.which("x-terminal-emulator"):
            subprocess.Popen(["x-terminal-emulator", "--working-directory", str(path)])
            return
        QMessageBox.warning(
            self._window,
            "Context Action Failed",
            "No terminal launcher found for this platform.",
        )

    def _python_command_with_fallbacks(self, root_path: Path, command: str) -> str:
        activate_path = root_path / ".venv" / "Scripts" / "Activate.ps1"
        if activate_path.is_file():
            return command
        normalized = command.strip().lower()
        if normalized.startswith("hatch run "):
            return command
        if shutil.which("uv"):
            return f"uv run {command}"
        if shutil.which("hatch"):
            return f"hatch run {command}"
        return command

    def _powershell_quote(self, value: str) -> str:
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def _root_label(self, root_path: Path) -> str:
        return str(root_path)

    def _script_key(
        self,
        mode_key: str,
        root_path: Path,
        runner: str,
    ) -> tuple[str, str, str]:
        return (str(mode_key), str(root_path), str(runner))

    def _track_menu(self, menu: QMenu) -> QMenu:
        self._owned_menus.append(menu)
        return menu
