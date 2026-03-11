from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow
from threep_commons.paths import configure_qsettings, resolve_app_data_dir

from . import file_ops
from ._operations.backend_options import resolve_copy_move_backend_args
from ._operations.discovery import (
    resolve_companion_tool_paths,
    resolve_system_command_paths,
)
from ._operations.queue_manager import OperationQueueManager
from ._operations.types import OperationExecutionPreferences
from ._settings.manager import SettingsManager
from .constants import (
    APP_DISPLAY_NAME,
    APP_IDENTITY,
    SETTINGS_APP_NAME,
    SETTINGS_ORG_NAME,
)
from .operation_queue_widgets import OperationQueuePanel, OperationQueueTableModel
from .window import ExplorerWindow

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from ._settings.models import UiPreferences


class AppController:
    def __init__(self, argv: Iterable[str] | None = None) -> None:
        argv_list = list(argv) if argv is not None else []
        configure_qsettings(APP_IDENTITY)
        resolve_app_data_dir(APP_IDENTITY)
        existing = cast("QApplication | None", QApplication.instance())
        self.app: QApplication = (
            existing if existing is not None else QApplication(argv_list)
        )
        self.app.setApplicationName(SETTINGS_APP_NAME)
        self.app.setOrganizationName(SETTINGS_ORG_NAME)
        self.app.setApplicationDisplayName(APP_DISPLAY_NAME)
        self.app.setQuitOnLastWindowClosed(True)
        self._default_app_font = QFont(self.app.font())

        self.settings = SettingsManager()
        self._bootstrap_companion_tools_once()
        initial_preferences = self.settings.ui_preferences()
        self._apply_application_font(initial_preferences)
        self._apply_file_open_routing(initial_preferences)
        self.operation_queue_manager = OperationQueueManager(
            preferences=self._preferences_to_operation_execution(
                initial_preferences
            ),
            parent=self.app,
        )
        self.operation_queue_model = OperationQueueTableModel(
            self.operation_queue_manager
        )
        self.windows: list[ExplorerWindow] = []
        self._queue_windows: list[QMainWindow] = []
        self._is_raising_windows = False
        self._activation_pass_done_for_current_active_state = False
        self._last_closed_window_id: str | None = None

        self.app.aboutToQuit.connect(self.save_session)
        self.app.applicationStateChanged.connect(self._on_application_state_changed)

    def new_window(
        self,
        from_window: ExplorerWindow | None = None,
        *,
        window_id: str | None = None,
        show: bool = True,
        roots_provider: Callable[[Path | None], list[Path]] | None = None,
    ) -> ExplorerWindow:
        initial_path = Path.home()
        if from_window is not None:
            active_panel = from_window.active_panel()
            if active_panel is not None:
                initial_path = active_panel.current_path()
            if roots_provider is None:
                roots_provider = from_window.roots_provider

        window = ExplorerWindow(
            controller=self,
            settings=self.settings,
            window_id=window_id,
            initial_path=initial_path,
            roots_provider=roots_provider,
        )
        window.request_new_window.connect(
            lambda w=window: self.new_window(from_window=w)
        )
        window.window_activated.connect(lambda w=window: self._on_window_activated(w))

        if from_window is not None:
            geo = from_window.geometry()
            window.resize(geo.width(), geo.height())
            window.move(geo.x() + 30, geo.y() + 30)

        self.windows.append(window)
        if show:
            window.show()
        return window

    def close_window(self, window: ExplorerWindow) -> None:
        # Persist the last closed window so app restart can restore it.
        window.save_to_settings()
        if window in self.windows:
            was_last = len(self.windows) == 1
            self.windows.remove(window)
            if was_last:
                self._last_closed_window_id = window.window_id

    def bring_all_windows_to_front(self, restore_minimized: bool = True) -> None:
        if self._is_raising_windows:
            return

        self._is_raising_windows = True
        try:
            managed_windows = list(self.windows)
            for window in managed_windows:
                if (
                    restore_minimized
                    and window.windowState() & Qt.WindowState.WindowMinimized
                ):
                    window.showNormal()
                window.raise_()
        finally:
            self._is_raising_windows = False

    def save_session(self) -> None:
        window_ids: list[str] = []
        for window in list(self.windows):
            if not window.isVisible():
                continue
            window.save_to_settings()
            window_ids.append(window.window_id)

        if not window_ids and self._last_closed_window_id is not None:
            window_ids = [self._last_closed_window_id]

        self.settings.set_session_window_ids(window_ids)
        self.settings.sync()

    def restore_session(self) -> None:
        window_ids = self.settings.session_window_ids()
        if not window_ids:
            self.new_window(show=True)
            return

        for window_id in window_ids:
            window = self.new_window(window_id=window_id, show=False)
            window.restore_from_settings()
            window.show()

    def _on_window_activated(self, _window: ExplorerWindow | None = None) -> None:
        if self._activation_pass_done_for_current_active_state:
            return

        self._activation_pass_done_for_current_active_state = True
        self.bring_all_windows_to_front(restore_minimized=True)

    def _on_application_state_changed(self, state: Qt.ApplicationState) -> None:
        if state != Qt.ApplicationState.ApplicationActive:
            self._activation_pass_done_for_current_active_state = False

    def run(self) -> int:
        self.restore_session()
        return self.app.exec()

    def current_ui_preferences(self) -> UiPreferences:
        return self.settings.ui_preferences()

    def preview_ui_preferences(self, preferences: UiPreferences) -> None:
        self._apply_application_font(preferences)
        self._apply_file_open_routing(preferences)
        self.operation_queue_manager.set_preferences(
            self._preferences_to_operation_execution(preferences)
        )
        for window in list(self.windows):
            window.apply_ui_preferences(preferences)

    def apply_ui_preferences(self, preferences: UiPreferences) -> None:
        self.settings.set_ui_preferences(preferences)
        self.settings.sync()
        self.preview_ui_preferences(preferences)

    def broadcast_column_widths(
        self,
        widths: list[object],
        *,
        source_window: ExplorerWindow | None = None,
        source_panel_id: int | None = None,
        source_tab: object | None = None,
    ) -> None:
        for window in list(self.windows):
            window.apply_column_widths_all_panels(
                widths,
                source_panel_id=source_panel_id if window is source_window else None,
                source_tab=source_tab if window is source_window else None,
            )

    def _apply_application_font(self, preferences: UiPreferences) -> None:
        self.app.setFont(self._effective_application_font(preferences))

    def _effective_application_font(self, preferences: UiPreferences) -> QFont:
        font = QFont(self._default_app_font)
        family = str(preferences.app_font_family or "").strip()
        if family:
            font.setFamily(family)
        size_pt = int(preferences.app_font_size_pt)
        if size_pt > 0:
            font.setPointSize(size_pt)
        return font

    def _apply_file_open_routing(self, preferences: UiPreferences) -> None:
        file_ops.configure_open_routing(
            default_editor_executable=preferences.default_editor_executable,
            default_viewer_executable=preferences.default_viewer_executable,
            overrides_json=preferences.file_open_overrides_json,
        )

    def show_queue_floating_window(self) -> QMainWindow:
        for existing in list(self._queue_windows):
            if existing.isVisible():
                existing.raise_()
                existing.activateWindow()
                return existing
        window = QMainWindow()
        window.setWindowTitle("Operation Queue")
        panel = OperationQueuePanel(
            manager=self.operation_queue_manager,
            model=self.operation_queue_model,
            parent=window,
        )
        window.setCentralWidget(panel)
        window.resize(900, 380)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.destroyed.connect(
            lambda _obj=None, w=window: self._on_queue_window_destroyed(w)
        )
        self._queue_windows.append(window)
        window.show()
        window.raise_()
        return window

    def _on_queue_window_destroyed(self, window: QMainWindow) -> None:
        if window in self._queue_windows:
            self._queue_windows.remove(window)

    def _preferences_to_operation_execution(
        self,
        preferences: UiPreferences,
    ) -> OperationExecutionPreferences:
        resolved_cmd, resolved_robocopy = resolve_system_command_paths()
        resolved_copy_move = resolve_copy_move_backend_args(
            robocopy_options=preferences.robocopy_structured_options,
            teracopy_options=preferences.teracopy_structured_options,
            unstoppable_options=preferences.unstoppable_structured_options,
            external_copymove_options=preferences.external_copymove_structured_options,
        )
        return OperationExecutionPreferences(
            default_copy_move_backend=preferences.default_copy_move_backend,
            default_delete_backend=preferences.default_delete_backend,
            default_dispatch_mode=preferences.default_operation_dispatch_mode,
            default_conflict_policy=preferences.default_operation_conflict_policy,
            shortcut_behavior=preferences.operation_shortcut_behavior,
            queue_view_mode=preferences.operation_queue_view_mode,
            default_editor_executable=preferences.default_editor_executable,
            default_viewer_executable=preferences.default_viewer_executable,
            file_open_overrides_json=preferences.file_open_overrides_json,
            use_extended_paths_robocopy=preferences.use_extended_paths_robocopy,
            use_extended_paths_teracopy=preferences.use_extended_paths_teracopy,
            use_extended_paths_unstoppable=preferences.use_extended_paths_unstoppable,
            use_extended_paths_external_copymove=preferences.use_extended_paths_external_copymove,
            use_extended_paths_cmd_delete=preferences.use_extended_paths_cmd_delete,
            use_extended_paths_powershell_delete=preferences.use_extended_paths_powershell_delete,
            use_extended_paths_rimraf=preferences.use_extended_paths_rimraf,
            use_extended_paths_external_delete=preferences.use_extended_paths_external_delete,
            script_editor_executable=preferences.default_editor_executable,
            teracopy_executable=preferences.teracopy_executable,
            teracopy_args_template=resolved_copy_move.teracopy_args_template,
            unstoppable_executable=preferences.unstoppable_executable,
            unstoppable_args_template=resolved_copy_move.unstoppable_args_template,
            generic_copymove_executable=preferences.generic_copymove_executable,
            generic_copymove_args_template=resolved_copy_move.external_copymove_args_template,
            generic_delete_executable=preferences.generic_delete_executable,
            generic_delete_args_template=preferences.generic_delete_args_template,
            robocopy_copy_args=resolved_copy_move.robocopy_copy_args,
            robocopy_move_args=resolved_copy_move.robocopy_move_args,
            cmd_delete_args=preferences.cmd_delete_args,
            powershell_delete_args=preferences.powershell_delete_args,
            rimraf_executable=preferences.rimraf_executable,
            rimraf_args_template=preferences.rimraf_args_template,
            resolved_cmd_path=resolved_cmd,
            resolved_robocopy_path=resolved_robocopy,
        )

    def _bootstrap_companion_tools_once(self) -> None:
        if self.settings.ops_companion_bootstrap_done:
            return
        preferences = self.settings.ui_preferences()
        resolved = resolve_companion_tool_paths(
            self._preferences_to_operation_execution(preferences)
        )
        changed = False
        if preferences.teracopy_executable != resolved.teracopy_executable:
            self.settings.teracopy_executable = resolved.teracopy_executable
            changed = True
        if preferences.unstoppable_executable != resolved.unstoppable_executable:
            self.settings.unstoppable_executable = resolved.unstoppable_executable
            changed = True
        if preferences.rimraf_executable != resolved.rimraf_executable:
            self.settings.rimraf_executable = resolved.rimraf_executable
            changed = True
        self.settings.ops_companion_bootstrap_done = True
        changed = True
        if changed:
            self.settings.sync()
