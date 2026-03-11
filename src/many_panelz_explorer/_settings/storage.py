from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from threep_commons.qsettings_store import create_qsettings

from many_panelz_explorer.constants import APP_IDENTITY


class SettingsStorage:
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

    def clear_all(self) -> None:
        self.qsettings.clear()

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
