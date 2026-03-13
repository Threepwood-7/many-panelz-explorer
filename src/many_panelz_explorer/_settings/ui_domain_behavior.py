"""Behavior and visibility settings for the UI domain."""

from __future__ import annotations

from threep_commons.settings import SettingsDomainBase

from . import normalize
from .registry import SettingsRegistry


class UiBehaviorSettingsMixin(SettingsDomainBase, SettingsRegistry):
    """Persist behavior, visibility, and context-tool preferences."""

    @property
    def new_context_mode(self) -> str:
        value = str(self._storage.value(self.NEW_CONTEXT_MODE_KEY, "clone_active_path"))
        mode = value.strip().lower()
        if mode not in self.ALLOWED_NEW_CONTEXT_MODES:
            return "clone_active_path"
        return mode

    @new_context_mode.setter
    def new_context_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        if normalized not in self.ALLOWED_NEW_CONTEXT_MODES:
            normalized = "clone_active_path"
        self._storage.set_value(self.NEW_CONTEXT_MODE_KEY, normalized)

    @property
    def show_hidden_default(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.SHOW_HIDDEN_DEFAULT_KEY, True)
        )

    @show_hidden_default.setter
    def show_hidden_default(self, enabled: bool) -> None:
        self._storage.set_value(self.SHOW_HIDDEN_DEFAULT_KEY, bool(enabled))

    @property
    def show_root_dropdown(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.SHOW_ROOT_DROPDOWN_KEY, False)
        )

    @show_root_dropdown.setter
    def show_root_dropdown(self, enabled: bool) -> None:
        self._storage.set_value(self.SHOW_ROOT_DROPDOWN_KEY, bool(enabled))

    @property
    def show_storage_overview_status_row(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.SHOW_STORAGE_OVERVIEW_STATUS_ROW_KEY,
                self.DEFAULT_SHOW_STORAGE_OVERVIEW_STATUS_ROW,
            )
        )

    @show_storage_overview_status_row.setter
    def show_storage_overview_status_row(self, enabled: bool) -> None:
        self._storage.set_value(
            self.SHOW_STORAGE_OVERVIEW_STATUS_ROW_KEY, bool(enabled)
        )

    @property
    def column_width_auto_align_mode(self) -> str:
        value = str(
            self._storage.value(
                self.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY,
                self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE,
            )
        )
        mode = value.strip().lower()
        if mode not in self.ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES:
            return self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        return mode

    @column_width_auto_align_mode.setter
    def column_width_auto_align_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        if normalized not in self.ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES:
            normalized = self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        self._storage.set_value(self.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY, normalized)

    @property
    def show_refresh_button(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.SHOW_REFRESH_BUTTON_KEY, True)
        )

    @show_refresh_button.setter
    def show_refresh_button(self, enabled: bool) -> None:
        self._storage.set_value(self.SHOW_REFRESH_BUTTON_KEY, bool(enabled))

    @property
    def show_root_buttons(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.SHOW_ROOT_BUTTONS_KEY, True)
        )

    @show_root_buttons.setter
    def show_root_buttons(self, enabled: bool) -> None:
        self._storage.set_value(self.SHOW_ROOT_BUTTONS_KEY, bool(enabled))

    @property
    def show_address_bar(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.SHOW_ADDRESS_BAR_KEY, True)
        )

    @show_address_bar.setter
    def show_address_bar(self, enabled: bool) -> None:
        self._storage.set_value(self.SHOW_ADDRESS_BAR_KEY, bool(enabled))

    @property
    def show_navigation_buttons(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(self.SHOW_NAVIGATION_BUTTONS_KEY, True)
        )

    @show_navigation_buttons.setter
    def show_navigation_buttons(self, enabled: bool) -> None:
        self._storage.set_value(self.SHOW_NAVIGATION_BUTTONS_KEY, bool(enabled))

    @property
    def context_immediate_child_scan_cap(self) -> int:
        return normalize.normalize_positive_int(
            self._storage.value(
                self.CONTEXT_IMMEDIATE_CHILD_SCAN_CAP_KEY,
                self.DEFAULT_CONTEXT_IMMEDIATE_CHILD_SCAN_CAP,
            ),
            fallback=self.DEFAULT_CONTEXT_IMMEDIATE_CHILD_SCAN_CAP,
            minimum=1,
            maximum=10_000,
        )

    @context_immediate_child_scan_cap.setter
    def context_immediate_child_scan_cap(self, value: int) -> None:
        self._storage.set_value(
            self.CONTEXT_IMMEDIATE_CHILD_SCAN_CAP_KEY,
            normalize.normalize_positive_int(
                value,
                fallback=self.DEFAULT_CONTEXT_IMMEDIATE_CHILD_SCAN_CAP,
                minimum=1,
                maximum=10_000,
            ),
        )

    @property
    def context_tool_code_editor_exe_path(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.CONTEXT_TOOL_CODE_EDITOR_EXE_PATH_KEY,
                self.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH,
            ),
            fallback=self.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH,
        )

    @context_tool_code_editor_exe_path.setter
    def context_tool_code_editor_exe_path(self, value: str) -> None:
        self._storage.set_value(
            self.CONTEXT_TOOL_CODE_EDITOR_EXE_PATH_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_EXE_PATH
            ),
        )

    @property
    def context_tool_code_editor_args_template(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE_KEY,
                self.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE,
        )

    @context_tool_code_editor_args_template.setter
    def context_tool_code_editor_args_template(self, value: str) -> None:
        self._storage.set_value(
            self.CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE_KEY,
            normalize.normalize_text(
                value, fallback=self.DEFAULT_CONTEXT_TOOL_CODE_EDITOR_ARGS_TEMPLATE
            ),
        )

    @property
    def context_tool_git_gui_exe_path(self) -> str:
        return normalize.normalize_windows_path_text(
            self._storage.value(
                self.CONTEXT_TOOL_GIT_GUI_EXE_PATH_KEY,
                self.DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH,
            ),
            fallback=self.DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH,
        )

    @context_tool_git_gui_exe_path.setter
    def context_tool_git_gui_exe_path(self, value: str) -> None:
        self._storage.set_value(
            self.CONTEXT_TOOL_GIT_GUI_EXE_PATH_KEY,
            normalize.normalize_windows_path_text(
                value, fallback=self.DEFAULT_CONTEXT_TOOL_GIT_GUI_EXE_PATH
            ),
        )

    @property
    def context_tool_git_gui_args_template(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE_KEY,
                self.DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE,
        )

    @context_tool_git_gui_args_template.setter
    def context_tool_git_gui_args_template(self, value: str) -> None:
        self._storage.set_value(
            self.CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE_KEY,
            normalize.normalize_text(
                value, fallback=self.DEFAULT_CONTEXT_TOOL_GIT_GUI_ARGS_TEMPLATE
            ),
        )
