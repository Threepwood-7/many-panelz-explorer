from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from threep_commons.qsettings_store import create_qsettings

from .constants import APP_IDENTITY
from .operations import (
    BACKEND_PYTHON,
    BACKEND_RECYCLE_BIN,
    DEFAULT_CMD_DELETE_ARGS,
    DEFAULT_GENERIC_COPYMOVE_ARGS,
    DEFAULT_GENERIC_COPYMOVE_EXE,
    DEFAULT_GENERIC_DELETE_ARGS,
    DEFAULT_GENERIC_DELETE_EXE,
    DEFAULT_POWERSHELL_DELETE_ARGS,
    DEFAULT_RIMRAF_ARGS,
    DEFAULT_RIMRAF_EXE,
    DEFAULT_ROBOCOPY_COPY_ARGS,
    DEFAULT_ROBOCOPY_MOVE_ARGS,
    DEFAULT_TERA_COPY_ARGS,
    DEFAULT_TERA_COPY_EXE,
    DEFAULT_UNSTOPPABLE_ARGS,
    DEFAULT_UNSTOPPABLE_EXE,
    DISPATCH_MODE_QUEUE,
    QUEUE_VIEW_DOCK,
    SHORTCUT_BEHAVIOR_DIRECT,
    normalize_conflict_policy,
    normalize_copy_move_backend,
    normalize_delete_backend,
    normalize_dispatch_mode,
    normalize_queue_view_mode,
    normalize_shortcut_behavior,
)


@dataclass(frozen=True)
class UiPreferences:
    new_context_mode: str = "clone_active_path"
    show_hidden_default: bool = True
    show_root_dropdown: bool = False
    column_width_auto_align_mode: str = "current_panel_tabs"
    show_refresh_button: bool = True
    show_root_buttons: bool = True
    show_address_bar: bool = True
    show_navigation_buttons: bool = True
    app_font_family: str = ""
    app_font_size_pt: int = 0
    file_list_use_app_font: bool = True
    file_list_font_family: str = ""
    file_list_font_size_pt: int = 10
    navigation_use_app_font: bool = True
    navigation_font_family: str = ""
    navigation_font_size_pt: int = 10
    active_panel_tint_color_hex: str = "#A8B6C4"
    active_panel_tint_intensity_percent: int = 24
    target_panel_tint_color_hex: str = "#D2CCAA"
    target_panel_tint_intensity_percent: int = 28
    default_copy_move_backend: str = BACKEND_PYTHON
    default_delete_backend: str = BACKEND_RECYCLE_BIN
    default_operation_dispatch_mode: str = DISPATCH_MODE_QUEUE
    default_operation_conflict_policy: str = "rename"
    operation_shortcut_behavior: str = SHORTCUT_BEHAVIOR_DIRECT
    operation_queue_view_mode: str = QUEUE_VIEW_DOCK
    default_editor_executable: str = ""
    default_viewer_executable: str = ""
    file_open_overrides_json: str = "{}"
    use_extended_paths_robocopy: bool = False
    use_extended_paths_teracopy: bool = False
    use_extended_paths_unstoppable: bool = False
    use_extended_paths_external_copymove: bool = False
    use_extended_paths_cmd_delete: bool = False
    use_extended_paths_powershell_delete: bool = False
    use_extended_paths_rimraf: bool = False
    use_extended_paths_external_delete: bool = False
    script_editor_executable: str = ""
    teracopy_executable: str = DEFAULT_TERA_COPY_EXE
    teracopy_args_template: str = DEFAULT_TERA_COPY_ARGS
    unstoppable_executable: str = DEFAULT_UNSTOPPABLE_EXE
    unstoppable_args_template: str = DEFAULT_UNSTOPPABLE_ARGS
    generic_copymove_executable: str = DEFAULT_GENERIC_COPYMOVE_EXE
    generic_copymove_args_template: str = DEFAULT_GENERIC_COPYMOVE_ARGS
    generic_delete_executable: str = DEFAULT_GENERIC_DELETE_EXE
    generic_delete_args_template: str = DEFAULT_GENERIC_DELETE_ARGS
    robocopy_copy_args: str = DEFAULT_ROBOCOPY_COPY_ARGS
    robocopy_move_args: str = DEFAULT_ROBOCOPY_MOVE_ARGS
    cmd_delete_args: str = DEFAULT_CMD_DELETE_ARGS
    powershell_delete_args: str = DEFAULT_POWERSHELL_DELETE_ARGS
    rimraf_executable: str = DEFAULT_RIMRAF_EXE
    rimraf_args_template: str = DEFAULT_RIMRAF_ARGS


class SettingsManager:
    """Thin wrapper around QSettings using INI storage."""

    NEW_CONTEXT_MODE_KEY = "config/new_context_mode"
    SHOW_HIDDEN_DEFAULT_KEY = "ui/show_hidden_default"
    SHOW_ROOT_DROPDOWN_KEY = "ui/show_root_dropdown"
    COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY = "ui/file_list/column_width_auto_align_mode"
    SHOW_REFRESH_BUTTON_KEY = "ui/show_refresh_button"
    SHOW_ROOT_BUTTONS_KEY = "ui/show_root_buttons"
    SHOW_ADDRESS_BAR_KEY = "ui/show_address_bar"
    SHOW_NAVIGATION_BUTTONS_KEY = "ui/show_navigation_buttons"
    APP_FONT_FAMILY_KEY = "ui/font/app/family"
    APP_FONT_SIZE_PT_KEY = "ui/font/app/size_pt"
    FILE_LIST_USE_APP_FONT_KEY = "ui/font/file_list/use_app_font"
    FILE_LIST_FONT_FAMILY_KEY = "ui/font/file_list/family"
    FILE_LIST_FONT_SIZE_PT_KEY = "ui/font/file_list/size_pt"
    NAVIGATION_USE_APP_FONT_KEY = "ui/font/navigation/use_app_font"
    NAVIGATION_FONT_FAMILY_KEY = "ui/font/navigation/family"
    NAVIGATION_FONT_SIZE_PT_KEY = "ui/font/navigation/size_pt"
    ACTIVE_PANEL_TINT_COLOR_KEY = "ui/panel_tint/active_color_hex"
    ACTIVE_PANEL_TINT_INTENSITY_KEY = "ui/panel_tint/active_intensity_percent"
    TARGET_PANEL_TINT_COLOR_KEY = "ui/panel_tint/target_color_hex"
    TARGET_PANEL_TINT_INTENSITY_KEY = "ui/panel_tint/target_intensity_percent"
    DEFAULT_COPY_MOVE_BACKEND_KEY = "ops/default_copy_move_backend"
    DEFAULT_DELETE_BACKEND_KEY = "ops/default_delete_backend"
    DEFAULT_OPERATION_DISPATCH_MODE_KEY = "ops/default_dispatch_mode"
    DEFAULT_OPERATION_CONFLICT_POLICY_KEY = "ops/default_conflict_policy"
    OPERATION_SHORTCUT_BEHAVIOR_KEY = "ops/shortcut_behavior"
    OPERATION_QUEUE_VIEW_MODE_KEY = "ops/queue_view_mode"
    DEFAULT_EDITOR_EXECUTABLE_KEY = "ops/open/default_editor_executable"
    DEFAULT_VIEWER_EXECUTABLE_KEY = "ops/open/default_viewer_executable"
    FILE_OPEN_OVERRIDES_JSON_KEY = "ops/open/file_open_overrides_json"
    USE_EXTENDED_PATHS_ROBOCOPY_KEY = "ops/backends/robocopy/use_extended_paths"
    USE_EXTENDED_PATHS_TERACOPY_KEY = "ops/backends/teracopy/use_extended_paths"
    USE_EXTENDED_PATHS_UNSTOPPABLE_KEY = "ops/backends/unstoppable/use_extended_paths"
    USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY = "ops/backends/external_copymove/use_extended_paths"
    USE_EXTENDED_PATHS_CMD_DELETE_KEY = "ops/backends/cmd_delete/use_extended_paths"
    USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY = "ops/backends/powershell_delete/use_extended_paths"
    USE_EXTENDED_PATHS_RIMRAF_KEY = "ops/backends/rimraf/use_extended_paths"
    USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY = "ops/backends/external_delete/use_extended_paths"
    SCRIPT_EDITOR_EXECUTABLE_KEY = "ops/script_editor/executable"
    TERACOPY_EXECUTABLE_KEY = "ops/backends/teracopy/executable"
    TERACOPY_ARGS_TEMPLATE_KEY = "ops/backends/teracopy/args_template"
    UNSTOPPABLE_EXECUTABLE_KEY = "ops/backends/unstoppable/executable"
    UNSTOPPABLE_ARGS_TEMPLATE_KEY = "ops/backends/unstoppable/args_template"
    GENERIC_COPYMOVE_EXECUTABLE_KEY = "ops/backends/generic_copymove/executable"
    GENERIC_COPYMOVE_ARGS_TEMPLATE_KEY = "ops/backends/generic_copymove/args_template"
    GENERIC_DELETE_EXECUTABLE_KEY = "ops/backends/generic_delete/executable"
    GENERIC_DELETE_ARGS_TEMPLATE_KEY = "ops/backends/generic_delete/args_template"
    ROBOCOPY_COPY_ARGS_KEY = "ops/backends/robocopy/copy_args"
    ROBOCOPY_MOVE_ARGS_KEY = "ops/backends/robocopy/move_args"
    CMD_DELETE_ARGS_KEY = "ops/backends/cmd_delete/args"
    POWERSHELL_DELETE_ARGS_KEY = "ops/backends/powershell_delete/args"
    RIMRAF_EXECUTABLE_KEY = "ops/backends/rimraf/executable"
    RIMRAF_ARGS_TEMPLATE_KEY = "ops/backends/rimraf/args_template"
    OPS_COMPANION_BOOTSTRAP_DONE_KEY = "ops/internal/companion_bootstrap_done"
    SESSION_WINDOWS_KEY = "prefs/session_windows"
    SAVED_VIEWS_KEY = "prefs/saved_views"
    DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX = "#A8B6C4"
    DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT = 24
    DEFAULT_TARGET_PANEL_TINT_COLOR_HEX = "#D2CCAA"
    DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT = 28
    DEFAULT_APP_FONT_FAMILY = ""
    DEFAULT_APP_FONT_SIZE_PT = 0
    DEFAULT_FILE_LIST_USE_APP_FONT = True
    DEFAULT_FILE_LIST_FONT_FAMILY = ""
    DEFAULT_FILE_LIST_FONT_SIZE_PT = 10
    DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE = "current_panel_tabs"
    DEFAULT_NAVIGATION_USE_APP_FONT = True
    DEFAULT_NAVIGATION_FONT_FAMILY = ""
    DEFAULT_NAVIGATION_FONT_SIZE_PT = 10
    DEFAULT_COPY_MOVE_BACKEND = BACKEND_PYTHON
    DEFAULT_DELETE_BACKEND = BACKEND_RECYCLE_BIN
    DEFAULT_OPERATION_DISPATCH_MODE = DISPATCH_MODE_QUEUE
    DEFAULT_OPERATION_CONFLICT_POLICY = "rename"
    DEFAULT_OPERATION_SHORTCUT_BEHAVIOR = SHORTCUT_BEHAVIOR_DIRECT
    DEFAULT_OPERATION_QUEUE_VIEW_MODE = QUEUE_VIEW_DOCK
    DEFAULT_DEFAULT_EDITOR_EXECUTABLE = ""
    DEFAULT_DEFAULT_VIEWER_EXECUTABLE = ""
    DEFAULT_FILE_OPEN_OVERRIDES_JSON = "{}"
    DEFAULT_USE_EXTENDED_PATHS_ROBOCOPY = False
    DEFAULT_USE_EXTENDED_PATHS_TERACOPY = False
    DEFAULT_USE_EXTENDED_PATHS_UNSTOPPABLE = False
    DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE = False
    DEFAULT_USE_EXTENDED_PATHS_CMD_DELETE = False
    DEFAULT_USE_EXTENDED_PATHS_POWERSHELL_DELETE = False
    DEFAULT_USE_EXTENDED_PATHS_RIMRAF = False
    DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_DELETE = False
    DEFAULT_SCRIPT_EDITOR_EXECUTABLE = ""
    DEFAULT_TERACOPY_EXECUTABLE = DEFAULT_TERA_COPY_EXE
    DEFAULT_TERACOPY_ARGS_TEMPLATE = DEFAULT_TERA_COPY_ARGS
    DEFAULT_UNSTOPPABLE_EXECUTABLE = DEFAULT_UNSTOPPABLE_EXE
    DEFAULT_UNSTOPPABLE_ARGS_TEMPLATE = DEFAULT_UNSTOPPABLE_ARGS
    DEFAULT_GENERIC_COPYMOVE_EXECUTABLE = DEFAULT_GENERIC_COPYMOVE_EXE
    DEFAULT_GENERIC_COPYMOVE_ARGS_TEMPLATE = DEFAULT_GENERIC_COPYMOVE_ARGS
    DEFAULT_GENERIC_DELETE_EXECUTABLE = DEFAULT_GENERIC_DELETE_EXE
    DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE = DEFAULT_GENERIC_DELETE_ARGS
    DEFAULT_ROBOCOPY_COPY_ARGS = DEFAULT_ROBOCOPY_COPY_ARGS
    DEFAULT_ROBOCOPY_MOVE_ARGS = DEFAULT_ROBOCOPY_MOVE_ARGS
    DEFAULT_CMD_DELETE_ARGS = DEFAULT_CMD_DELETE_ARGS
    DEFAULT_POWERSHELL_DELETE_ARGS = DEFAULT_POWERSHELL_DELETE_ARGS
    DEFAULT_RIMRAF_EXECUTABLE = DEFAULT_RIMRAF_EXE
    DEFAULT_RIMRAF_ARGS_TEMPLATE = DEFAULT_RIMRAF_ARGS
    _ALLOWED_NEW_CONTEXT_MODES = {"clone_active_path", "home", "cwd"}
    _ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES = {
        "all_panels_tabs",
        "current_panel_tabs",
        "none",
    }
    _HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def __init__(self) -> None:
        self.qsettings = create_qsettings(APP_IDENTITY)
        self.qsettings.sync()
        self.settings_path = Path(str(self.qsettings.fileName() or ""))

    def sync(self) -> None:
        self.qsettings.sync()

    def value(self, key: str, default: Any = None) -> Any:
        return self.qsettings.value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self.qsettings.setValue(key, value)

    def remove(self, key: str) -> None:
        self.qsettings.remove(key)

    def set_json(self, key: str, value: Any) -> None:
        self.qsettings.setValue(key, json.dumps(value))

    def get_json(self, key: str, default: Any) -> Any:
        raw = self.qsettings.value(key)
        if raw is None:
            return default
        if isinstance(raw, dict):
            return dict(cast("dict[str, Any]", raw))
        if isinstance(raw, list):
            return list(cast("list[Any]", raw))
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError:
            return default

    @property
    def new_context_mode(self) -> str:
        value = str(self.value(self.NEW_CONTEXT_MODE_KEY, "clone_active_path"))
        mode = value.strip().lower()
        if mode not in self._ALLOWED_NEW_CONTEXT_MODES:
            return "clone_active_path"
        return mode

    @new_context_mode.setter
    def new_context_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        if normalized not in self._ALLOWED_NEW_CONTEXT_MODES:
            normalized = "clone_active_path"
        self.set_value(self.NEW_CONTEXT_MODE_KEY, normalized)

    @property
    def show_hidden_default(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_HIDDEN_DEFAULT_KEY, True))

    @show_hidden_default.setter
    def show_hidden_default(self, enabled: bool) -> None:
        self.set_value(self.SHOW_HIDDEN_DEFAULT_KEY, bool(enabled))

    @property
    def show_root_dropdown(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_ROOT_DROPDOWN_KEY, False))

    @show_root_dropdown.setter
    def show_root_dropdown(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ROOT_DROPDOWN_KEY, bool(enabled))

    @property
    def column_width_auto_align_mode(self) -> str:
        value = str(
            self.value(
                self.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY,
                self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE,
            )
        )
        mode = value.strip().lower()
        if mode not in self._ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES:
            return self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        return mode

    @column_width_auto_align_mode.setter
    def column_width_auto_align_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        if normalized not in self._ALLOWED_COLUMN_WIDTH_AUTO_ALIGN_MODES:
            normalized = self.DEFAULT_COLUMN_WIDTH_AUTO_ALIGN_MODE
        self.set_value(self.COLUMN_WIDTH_AUTO_ALIGN_MODE_KEY, normalized)

    @property
    def show_refresh_button(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_REFRESH_BUTTON_KEY, True))

    @show_refresh_button.setter
    def show_refresh_button(self, enabled: bool) -> None:
        self.set_value(self.SHOW_REFRESH_BUTTON_KEY, bool(enabled))

    @property
    def show_root_buttons(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_ROOT_BUTTONS_KEY, True))

    @show_root_buttons.setter
    def show_root_buttons(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ROOT_BUTTONS_KEY, bool(enabled))

    @property
    def show_address_bar(self) -> bool:
        return self._normalize_bool(self.value(self.SHOW_ADDRESS_BAR_KEY, True))

    @show_address_bar.setter
    def show_address_bar(self, enabled: bool) -> None:
        self.set_value(self.SHOW_ADDRESS_BAR_KEY, bool(enabled))

    @property
    def show_navigation_buttons(self) -> bool:
        return self._normalize_bool(
            self.value(self.SHOW_NAVIGATION_BUTTONS_KEY, True)
        )

    @show_navigation_buttons.setter
    def show_navigation_buttons(self, enabled: bool) -> None:
        self.set_value(self.SHOW_NAVIGATION_BUTTONS_KEY, bool(enabled))

    @property
    def app_font_family(self) -> str:
        return self._normalize_font_family(
            self.value(self.APP_FONT_FAMILY_KEY, self.DEFAULT_APP_FONT_FAMILY)
        )

    @app_font_family.setter
    def app_font_family(self, family: str) -> None:
        self.set_value(self.APP_FONT_FAMILY_KEY, self._normalize_font_family(family))

    @property
    def app_font_size_pt(self) -> int:
        return self._normalize_font_size(
            self.value(self.APP_FONT_SIZE_PT_KEY, self.DEFAULT_APP_FONT_SIZE_PT),
            fallback=self.DEFAULT_APP_FONT_SIZE_PT,
            allow_zero=True,
        )

    @app_font_size_pt.setter
    def app_font_size_pt(self, size_pt: int) -> None:
        self.set_value(
            self.APP_FONT_SIZE_PT_KEY,
            self._normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_APP_FONT_SIZE_PT,
                allow_zero=True,
            ),
        )

    @property
    def file_list_use_app_font(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.FILE_LIST_USE_APP_FONT_KEY,
                self.DEFAULT_FILE_LIST_USE_APP_FONT,
            )
        )

    @file_list_use_app_font.setter
    def file_list_use_app_font(self, enabled: bool) -> None:
        self.set_value(self.FILE_LIST_USE_APP_FONT_KEY, bool(enabled))

    @property
    def file_list_font_family(self) -> str:
        return self._normalize_font_family(
            self.value(
                self.FILE_LIST_FONT_FAMILY_KEY,
                self.DEFAULT_FILE_LIST_FONT_FAMILY,
            )
        )

    @file_list_font_family.setter
    def file_list_font_family(self, family: str) -> None:
        self.set_value(
            self.FILE_LIST_FONT_FAMILY_KEY,
            self._normalize_font_family(family),
        )

    @property
    def file_list_font_size_pt(self) -> int:
        return self._normalize_font_size(
            self.value(
                self.FILE_LIST_FONT_SIZE_PT_KEY,
                self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
        )

    @file_list_font_size_pt.setter
    def file_list_font_size_pt(self, size_pt: int) -> None:
        self.set_value(
            self.FILE_LIST_FONT_SIZE_PT_KEY,
            self._normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_FILE_LIST_FONT_SIZE_PT,
            ),
        )

    @property
    def navigation_use_app_font(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.NAVIGATION_USE_APP_FONT_KEY,
                self.DEFAULT_NAVIGATION_USE_APP_FONT,
            )
        )

    @navigation_use_app_font.setter
    def navigation_use_app_font(self, enabled: bool) -> None:
        self.set_value(self.NAVIGATION_USE_APP_FONT_KEY, bool(enabled))

    @property
    def navigation_font_family(self) -> str:
        return self._normalize_font_family(
            self.value(
                self.NAVIGATION_FONT_FAMILY_KEY,
                self.DEFAULT_NAVIGATION_FONT_FAMILY,
            )
        )

    @navigation_font_family.setter
    def navigation_font_family(self, family: str) -> None:
        self.set_value(
            self.NAVIGATION_FONT_FAMILY_KEY,
            self._normalize_font_family(family),
        )

    @property
    def navigation_font_size_pt(self) -> int:
        return self._normalize_font_size(
            self.value(
                self.NAVIGATION_FONT_SIZE_PT_KEY,
                self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
            fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
        )

    @navigation_font_size_pt.setter
    def navigation_font_size_pt(self, size_pt: int) -> None:
        self.set_value(
            self.NAVIGATION_FONT_SIZE_PT_KEY,
            self._normalize_font_size(
                size_pt,
                fallback=self.DEFAULT_NAVIGATION_FONT_SIZE_PT,
            ),
        )

    @property
    def active_panel_tint_color_hex(self) -> str:
        return self._normalize_color_hex(
            self.value(
                self.ACTIVE_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX,
        )

    @active_panel_tint_color_hex.setter
    def active_panel_tint_color_hex(self, color_hex: str) -> None:
        self.set_value(
            self.ACTIVE_PANEL_TINT_COLOR_KEY,
            self._normalize_color_hex(
                color_hex, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def active_panel_tint_intensity_percent(self) -> int:
        return self._normalize_percent(
            self.value(
                self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT,
        )

    @active_panel_tint_intensity_percent.setter
    def active_panel_tint_intensity_percent(self, percent: int) -> None:
        self.set_value(
            self.ACTIVE_PANEL_TINT_INTENSITY_KEY,
            self._normalize_percent(
                percent, fallback=self.DEFAULT_ACTIVE_PANEL_TINT_INTENSITY_PERCENT
            ),
        )

    @property
    def target_panel_tint_color_hex(self) -> str:
        return self._normalize_color_hex(
            self.value(
                self.TARGET_PANEL_TINT_COLOR_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX,
        )

    @target_panel_tint_color_hex.setter
    def target_panel_tint_color_hex(self, color_hex: str) -> None:
        self.set_value(
            self.TARGET_PANEL_TINT_COLOR_KEY,
            self._normalize_color_hex(
                color_hex, fallback=self.DEFAULT_TARGET_PANEL_TINT_COLOR_HEX
            ),
        )

    @property
    def target_panel_tint_intensity_percent(self) -> int:
        return self._normalize_percent(
            self.value(
                self.TARGET_PANEL_TINT_INTENSITY_KEY,
                self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
            ),
            fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT,
        )

    @target_panel_tint_intensity_percent.setter
    def target_panel_tint_intensity_percent(self, percent: int) -> None:
        self.set_value(
            self.TARGET_PANEL_TINT_INTENSITY_KEY,
            self._normalize_percent(
                percent, fallback=self.DEFAULT_TARGET_PANEL_TINT_INTENSITY_PERCENT
            ),
        )

    @property
    def default_copy_move_backend(self) -> str:
        return normalize_copy_move_backend(
            self.value(
                self.DEFAULT_COPY_MOVE_BACKEND_KEY,
                self.DEFAULT_COPY_MOVE_BACKEND,
            )
        )

    @default_copy_move_backend.setter
    def default_copy_move_backend(self, backend: str) -> None:
        self.set_value(
            self.DEFAULT_COPY_MOVE_BACKEND_KEY,
            normalize_copy_move_backend(backend),
        )

    @property
    def default_delete_backend(self) -> str:
        return normalize_delete_backend(
            self.value(
                self.DEFAULT_DELETE_BACKEND_KEY,
                self.DEFAULT_DELETE_BACKEND,
            )
        )

    @default_delete_backend.setter
    def default_delete_backend(self, backend: str) -> None:
        self.set_value(
            self.DEFAULT_DELETE_BACKEND_KEY,
            normalize_delete_backend(backend),
        )

    @property
    def default_operation_dispatch_mode(self) -> str:
        return normalize_dispatch_mode(
            self.value(
                self.DEFAULT_OPERATION_DISPATCH_MODE_KEY,
                self.DEFAULT_OPERATION_DISPATCH_MODE,
            )
        )

    @default_operation_dispatch_mode.setter
    def default_operation_dispatch_mode(self, mode: str) -> None:
        self.set_value(
            self.DEFAULT_OPERATION_DISPATCH_MODE_KEY,
            normalize_dispatch_mode(mode),
        )

    @property
    def default_operation_conflict_policy(self) -> str:
        return normalize_conflict_policy(
            self.value(
                self.DEFAULT_OPERATION_CONFLICT_POLICY_KEY,
                self.DEFAULT_OPERATION_CONFLICT_POLICY,
            )
        )

    @default_operation_conflict_policy.setter
    def default_operation_conflict_policy(self, policy: str) -> None:
        self.set_value(
            self.DEFAULT_OPERATION_CONFLICT_POLICY_KEY,
            normalize_conflict_policy(policy),
        )

    @property
    def operation_shortcut_behavior(self) -> str:
        return normalize_shortcut_behavior(
            self.value(
                self.OPERATION_SHORTCUT_BEHAVIOR_KEY,
                self.DEFAULT_OPERATION_SHORTCUT_BEHAVIOR,
            )
        )

    @operation_shortcut_behavior.setter
    def operation_shortcut_behavior(self, behavior: str) -> None:
        self.set_value(
            self.OPERATION_SHORTCUT_BEHAVIOR_KEY,
            normalize_shortcut_behavior(behavior),
        )

    @property
    def operation_queue_view_mode(self) -> str:
        return normalize_queue_view_mode(
            self.value(
                self.OPERATION_QUEUE_VIEW_MODE_KEY,
                self.DEFAULT_OPERATION_QUEUE_VIEW_MODE,
            )
        )

    @operation_queue_view_mode.setter
    def operation_queue_view_mode(self, mode: str) -> None:
        self.set_value(
            self.OPERATION_QUEUE_VIEW_MODE_KEY,
            normalize_queue_view_mode(mode),
        )

    @property
    def default_editor_executable(self) -> str:
        value = self._normalize_text(
            self.value(
                self.DEFAULT_EDITOR_EXECUTABLE_KEY,
                self.DEFAULT_DEFAULT_EDITOR_EXECUTABLE,
            ),
            fallback=self.DEFAULT_DEFAULT_EDITOR_EXECUTABLE,
        )
        if value:
            return value
        # Backward compatibility with earlier script-only editor setting.
        return self.script_editor_executable

    @default_editor_executable.setter
    def default_editor_executable(self, value: str) -> None:
        self.set_value(
            self.DEFAULT_EDITOR_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_DEFAULT_EDITOR_EXECUTABLE),
        )

    @property
    def default_viewer_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.DEFAULT_VIEWER_EXECUTABLE_KEY,
                self.DEFAULT_DEFAULT_VIEWER_EXECUTABLE,
            ),
            fallback=self.DEFAULT_DEFAULT_VIEWER_EXECUTABLE,
        )

    @default_viewer_executable.setter
    def default_viewer_executable(self, value: str) -> None:
        self.set_value(
            self.DEFAULT_VIEWER_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_DEFAULT_VIEWER_EXECUTABLE),
        )

    @property
    def file_open_overrides_json(self) -> str:
        return self._normalize_overrides_json(
            self.value(
                self.FILE_OPEN_OVERRIDES_JSON_KEY,
                self.DEFAULT_FILE_OPEN_OVERRIDES_JSON,
            ),
            fallback=self.DEFAULT_FILE_OPEN_OVERRIDES_JSON,
        )

    @file_open_overrides_json.setter
    def file_open_overrides_json(self, value: str) -> None:
        self.set_value(
            self.FILE_OPEN_OVERRIDES_JSON_KEY,
            self._normalize_overrides_json(
                value,
                fallback=self.DEFAULT_FILE_OPEN_OVERRIDES_JSON,
            ),
        )

    @property
    def use_extended_paths_robocopy(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_ROBOCOPY_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_ROBOCOPY,
            )
        )

    @use_extended_paths_robocopy.setter
    def use_extended_paths_robocopy(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_ROBOCOPY_KEY, bool(enabled))

    @property
    def use_extended_paths_teracopy(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_TERACOPY_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_TERACOPY,
            )
        )

    @use_extended_paths_teracopy.setter
    def use_extended_paths_teracopy(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_TERACOPY_KEY, bool(enabled))

    @property
    def use_extended_paths_unstoppable(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_UNSTOPPABLE,
            )
        )

    @use_extended_paths_unstoppable.setter
    def use_extended_paths_unstoppable(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_UNSTOPPABLE_KEY, bool(enabled))

    @property
    def use_extended_paths_external_copymove(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE,
            )
        )

    @use_extended_paths_external_copymove.setter
    def use_extended_paths_external_copymove(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_EXTERNAL_COPYMOVE_KEY, bool(enabled))

    @property
    def use_extended_paths_cmd_delete(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_CMD_DELETE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_CMD_DELETE,
            )
        )

    @use_extended_paths_cmd_delete.setter
    def use_extended_paths_cmd_delete(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_CMD_DELETE_KEY, bool(enabled))

    @property
    def use_extended_paths_powershell_delete(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_POWERSHELL_DELETE,
            )
        )

    @use_extended_paths_powershell_delete.setter
    def use_extended_paths_powershell_delete(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_POWERSHELL_DELETE_KEY, bool(enabled))

    @property
    def use_extended_paths_rimraf(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_RIMRAF_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_RIMRAF,
            )
        )

    @use_extended_paths_rimraf.setter
    def use_extended_paths_rimraf(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_RIMRAF_KEY, bool(enabled))

    @property
    def use_extended_paths_external_delete(self) -> bool:
        return self._normalize_bool(
            self.value(
                self.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY,
                self.DEFAULT_USE_EXTENDED_PATHS_EXTERNAL_DELETE,
            )
        )

    @use_extended_paths_external_delete.setter
    def use_extended_paths_external_delete(self, enabled: bool) -> None:
        self.set_value(self.USE_EXTENDED_PATHS_EXTERNAL_DELETE_KEY, bool(enabled))

    @property
    def script_editor_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.SCRIPT_EDITOR_EXECUTABLE_KEY,
                self.DEFAULT_SCRIPT_EDITOR_EXECUTABLE,
            ),
            fallback=self.DEFAULT_SCRIPT_EDITOR_EXECUTABLE,
        )

    @script_editor_executable.setter
    def script_editor_executable(self, value: str) -> None:
        self.set_value(
            self.SCRIPT_EDITOR_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_SCRIPT_EDITOR_EXECUTABLE),
        )

    @property
    def teracopy_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.TERACOPY_EXECUTABLE_KEY,
                self.DEFAULT_TERACOPY_EXECUTABLE,
            ),
            fallback=self.DEFAULT_TERACOPY_EXECUTABLE,
        )

    @teracopy_executable.setter
    def teracopy_executable(self, value: str) -> None:
        self.set_value(
            self.TERACOPY_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_TERACOPY_EXECUTABLE),
        )

    @property
    def teracopy_args_template(self) -> str:
        return self._normalize_text(
            self.value(
                self.TERACOPY_ARGS_TEMPLATE_KEY,
                self.DEFAULT_TERACOPY_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_TERACOPY_ARGS_TEMPLATE,
        )

    @teracopy_args_template.setter
    def teracopy_args_template(self, value: str) -> None:
        self.set_value(
            self.TERACOPY_ARGS_TEMPLATE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_TERACOPY_ARGS_TEMPLATE),
        )

    @property
    def unstoppable_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.UNSTOPPABLE_EXECUTABLE_KEY,
                self.DEFAULT_UNSTOPPABLE_EXECUTABLE,
            ),
            fallback=self.DEFAULT_UNSTOPPABLE_EXECUTABLE,
        )

    @unstoppable_executable.setter
    def unstoppable_executable(self, value: str) -> None:
        self.set_value(
            self.UNSTOPPABLE_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_UNSTOPPABLE_EXECUTABLE),
        )

    @property
    def unstoppable_args_template(self) -> str:
        return self._normalize_text(
            self.value(
                self.UNSTOPPABLE_ARGS_TEMPLATE_KEY,
                self.DEFAULT_UNSTOPPABLE_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_UNSTOPPABLE_ARGS_TEMPLATE,
        )

    @unstoppable_args_template.setter
    def unstoppable_args_template(self, value: str) -> None:
        self.set_value(
            self.UNSTOPPABLE_ARGS_TEMPLATE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_UNSTOPPABLE_ARGS_TEMPLATE),
        )

    @property
    def generic_copymove_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.GENERIC_COPYMOVE_EXECUTABLE_KEY,
                self.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE,
            ),
            fallback=self.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE,
        )

    @generic_copymove_executable.setter
    def generic_copymove_executable(self, value: str) -> None:
        self.set_value(
            self.GENERIC_COPYMOVE_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_GENERIC_COPYMOVE_EXECUTABLE),
        )

    @property
    def generic_copymove_args_template(self) -> str:
        return self._normalize_text(
            self.value(
                self.GENERIC_COPYMOVE_ARGS_TEMPLATE_KEY,
                self.DEFAULT_GENERIC_COPYMOVE_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_GENERIC_COPYMOVE_ARGS_TEMPLATE,
        )

    @generic_copymove_args_template.setter
    def generic_copymove_args_template(self, value: str) -> None:
        self.set_value(
            self.GENERIC_COPYMOVE_ARGS_TEMPLATE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_GENERIC_COPYMOVE_ARGS_TEMPLATE),
        )

    @property
    def generic_delete_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.GENERIC_DELETE_EXECUTABLE_KEY,
                self.DEFAULT_GENERIC_DELETE_EXECUTABLE,
            ),
            fallback=self.DEFAULT_GENERIC_DELETE_EXECUTABLE,
        )

    @generic_delete_executable.setter
    def generic_delete_executable(self, value: str) -> None:
        self.set_value(
            self.GENERIC_DELETE_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_GENERIC_DELETE_EXECUTABLE),
        )

    @property
    def generic_delete_args_template(self) -> str:
        return self._normalize_text(
            self.value(
                self.GENERIC_DELETE_ARGS_TEMPLATE_KEY,
                self.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE,
        )

    @generic_delete_args_template.setter
    def generic_delete_args_template(self, value: str) -> None:
        self.set_value(
            self.GENERIC_DELETE_ARGS_TEMPLATE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_GENERIC_DELETE_ARGS_TEMPLATE),
        )

    @property
    def robocopy_copy_args(self) -> str:
        return self._normalize_text(
            self.value(
                self.ROBOCOPY_COPY_ARGS_KEY,
                self.DEFAULT_ROBOCOPY_COPY_ARGS,
            ),
            fallback=self.DEFAULT_ROBOCOPY_COPY_ARGS,
        )

    @robocopy_copy_args.setter
    def robocopy_copy_args(self, value: str) -> None:
        self.set_value(
            self.ROBOCOPY_COPY_ARGS_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_ROBOCOPY_COPY_ARGS),
        )

    @property
    def robocopy_move_args(self) -> str:
        return self._normalize_text(
            self.value(
                self.ROBOCOPY_MOVE_ARGS_KEY,
                self.DEFAULT_ROBOCOPY_MOVE_ARGS,
            ),
            fallback=self.DEFAULT_ROBOCOPY_MOVE_ARGS,
        )

    @robocopy_move_args.setter
    def robocopy_move_args(self, value: str) -> None:
        self.set_value(
            self.ROBOCOPY_MOVE_ARGS_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_ROBOCOPY_MOVE_ARGS),
        )

    @property
    def cmd_delete_args(self) -> str:
        return self._normalize_text(
            self.value(
                self.CMD_DELETE_ARGS_KEY,
                self.DEFAULT_CMD_DELETE_ARGS,
            ),
            fallback=self.DEFAULT_CMD_DELETE_ARGS,
        )

    @cmd_delete_args.setter
    def cmd_delete_args(self, value: str) -> None:
        self.set_value(
            self.CMD_DELETE_ARGS_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_CMD_DELETE_ARGS),
        )

    @property
    def powershell_delete_args(self) -> str:
        return self._normalize_text(
            self.value(
                self.POWERSHELL_DELETE_ARGS_KEY,
                self.DEFAULT_POWERSHELL_DELETE_ARGS,
            ),
            fallback=self.DEFAULT_POWERSHELL_DELETE_ARGS,
        )

    @powershell_delete_args.setter
    def powershell_delete_args(self, value: str) -> None:
        self.set_value(
            self.POWERSHELL_DELETE_ARGS_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_POWERSHELL_DELETE_ARGS),
        )

    @property
    def rimraf_executable(self) -> str:
        return self._normalize_text(
            self.value(
                self.RIMRAF_EXECUTABLE_KEY,
                self.DEFAULT_RIMRAF_EXECUTABLE,
            ),
            fallback=self.DEFAULT_RIMRAF_EXECUTABLE,
        )

    @rimraf_executable.setter
    def rimraf_executable(self, value: str) -> None:
        self.set_value(
            self.RIMRAF_EXECUTABLE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_RIMRAF_EXECUTABLE),
        )

    @property
    def rimraf_args_template(self) -> str:
        return self._normalize_text(
            self.value(
                self.RIMRAF_ARGS_TEMPLATE_KEY,
                self.DEFAULT_RIMRAF_ARGS_TEMPLATE,
            ),
            fallback=self.DEFAULT_RIMRAF_ARGS_TEMPLATE,
        )

    @rimraf_args_template.setter
    def rimraf_args_template(self, value: str) -> None:
        self.set_value(
            self.RIMRAF_ARGS_TEMPLATE_KEY,
            self._normalize_text(value, fallback=self.DEFAULT_RIMRAF_ARGS_TEMPLATE),
        )

    @property
    def ops_companion_bootstrap_done(self) -> bool:
        return self._normalize_bool(
            self.value(self.OPS_COMPANION_BOOTSTRAP_DONE_KEY, False)
        )

    @ops_companion_bootstrap_done.setter
    def ops_companion_bootstrap_done(self, done: bool) -> None:
        self.set_value(self.OPS_COMPANION_BOOTSTRAP_DONE_KEY, bool(done))

    def ui_preferences(self) -> UiPreferences:
        return UiPreferences(
            new_context_mode=self.new_context_mode,
            show_hidden_default=self.show_hidden_default,
            show_root_dropdown=self.show_root_dropdown,
            column_width_auto_align_mode=self.column_width_auto_align_mode,
            show_refresh_button=self.show_refresh_button,
            show_root_buttons=self.show_root_buttons,
            show_address_bar=self.show_address_bar,
            show_navigation_buttons=self.show_navigation_buttons,
            app_font_family=self.app_font_family,
            app_font_size_pt=self.app_font_size_pt,
            file_list_use_app_font=self.file_list_use_app_font,
            file_list_font_family=self.file_list_font_family,
            file_list_font_size_pt=self.file_list_font_size_pt,
            navigation_use_app_font=self.navigation_use_app_font,
            navigation_font_family=self.navigation_font_family,
            navigation_font_size_pt=self.navigation_font_size_pt,
            active_panel_tint_color_hex=self.active_panel_tint_color_hex,
            active_panel_tint_intensity_percent=self.active_panel_tint_intensity_percent,
            target_panel_tint_color_hex=self.target_panel_tint_color_hex,
            target_panel_tint_intensity_percent=self.target_panel_tint_intensity_percent,
            default_copy_move_backend=self.default_copy_move_backend,
            default_delete_backend=self.default_delete_backend,
            default_operation_dispatch_mode=self.default_operation_dispatch_mode,
            default_operation_conflict_policy=self.default_operation_conflict_policy,
            operation_shortcut_behavior=self.operation_shortcut_behavior,
            operation_queue_view_mode=self.operation_queue_view_mode,
            default_editor_executable=self.default_editor_executable,
            default_viewer_executable=self.default_viewer_executable,
            file_open_overrides_json=self.file_open_overrides_json,
            use_extended_paths_robocopy=self.use_extended_paths_robocopy,
            use_extended_paths_teracopy=self.use_extended_paths_teracopy,
            use_extended_paths_unstoppable=self.use_extended_paths_unstoppable,
            use_extended_paths_external_copymove=self.use_extended_paths_external_copymove,
            use_extended_paths_cmd_delete=self.use_extended_paths_cmd_delete,
            use_extended_paths_powershell_delete=self.use_extended_paths_powershell_delete,
            use_extended_paths_rimraf=self.use_extended_paths_rimraf,
            use_extended_paths_external_delete=self.use_extended_paths_external_delete,
            script_editor_executable=self.script_editor_executable,
            teracopy_executable=self.teracopy_executable,
            teracopy_args_template=self.teracopy_args_template,
            unstoppable_executable=self.unstoppable_executable,
            unstoppable_args_template=self.unstoppable_args_template,
            generic_copymove_executable=self.generic_copymove_executable,
            generic_copymove_args_template=self.generic_copymove_args_template,
            generic_delete_executable=self.generic_delete_executable,
            generic_delete_args_template=self.generic_delete_args_template,
            robocopy_copy_args=self.robocopy_copy_args,
            robocopy_move_args=self.robocopy_move_args,
            cmd_delete_args=self.cmd_delete_args,
            powershell_delete_args=self.powershell_delete_args,
            rimraf_executable=self.rimraf_executable,
            rimraf_args_template=self.rimraf_args_template,
        )

    def set_ui_preferences(self, preferences: UiPreferences) -> None:
        self.new_context_mode = preferences.new_context_mode
        self.show_hidden_default = preferences.show_hidden_default
        self.show_root_dropdown = preferences.show_root_dropdown
        self.column_width_auto_align_mode = preferences.column_width_auto_align_mode
        self.show_refresh_button = preferences.show_refresh_button
        self.show_root_buttons = preferences.show_root_buttons
        self.show_address_bar = preferences.show_address_bar
        self.show_navigation_buttons = preferences.show_navigation_buttons
        self.app_font_family = preferences.app_font_family
        self.app_font_size_pt = preferences.app_font_size_pt
        self.file_list_use_app_font = preferences.file_list_use_app_font
        self.file_list_font_family = preferences.file_list_font_family
        self.file_list_font_size_pt = preferences.file_list_font_size_pt
        self.navigation_use_app_font = preferences.navigation_use_app_font
        self.navigation_font_family = preferences.navigation_font_family
        self.navigation_font_size_pt = preferences.navigation_font_size_pt
        self.active_panel_tint_color_hex = preferences.active_panel_tint_color_hex
        self.active_panel_tint_intensity_percent = (
            preferences.active_panel_tint_intensity_percent
        )
        self.target_panel_tint_color_hex = preferences.target_panel_tint_color_hex
        self.target_panel_tint_intensity_percent = (
            preferences.target_panel_tint_intensity_percent
        )
        self.default_copy_move_backend = preferences.default_copy_move_backend
        self.default_delete_backend = preferences.default_delete_backend
        self.default_operation_dispatch_mode = preferences.default_operation_dispatch_mode
        self.default_operation_conflict_policy = (
            preferences.default_operation_conflict_policy
        )
        self.operation_shortcut_behavior = preferences.operation_shortcut_behavior
        self.operation_queue_view_mode = preferences.operation_queue_view_mode
        self.default_editor_executable = preferences.default_editor_executable
        self.default_viewer_executable = preferences.default_viewer_executable
        self.file_open_overrides_json = preferences.file_open_overrides_json
        self.use_extended_paths_robocopy = preferences.use_extended_paths_robocopy
        self.use_extended_paths_teracopy = preferences.use_extended_paths_teracopy
        self.use_extended_paths_unstoppable = preferences.use_extended_paths_unstoppable
        self.use_extended_paths_external_copymove = (
            preferences.use_extended_paths_external_copymove
        )
        self.use_extended_paths_cmd_delete = preferences.use_extended_paths_cmd_delete
        self.use_extended_paths_powershell_delete = (
            preferences.use_extended_paths_powershell_delete
        )
        self.use_extended_paths_rimraf = preferences.use_extended_paths_rimraf
        self.use_extended_paths_external_delete = (
            preferences.use_extended_paths_external_delete
        )
        self.script_editor_executable = preferences.script_editor_executable
        self.teracopy_executable = preferences.teracopy_executable
        self.teracopy_args_template = preferences.teracopy_args_template
        self.unstoppable_executable = preferences.unstoppable_executable
        self.unstoppable_args_template = preferences.unstoppable_args_template
        self.generic_copymove_executable = preferences.generic_copymove_executable
        self.generic_copymove_args_template = preferences.generic_copymove_args_template
        self.generic_delete_executable = preferences.generic_delete_executable
        self.generic_delete_args_template = preferences.generic_delete_args_template
        self.robocopy_copy_args = preferences.robocopy_copy_args
        self.robocopy_move_args = preferences.robocopy_move_args
        self.cmd_delete_args = preferences.cmd_delete_args
        self.powershell_delete_args = preferences.powershell_delete_args
        self.rimraf_executable = preferences.rimraf_executable
        self.rimraf_args_template = preferences.rimraf_args_template

    def window_key(self, window_id: str, suffix: str) -> str:
        return f"ui/windows/{window_id}/{suffix}"

    def session_window_ids(self) -> list[str]:
        data = self.get_json(self.SESSION_WINDOWS_KEY, [])
        if not isinstance(data, list):
            return []
        return [str(item) for item in cast("list[Any]", data)]

    def set_session_window_ids(self, window_ids: list[str]) -> None:
        self.set_json(self.SESSION_WINDOWS_KEY, window_ids)

    def _saved_views(self) -> dict[str, dict[str, Any]]:
        data = self.get_json(self.SAVED_VIEWS_KEY, {})
        if not isinstance(data, dict):
            return {}
        views: dict[str, dict[str, Any]] = {}
        for key, value in cast("dict[str, Any]", data).items():
            if isinstance(value, dict):
                views[str(key)] = dict(cast("dict[str, Any]", value))
        return views

    def list_saved_views(self) -> list[str]:
        return sorted(self._saved_views().keys(), key=str.casefold)

    def get_saved_view(self, name: str) -> dict[str, Any] | None:
        return self._saved_views().get(name)

    def set_saved_view(self, name: str, payload: dict[str, Any]) -> None:
        views = self._saved_views()
        views[name] = payload
        self.set_json(self.SAVED_VIEWS_KEY, views)

    def _normalize_percent(self, raw: Any, *, fallback: int) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return int(fallback)
        if value < 0:
            return 0
        if value > 100:
            return 100
        return value

    def _normalize_bool(self, raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return bool(raw)

    def _normalize_font_family(self, raw: Any) -> str:
        return str(raw or "").strip()

    def _normalize_font_size(
        self,
        raw: Any,
        *,
        fallback: int,
        allow_zero: bool = False,
    ) -> int:
        try:
            size = int(raw)
        except (TypeError, ValueError):
            return int(fallback)
        if allow_zero and size <= 0:
            return 0
        if size < 6:
            return 6
        if size > 32:
            return 32
        return size

    def _normalize_color_hex(self, raw: Any, *, fallback: str) -> str:
        text = str(raw).strip()
        if not text:
            return fallback
        if not text.startswith("#"):
            text = f"#{text}"
        if self._HEX_COLOR_RE.fullmatch(text) is None:
            return fallback
        return text.upper()

    def _normalize_text(self, raw: Any, *, fallback: str) -> str:
        text = str(raw or "").strip()
        if text:
            return text
        return str(fallback)

    def _normalize_overrides_json(self, raw: Any, *, fallback: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return str(fallback)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return str(fallback)
        if not isinstance(payload, dict):
            return str(fallback)
        normalized: dict[str, dict[str, str]] = {}
        for ext, value in payload.items():
            ext_text = str(ext or "").strip().lower()
            if not ext_text:
                continue
            if not ext_text.startswith("."):
                ext_text = f".{ext_text}"
            if isinstance(value, dict):
                editor = str(value.get("editor", "")).strip()
                viewer = str(value.get("viewer", "")).strip()
            else:
                editor = ""
                viewer = ""
            normalized[ext_text] = {"editor": editor, "viewer": viewer}
        return json.dumps(normalized, sort_keys=True)
