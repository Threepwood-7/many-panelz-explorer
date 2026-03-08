from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from threep_commons.paths import configure_qsettings, resolve_app_data_dir

from .constants import (
    APP_DISPLAY_NAME,
    APP_IDENTITY,
    SETTINGS_APP_NAME,
    SETTINGS_ORG_NAME,
)
from .settings import SettingsManager, UiPreferences
from .window import ExplorerWindow

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


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
        self._apply_application_font(self.settings.ui_preferences())
        self.windows: list[ExplorerWindow] = []
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
        for window in list(self.windows):
            window.apply_ui_preferences(preferences)

    def apply_ui_preferences(self, preferences: UiPreferences) -> None:
        self.settings.set_ui_preferences(preferences)
        self.settings.sync()
        self.preview_ui_preferences(preferences)

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
