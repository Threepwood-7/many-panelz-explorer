"""Application identity constants shared by the generated app package."""

from __future__ import annotations

from threep_commons.app_identity import AppIdentity

SETTINGS_ORG_NAME = "ThreepSoftwz"
SETTINGS_APP_NAME = "many_panelz_explorer"
APP_DISPLAY_NAME = "many-panelz-explorer"
APP_VERSION = "0.1.0"
DEFAULT_LOG_FILENAME = "many_panelz_explorer.log"
DEFAULT_LOG_MAX_BYTES = 1_048_576
DEFAULT_LOG_BACKUP_COUNT = 3

APP_IDENTITY = AppIdentity(
    org_name=SETTINGS_ORG_NAME,
    app_name=SETTINGS_APP_NAME,
    display_name=APP_DISPLAY_NAME,
    default_log_filename=DEFAULT_LOG_FILENAME,
    default_log_max_bytes=DEFAULT_LOG_MAX_BYTES,
    default_log_backup_count=DEFAULT_LOG_BACKUP_COUNT,
)
