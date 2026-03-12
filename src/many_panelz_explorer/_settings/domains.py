from __future__ import annotations

from typing import Any, cast

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


class UiSettingsDomain(SettingsDomainBase, SettingsRegistry):
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

    def _normalized_byte_separators(self) -> tuple[str, str]:
        return normalize.normalize_byte_separators(
            self._storage.value(
                self.BYTES_THOUSANDS_SEPARATOR_KEY,
                self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            ),
            self._storage.value(
                self.BYTES_DECIMAL_SEPARATOR_KEY,
                self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
            ),
            fallback_thousands=self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            fallback_decimal=self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
        )

    def set_byte_separators(self, thousands_raw: str, decimal_raw: str) -> None:
        thousands, decimal = normalize.normalize_byte_separators(
            thousands_raw,
            decimal_raw,
            fallback_thousands=self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            fallback_decimal=self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
        )
        self._storage.set_value(self.BYTES_THOUSANDS_SEPARATOR_KEY, thousands)
        self._storage.set_value(self.BYTES_DECIMAL_SEPARATOR_KEY, decimal)

    @property
    def byte_thousands_separator(self) -> str:
        thousands, _ = self._normalized_byte_separators()
        return thousands

    @byte_thousands_separator.setter
    def byte_thousands_separator(self, value: str) -> None:
        normalized = normalize.normalize_byte_separator(
            value,
            fallback=self.DEFAULT_BYTES_THOUSANDS_SEPARATOR,
            allow_empty=True,
        )
        self._storage.set_value(self.BYTES_THOUSANDS_SEPARATOR_KEY, normalized)

    @property
    def byte_decimal_separator(self) -> str:
        _, decimal = self._normalized_byte_separators()
        return decimal

    @byte_decimal_separator.setter
    def byte_decimal_separator(self, value: str) -> None:
        normalized = normalize.normalize_byte_separator(
            value,
            fallback=self.DEFAULT_BYTES_DECIMAL_SEPARATOR,
            allow_empty=False,
        )
        self._storage.set_value(self.BYTES_DECIMAL_SEPARATOR_KEY, normalized)

    @property
    def file_list_byte_format_mode(self) -> str:
        return normalize.normalize_byte_format_mode(
            self._storage.value(
                self.FILE_LIST_BYTE_FORMAT_MODE_KEY,
                self.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
            ),
            fallback=self.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
            allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
        )

    @file_list_byte_format_mode.setter
    def file_list_byte_format_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.FILE_LIST_BYTE_FORMAT_MODE_KEY,
            normalize.normalize_byte_format_mode(
                mode,
                fallback=self.DEFAULT_FILE_LIST_BYTE_FORMAT_MODE,
                allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
            ),
        )

    @property
    def file_list_byte_custom_template(self) -> str:
        return normalize.normalize_byte_custom_template(
            self._storage.value(
                self.FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY,
                self.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE,
            ),
            fallback=self.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE,
        )

    @file_list_byte_custom_template.setter
    def file_list_byte_custom_template(self, value: str) -> None:
        self._storage.set_value(
            self.FILE_LIST_BYTE_CUSTOM_TEMPLATE_KEY,
            normalize.normalize_byte_custom_template(
                value,
                fallback=self.DEFAULT_FILE_LIST_BYTE_CUSTOM_TEMPLATE,
            ),
        )

    @property
    def status_bar_byte_format_mode(self) -> str:
        return normalize.normalize_byte_format_mode(
            self._storage.value(
                self.STATUS_BAR_BYTE_FORMAT_MODE_KEY,
                self.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
            ),
            fallback=self.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
            allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
        )

    @status_bar_byte_format_mode.setter
    def status_bar_byte_format_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.STATUS_BAR_BYTE_FORMAT_MODE_KEY,
            normalize.normalize_byte_format_mode(
                mode,
                fallback=self.DEFAULT_STATUS_BAR_BYTE_FORMAT_MODE,
                allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
            ),
        )

    @property
    def status_bar_byte_custom_template(self) -> str:
        return normalize.normalize_byte_custom_template(
            self._storage.value(
                self.STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY,
                self.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE,
            ),
            fallback=self.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE,
        )

    @status_bar_byte_custom_template.setter
    def status_bar_byte_custom_template(self, value: str) -> None:
        self._storage.set_value(
            self.STATUS_BAR_BYTE_CUSTOM_TEMPLATE_KEY,
            normalize.normalize_byte_custom_template(
                value,
                fallback=self.DEFAULT_STATUS_BAR_BYTE_CUSTOM_TEMPLATE,
            ),
        )

    @property
    def status_bar_storage_label_template(self) -> str:
        return normalize.normalize_status_storage_label_template(
            self._storage.value(
                self.STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY,
                self.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE,
            ),
            fallback=self.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE,
        )

    @status_bar_storage_label_template.setter
    def status_bar_storage_label_template(self, value: str) -> None:
        self._storage.set_value(
            self.STATUS_BAR_STORAGE_LABEL_TEMPLATE_KEY,
            normalize.normalize_status_storage_label_template(
                value,
                fallback=self.DEFAULT_STATUS_BAR_STORAGE_LABEL_TEMPLATE,
            ),
        )

    @property
    def properties_byte_format_mode(self) -> str:
        return normalize.normalize_byte_format_mode(
            self._storage.value(
                self.PROPERTIES_BYTE_FORMAT_MODE_KEY,
                self.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
            ),
            fallback=self.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
            allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
        )

    @properties_byte_format_mode.setter
    def properties_byte_format_mode(self, mode: str) -> None:
        self._storage.set_value(
            self.PROPERTIES_BYTE_FORMAT_MODE_KEY,
            normalize.normalize_byte_format_mode(
                mode,
                fallback=self.DEFAULT_PROPERTIES_BYTE_FORMAT_MODE,
                allowed_modes=self.ALLOWED_BYTE_FORMAT_MODES,
            ),
        )

    @property
    def properties_byte_custom_template(self) -> str:
        return normalize.normalize_byte_custom_template(
            self._storage.value(
                self.PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY,
                self.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE,
            ),
            fallback=self.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE,
        )

    @properties_byte_custom_template.setter
    def properties_byte_custom_template(self, value: str) -> None:
        self._storage.set_value(
            self.PROPERTIES_BYTE_CUSTOM_TEMPLATE_KEY,
            normalize.normalize_byte_custom_template(
                value,
                fallback=self.DEFAULT_PROPERTIES_BYTE_CUSTOM_TEMPLATE,
            ),
        )

    @property
    def app_font_family(self) -> str:
        return normalize.normalize_font_family(
            self._storage.value(self.APP_FONT_FAMILY_KEY, self.DEFAULT_APP_FONT_FAMILY)
        )

    @app_font_family.setter
    def app_font_family(self, family: str) -> None:
        self._storage.set_value(
            self.APP_FONT_FAMILY_KEY, normalize.normalize_font_family(family)
        )

    @property
    def app_font_size_pt(self) -> int:
        return normalize.normalize_font_size(
            self._storage.value(
                self.APP_FONT_SIZE_PT_KEY, self.DEFAULT_APP_FONT_SIZE_PT
            ),
            fallback=self.DEFAULT_APP_FONT_SIZE_PT,
            allow_zero=True,
        )

    @app_font_size_pt.setter
    def app_font_size_pt(self, size_pt: int) -> None:
        self._storage.set_value(
            self.APP_FONT_SIZE_PT_KEY,
            normalize.normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_APP_FONT_SIZE_PT,
                allow_zero=True,
            ),
        )

    @property
    def file_list_use_app_font(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.FILE_LIST_USE_APP_FONT_KEY,
                self.DEFAULT_FILE_LIST_USE_APP_FONT,
            )
        )

    @file_list_use_app_font.setter
    def file_list_use_app_font(self, enabled: bool) -> None:
        self._storage.set_value(self.FILE_LIST_USE_APP_FONT_KEY, bool(enabled))

    @property
    def file_list_font_family(self) -> str:
        return normalize.normalize_font_family(
            self._storage.value(
                self.FILE_LIST_FONT_FAMILY_KEY,
                self.DEFAULT_FILE_LIST_FONT_FAMILY,
            )
        )

    @file_list_font_family.setter
    def file_list_font_family(self, family: str) -> None:
        self._storage.set_value(
            self.FILE_LIST_FONT_FAMILY_KEY,
            normalize.normalize_font_family(family),
        )

    @property
    def file_list_font_size_pt(self) -> int:
        return normalize.normalize_font_size(
            self._storage.value(
                self.FILE_LIST_FONT_SIZE_PT_KEY,
                self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
        )

    @file_list_font_size_pt.setter
    def file_list_font_size_pt(self, size_pt: int) -> None:
        self._storage.set_value(
            self.FILE_LIST_FONT_SIZE_PT_KEY,
            normalize.normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
        )

    @property
    def navigation_use_app_font(self) -> bool:
        return normalize.normalize_bool(
            self._storage.value(
                self.NAVIGATION_USE_APP_FONT_KEY,
                self.DEFAULT_NAVIGATION_USE_APP_FONT,
            )
        )

    @navigation_use_app_font.setter
    def navigation_use_app_font(self, enabled: bool) -> None:
        self._storage.set_value(self.NAVIGATION_USE_APP_FONT_KEY, bool(enabled))

    @property
    def navigation_font_family(self) -> str:
        return normalize.normalize_font_family(
            self._storage.value(
                self.NAVIGATION_FONT_FAMILY_KEY,
                self.DEFAULT_NAVIGATION_FONT_FAMILY,
            )
        )

    @navigation_font_family.setter
    def navigation_font_family(self, family: str) -> None:
        self._storage.set_value(
            self.NAVIGATION_FONT_FAMILY_KEY,
            normalize.normalize_font_family(family),
        )

    @property
    def navigation_font_size_pt(self) -> int:
        return normalize.normalize_font_size(
            self._storage.value(
                self.NAVIGATION_FONT_SIZE_PT_KEY,
                self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
        )

    @navigation_font_size_pt.setter
    def navigation_font_size_pt(self, size_pt: int) -> None:
        self._storage.set_value(
            self.NAVIGATION_FONT_SIZE_PT_KEY,
            normalize.normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
        )

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

    @property
    def active_panel_tint_color_hex(self) -> str:
        return normalize.normalize_color_hex(
            self._storage.value(
                self.ACTIVE_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
        )

    @active_panel_tint_color_hex.setter
    def active_panel_tint_color_hex(self, color_hex: str) -> None:
        self._storage.set_value(
            self.ACTIVE_PANEL_TINT_COLOR_KEY,
            normalize.normalize_color_hex(
                color_hex, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def active_panel_tint_intensity_percent(self) -> int:
        return normalize.normalize_percent(
            self._storage.value(
                self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
        )

    @active_panel_tint_intensity_percent.setter
    def active_panel_tint_intensity_percent(self, percent: int) -> None:
        self._storage.set_value(
            self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
            normalize.normalize_percent(
                percent, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT
            ),
        )

    @property
    def target_panel_tint_color_hex(self) -> str:
        return normalize.normalize_color_hex(
            self._storage.value(
                self.TARGET_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
        )

    @target_panel_tint_color_hex.setter
    def target_panel_tint_color_hex(self, color_hex: str) -> None:
        self._storage.set_value(
            self.TARGET_PANEL_TINT_COLOR_KEY,
            normalize.normalize_color_hex(
                color_hex, fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def target_panel_tint_intensity_percent(self) -> int:
        return normalize.normalize_percent(
            self._storage.value(
                self.TARGET_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
        )

    @target_panel_tint_intensity_percent.setter
    def target_panel_tint_intensity_percent(self, percent: int) -> None:
        self._storage.set_value(
            self.TARGET_PANEL_TINT_INTENSITY_KEY,
            normalize.normalize_percent(
                percent, fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT
            ),
        )


class OpsSettingsDomain(SettingsDomainBase, SettingsRegistry):
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


class SessionSettingsDomain(SettingsDomainBase, SettingsRegistry):
    def window_key(self, window_id: str, suffix: str) -> str:
        return f"ui/windows/{window_id}/{suffix}"

    def session_window_ids(self) -> list[str]:
        data = self._storage.get_json(self.SESSION_WINDOWS_KEY, [])
        if not isinstance(data, list):
            return []
        return [str(item) for item in cast("list[Any]", data)]

    def set_session_window_ids(self, window_ids: list[str]) -> None:
        self._storage.set_json(self.SESSION_WINDOWS_KEY, window_ids)

    @property
    def settings_dialog_last_section(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.SETTINGS_DIALOG_LAST_SECTION_KEY,
                self.DEFAULT_SETTINGS_DIALOG_LAST_SECTION,
            ),
            fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SECTION,
        )

    @settings_dialog_last_section.setter
    def settings_dialog_last_section(self, value: str) -> None:
        self._storage.set_value(
            self.SETTINGS_DIALOG_LAST_SECTION_KEY,
            normalize.normalize_text(
                value,
                fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SECTION,
            ),
        )

    @property
    def settings_dialog_last_subsection(self) -> str:
        return normalize.normalize_text(
            self._storage.value(
                self.SETTINGS_DIALOG_LAST_SUBSECTION_KEY,
                self.DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION,
            ),
            fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION,
        )

    @settings_dialog_last_subsection.setter
    def settings_dialog_last_subsection(self, value: str) -> None:
        self._storage.set_value(
            self.SETTINGS_DIALOG_LAST_SUBSECTION_KEY,
            normalize.normalize_text(
                value,
                fallback=self.DEFAULT_SETTINGS_DIALOG_LAST_SUBSECTION,
            ),
        )

    def saved_views(self) -> dict[str, dict[str, Any]]:
        data = self._storage.get_json(self.SAVED_VIEWS_KEY, {})
        if not isinstance(data, dict):
            return {}
        views: dict[str, dict[str, Any]] = {}
        for key, value in cast("dict[str, Any]", data).items():
            if isinstance(value, dict):
                views[str(key)] = dict(cast("dict[str, Any]", value))
        return views

    def list_saved_views(self) -> list[str]:
        return sorted(self.saved_views().keys(), key=str.casefold)

    def get_saved_view(self, name: str) -> dict[str, Any] | None:
        return self.saved_views().get(name)

    def set_saved_view(self, name: str, payload: dict[str, Any]) -> None:
        views = self.saved_views()
        views[name] = payload
        self._storage.set_json(self.SAVED_VIEWS_KEY, views)
