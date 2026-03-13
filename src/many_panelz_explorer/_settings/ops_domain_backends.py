"""Backend command and structured-option settings."""

from __future__ import annotations

from threep_commons.settings import SettingsDomainBase

from many_panelz_explorer._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    external_copymove_options_payload,
    robocopy_options_payload,
    teracopy_options_payload,
    unstoppable_options_payload,
)

from . import normalize
from .registry import SettingsRegistry


class OpsBackendSettingsMixin(SettingsDomainBase, SettingsRegistry):
    """Persist backend executables, args, and structured option payloads."""

    @property
    def use_extended_paths_robocopy(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_ROBOCOPY_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_ROBOCOPY,
            )
        )

    @use_extended_paths_robocopy.setter
    def use_extended_paths_robocopy(self, enabled: bool) -> None:
        self._storage.set_value(self.USE_EXTENDED_PATHS_ROBOCOPY_KEY, bool(enabled))

    @property
    def use_extended_paths_teracopy(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_TERACOPY_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_TERACOPY,
            )
        )

    @use_extended_paths_teracopy.setter
    def use_extended_paths_teracopy(self, enabled: bool) -> None:
        self._storage.set_value(self.USE_EXTENDED_PATHS_TERACOPY_KEY, bool(enabled))

    @property
    def use_extended_paths_unstoppable(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_UNSTOPPABLE,
            )
        )

    @use_extended_paths_unstoppable.setter
    def use_extended_paths_unstoppable(self, enabled: bool) -> None:
        self._storage.set_value(self.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY, bool(enabled))

    @property
    def use_extended_paths_external_copymove(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE,
            )
        )

    @use_extended_paths_external_copymove.setter
    def use_extended_paths_external_copymove(self, enabled: bool) -> None:
        self._storage.set_value(
            self.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY, bool(enabled)
        )

    @property
    def use_extended_paths_cmd_delete(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_CMD_DELETE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_CMD_DELETE,
            )
        )

    @use_extended_paths_cmd_delete.setter
    def use_extended_paths_cmd_delete(self, enabled: bool) -> None:
        self._storage.set_value(self.USE_EXTENDED_PATHS_CMD_DELETE_KEY, bool(enabled))

    @property
    def use_extended_paths_powershell_delete(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_POWERSHELL_DELETE,
            )
        )

    @use_extended_paths_powershell_delete.setter
    def use_extended_paths_powershell_delete(self, enabled: bool) -> None:
        self._storage.set_value(
            self.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY, bool(enabled)
        )

    @property
    def use_extended_paths_rimraf(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_RIMRAF_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_RIMRAF,
            )
        )

    @use_extended_paths_rimraf.setter
    def use_extended_paths_rimraf(self, enabled: bool) -> None:
        self._storage.set_value(self.USE_EXTENDED_PATHS_RIMRAF_KEY, bool(enabled))

    @property
    def use_extended_paths_external_delete(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_DELETE,
            )
        )

    @use_extended_paths_external_delete.setter
    def use_extended_paths_external_delete(self, enabled: bool) -> None:
        self._storage.set_value(
            self.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY, bool(enabled)
        )

    @property
    def teracopy_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.TERACOPY_EXECUTABLE_KEY,
                self.DEFAULT_TERACOPY_EXECUTABLE,
            ),
            fallback=self.DEFAULT_TERACOPY_EXECUTABLE,
        )

    @teracopy_executable.setter
    def teracopy_executable(self, value: str) -> None:
        self._storage.set_value(
            self.TERACOPY_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_TERACOPY_EXECUTABLE
            ),
        )

    @property
    def unstoppable_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.UNSTOPPABLE_EXECUTABLE_KEY,
                self.DEFAULT_UNSTOPPABLE_EXECUTABLE,
            ),
            fallback=self.DEFAULT_UNSTOPPABLE_EXECUTABLE,
        )

    @unstoppable_executable.setter
    def unstoppable_executable(self, value: str) -> None:
        self._storage.set_value(
            self.UNSTOPPABLE_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_UNSTOPPABLE_EXECUTABLE
            ),
        )

    @property
    def generic_copymove_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.GENERIC_COPYMOVE_EXECUTABLE_KEY,
                self.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE,
            ),
            fallback=self.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE,
        )

    @generic_copymove_executable.setter
    def generic_copymove_executable(self, value: str) -> None:
        self._storage.set_value(
            self.GENERIC_COPYMOVE_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE
            ),
        )

    @property
    def generic_delete_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.GENERIC_DELETE_EXECUTABLE_KEY,
                self.DEFAULT_GENERIC_DELETE_EXECUTABLE,
            ),
            fallback=self.DEFAULT_GENERIC_DELETE_EXECUTABLE,
        )

    @generic_delete_executable.setter
    def generic_delete_executable(self, value: str) -> None:
        self._storage.set_value(
            self.GENERIC_DELETE_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_GENERIC_DELETE_EXECUTABLE
            ),
        )

    @property
    def generic_delete_args_template(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.GENERIC_DELETE_ARGS_TEMPLATE_KEY,
                self.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE,
        )

    @generic_delete_args_template.setter
    def generic_delete_args_template(self, value: str) -> None:
        self._storage.set_value(
            self.GENERIC_DELETE_ARGS_TEMPLATE_KEY,
            normalize.normalize_text(
                value, fallback=self.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE
            ),
        )

    @property
    def robocopy_structured_options(self) -> RobocopyBackendOptions:
        return normalize.normalize_robocopy_structured_options(
            self._storage.get_json(
                self.ROBOCOPY_STRUCTURED_OPTIONS_KEY,
                self.DEFAULT_ROBOCOPY_STRUCTURED_OPTIONS,
            )
        )

    @robocopy_structured_options.setter
    def robocopy_structured_options(self, value: RobocopyBackendOptions) -> None:
        normalized = normalize.normalize_robocopy_structured_options(
            robocopy_options_payload(value),
        )
        self._storage.set_json(
            self.ROBOCOPY_STRUCTURED_OPTIONS_KEY,
            robocopy_options_payload(normalized),
        )

    @property
    def teracopy_structured_options(self) -> TeraCopyBackendOptions:
        return normalize.normalize_teracopy_structured_options(
            self._storage.get_json(
                self.TERACOPY_STRUCTURED_OPTIONS_KEY,
                self.DEFAULT_TERACOPY_STRUCTURED_OPTIONS,
            )
        )

    @teracopy_structured_options.setter
    def teracopy_structured_options(self, value: TeraCopyBackendOptions) -> None:
        normalized = normalize.normalize_teracopy_structured_options(
            teracopy_options_payload(value),
        )
        self._storage.set_json(
            self.TERACOPY_STRUCTURED_OPTIONS_KEY,
            teracopy_options_payload(normalized),
        )

    @property
    def unstoppable_structured_options(self) -> UnstoppableBackendOptions:
        return normalize.normalize_unstoppable_structured_options(
            self._storage.get_json(
                self.UNSTOPPABLE_STRUCTURED_OPTIONS_KEY,
                self.DEFAULT_UNSTOPPABLE_STRUCTURED_OPTIONS,
            )
        )

    @unstoppable_structured_options.setter
    def unstoppable_structured_options(self, value: UnstoppableBackendOptions) -> None:
        normalized = normalize.normalize_unstoppable_structured_options(
            unstoppable_options_payload(value),
        )
        self._storage.set_json(
            self.UNSTOPPABLE_STRUCTURED_OPTIONS_KEY,
            unstoppable_options_payload(normalized),
        )

    @property
    def external_copymove_structured_options(self) -> ExternalCopyMoveBackendOptions:
        return normalize.normalize_external_copymove_structured_options(
            self._storage.get_json(
                self.EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS_KEY,
                self.DEFAULT_EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS,
            )
        )

    @external_copymove_structured_options.setter
    def external_copymove_structured_options(
        self, value: ExternalCopyMoveBackendOptions
    ) -> None:
        normalized = normalize.normalize_external_copymove_structured_options(
            external_copymove_options_payload(value),
        )
        self._storage.set_json(
            self.EXTERNAL_COPYMOVE_STRUCTURED_OPTIONS_KEY,
            external_copymove_options_payload(normalized),
        )

    @property
    def cmd_delete_args(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.CMD_DELETE_ARGS_KEY,
                self.DEFAULT_CMD_DELETE_ARGS,
            ),
            fallback=self.DEFAULT_CMD_DELETE_ARGS,
        )

    @cmd_delete_args.setter
    def cmd_delete_args(self, value: str) -> None:
        self._storage.set_value(
            self.CMD_DELETE_ARGS_KEY,
            normalize.normalize_text(value, fallback=self.DEFAULT_CMD_DELETE_ARGS),
        )

    @property
    def powershell_delete_args(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.POWERSHELL_DELETE_ARGS_KEY,
                self.DEFAULT_POWERSHELL_DELETE_ARGS,
            ),
            fallback=self.DEFAULT_POWERSHELL_DELETE_ARGS,
        )

    @powershell_delete_args.setter
    def powershell_delete_args(self, value: str) -> None:
        self._storage.set_value(
            self.POWERSHELL_DELETE_ARGS_KEY,
            normalize.normalize_text(
                value, fallback=self.DEFAULT_POWERSHELL_DELETE_ARGS
            ),
        )

    @property
    def rimraf_executable(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.RIMRAF_EXECUTABLE_KEY,
                self.DEFAULT_RIMRAF_EXECUTABLE,
            ),
            fallback=self.DEFAULT_RIMRAF_EXECUTABLE,
        )

    @rimraf_executable.setter
    def rimraf_executable(self, value: str) -> None:
        self._storage.set_value(
            self.RIMRAF_EXECUTABLE_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_RIMRAF_EXECUTABLE
            ),
        )

    @property
    def rimraf_args_template(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.RIMRAF_ARGS_TEMPLATE_KEY,
                self.DEFAULT_RIMRAF_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_RIMRAF_ARGS_TEMPLATE,
        )

    @rimraf_args_template.setter
    def rimraf_args_template(self, value: str) -> None:
        self._storage.set_value(
            self.RIMRAF_ARGS_TEMPLATE_KEY,
            normalize.normalize_text(value, fallback=self.DEFAULT_RIMRAF_ARGS_TEMPLATE),
        )

    @property
    def ops_companion_bootstrap_done(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.OPS_COMPANION_BOOTSTRAP_DONE_KEY, False)
        )

    @ops_companion_bootstrap_done.setter
    def ops_companion_bootstrap_done(self, done: bool) -> None:
        self._storage.set_value(self.OPS_COMPANION_BOOTSTRAP_DONE_KEY, bool(done))
