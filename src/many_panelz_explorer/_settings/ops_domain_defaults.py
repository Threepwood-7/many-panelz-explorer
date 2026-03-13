"""Default operation and open-tool settings."""

from __future__ import annotations

from threep_commons.settings import SettingsDomainBase

from many_panelz_explorer._operations.normalize import (
    normalize_conflict_policy,
    normalize_copy_move_backend,
    normalize_delete_backend,
    normalize_dispatch_mode,
    normalize_queue_view_mode,
    normalize_shortcut_behavior,
)

from . import normalize
from .registry import SettingsRegistry


class OpsDefaultSettingsMixin(SettingsDomainBase, SettingsRegistry):
    """Persist operation defaults and file-open tool preferences."""

    @property
    def default_copy_move_backend(self) -> str:
        return normalize_copy_move_backend(
            self._storage.value(
                self.DEFAULT_COPY_MOVE_BACKEND_KEY,
                self.DEFAULT_COPY_MOVE_BACKEND,
            )
        )

    @default_copy_move_backend.setter
    def default_copy_move_backend(self, backend: str) -> None:
        self._storage.set_value(
            self.DEFAULT_COPY_MOVE_BACKEND_KEY,
            normalize_copy_move_backend(backend),
        )

    @property
    def default_delete_backend(self) -> str:
        return normalize_delete_backend(
            self._storage.value(
                self.DEFAULT_DELETE_BACKEND_KEY,
                self.DEFAULT_DELETE_BACKEND,
            )
        )

    @default_delete_backend.setter
    def default_delete_backend(self, backend: str) -> None:
        self._storage.set_value(
            self.DEFAULT_DELETE_BACKEND_KEY,
            normalize_delete_backend(backend),
        )

    @property
    def default_operation_dispatch_mode(self) -> str:
        return normalize_dispatch_mode(
            self._storage.value(
                self.DEFAULT_OPERATION_DISPATCH_MODE_KEY,
                self.DEFAULT_OPERATION_DISPATCH_MODE,
            )
        )

    @default_operation_dispatch_mode.setter
    def default_operation_dispatch_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.DEFAULT_OPERATION_DISPATCH_MODE_KEY,
            normalize_dispatch_mode(mode),
        )

    @property
    def default_operation_conflict_policy(self) -> str:
        return normalize_conflict_policy(
            self._storage.value(
                self.DEFAULT_OPERATION_CONFLICT_POLICY_KEY,
                self.DEFAULT_OPERATION_CONFLICT_POLICY,
            )
        )

    @default_operation_conflict_policy.setter
    def default_operation_conflict_policy(self, policy: str) -> None:
        self._storage.set_value(
            self.DEFAULT_OPERATION_CONFLICT_POLICY_KEY,
            normalize_conflict_policy(policy),
        )

    @property
    def operation_shortcut_behavior(self) -> str:
        return normalize_shortcut_behavior(
            self._storage.value(
                self.OPERATION_SHORTCUT_BEHAVIOR_KEY,
                self.DEFAULT_OPERATION_SHORTCUT_BEHAVIOR,
            )
        )

    @operation_shortcut_behavior.setter
    def operation_shortcut_behavior(self, behavior: str) -> None:
        self._storage.set_value(
            self.OPERATION_SHORTCUT_BEHAVIOR_KEY,
            normalize_shortcut_behavior(behavior),
        )

    @property
    def operation_queue_view_mode(self) -> str:
        return normalize_queue_view_mode(
            self._storage.value(
                self.OPERATION_QUEUE_VIEW_MODE_KEY,
                self.DEFAULT_OPERATION_QUEUE_VIEW_MODE,
            )
        )

    @operation_queue_view_mode.setter
    def operation_queue_view_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.OPERATION_QUEUE_VIEW_MODE_KEY,
            normalize_queue_view_mode(mode),
        )

    @property
    def default_editor_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.DEFAULT_EDITOR_EXECUTABLE_KEY,
                self.DEFAULT_DEFAULT_EDITOR_EXECUTABLE,
            ),
            fallback=self.DEFAULT_DEFAULT_EDITOR_EXECUTABLE,
        )

    @default_editor_executable.setter
    def default_editor_executable(self, value: str) -> None:
        self._storage.set_value(
            self.DEFAULT_EDITOR_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_DEFAULT_EDITOR_EXECUTABLE
            ),
        )

    @property
    def default_viewer_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.DEFAULT_VIEWER_EXECUTABLE_KEY,
                self.DEFAULT_DEFAULT_VIEWER_EXECUTABLE,
            ),
            fallback=self.DEFAULT_DEFAULT_VIEWER_EXECUTABLE,
        )

    @default_viewer_executable.setter
    def default_viewer_executable(self, value: str) -> None:
        self._storage.set_value(
            self.DEFAULT_VIEWER_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_DEFAULT_VIEWER_EXECUTABLE
            ),
        )

    @property
    def file_open_overrides_json(self) -> str:
        return normalize.normalize_overrides_json(
            self._storage.value(
                self.FILE_OPEN_OVERRIDES_JSON_KEY,
                self.DEFAULT_FILE_OPEN_OVERRIDES_JSON,
            ),
            fallback=self.DEFAULT_FILE_OPEN_OVERRIDES_JSON,
        )

    @file_open_overrides_json.setter
    def file_open_overrides_json(self, value: str) -> None:
        self._storage.set_value(
            self.FILE_OPEN_OVERRIDES_JSON_KEY,
            normalize.normalize_overrides_json(
                value,
                fallback=self.DEFAULT_FILE_OPEN_OVERRIDES_JSON,
            ),
        )
