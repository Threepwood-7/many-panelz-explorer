from __future__ import annotations

import json
import re
from string import Formatter
from typing import Any, cast

from many_panelz_explorer._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    normalize_external_copymove_options,
    normalize_robocopy_options,
    normalize_teracopy_options,
    normalize_unstoppable_options,
)
from threep_commons.fs_paths import normalize_windows_path_text as _normalize_windows_path_text

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_FORMATTER = Formatter()
_ALLOWED_STATUS_LABEL_FIELDS = {
    "disk_label",
    "disk_root",
    "root_path",
    "used_space",
    "free_space",
    "total_space",
    "used_bytes",
    "free_bytes",
    "total_bytes",
    "usage_percentage",
    "free_percentage",
    "usage_ratio",
    "free_ratio",
    "usage_indicator",
    "free_indicator",
}


def normalize_percent(raw: Any, *, fallback: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return int(fallback)
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


def normalize_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw)


def normalize_font_family(raw: Any) -> str:
    return str(raw or "").strip()


def normalize_font_size(
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


def normalize_color_hex(raw: Any, *, fallback: str) -> str:
    text = str(raw).strip()
    if not text:
        return fallback
    if not text.startswith("#"):
        text = f"#{text}"
    if HEX_COLOR_RE.fullmatch(text) is None:
        return fallback
    return text.upper()


def normalize_text(raw: Any, *, fallback: str) -> str:
    text = str(raw or "").strip()
    if text:
        return text
    return str(fallback)


def normalize_windows_path_text(raw: Any, *, fallback: str) -> str:
    text = normalize_text(raw, fallback=fallback)
    if not text:
        return text
    return _normalize_windows_path_text(text)


def normalize_positive_int(
    raw: Any,
    *,
    fallback: int,
    minimum: int = 1,
    maximum: int = 10_000,
) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return int(fallback)
    if value < int(minimum):
        return int(minimum)
    if value > int(maximum):
        return int(maximum)
    return int(value)


def normalize_overrides_json(raw: Any, *, fallback: str) -> str:
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
    for ext, value in cast("dict[str, Any]", payload).items():
        ext_text = str(ext or "").strip().lower()
        if not ext_text:
            continue
        if not ext_text.startswith("."):
            ext_text = f".{ext_text}"
        if isinstance(value, dict):
            source = cast("dict[str, Any]", value)
            editor = normalize_windows_path_text(source.get("editor", ""), fallback="")
            viewer = normalize_windows_path_text(source.get("viewer", ""), fallback="")
        else:
            editor = ""
            viewer = ""
        normalized[ext_text] = {"editor": editor, "viewer": viewer}
    return json.dumps(normalized, sort_keys=True)


def normalize_byte_separator(
    raw: Any,
    *,
    fallback: str,
    allow_empty: bool = False,
) -> str:
    if raw is None:
        return str(fallback)
    text = str(raw)
    if text == "":
        return "" if allow_empty else str(fallback)
    candidate = text[0]
    if candidate in {"\n", "\r", "\t"}:
        return "" if allow_empty else str(fallback)
    return candidate


def normalize_byte_separators(
    raw_thousands: Any,
    raw_decimal: Any,
    *,
    fallback_thousands: str = ",",
    fallback_decimal: str = ".",
) -> tuple[str, str]:
    thousands = normalize_byte_separator(
        raw_thousands,
        fallback=fallback_thousands,
        allow_empty=True,
    )
    decimal = normalize_byte_separator(
        raw_decimal,
        fallback=fallback_decimal,
        allow_empty=False,
    )
    if thousands == decimal:
        return fallback_thousands, fallback_decimal
    return thousands, decimal


def normalize_byte_format_mode(
    raw: Any,
    *,
    fallback: str,
    allowed_modes: set[str],
) -> str:
    mode = str(raw or "").strip().lower()
    if mode in allowed_modes:
        return mode
    return str(fallback)


def normalize_byte_custom_template(raw: Any, *, fallback: str = "") -> str:
    if raw is None:
        return str(fallback)
    text = str(raw)
    if text:
        return text
    return str(fallback)


def normalize_status_storage_label_template(raw: Any, *, fallback: str) -> str:
    template = str(raw or "")
    if not template:
        return str(fallback)
    try:
        parsed = list(_FORMATTER.parse(template))
    except ValueError:
        return str(fallback)

    has_field = False
    for _literal, field_name, _format_spec, conversion in parsed:
        if field_name is None:
            continue
        has_field = True
        if conversion is not None:
            return str(fallback)
        if str(field_name) not in _ALLOWED_STATUS_LABEL_FIELDS:
            return str(fallback)
    if not has_field:
        return str(fallback)
    return template


def normalize_robocopy_structured_options(raw: Any) -> RobocopyBackendOptions:
    return normalize_robocopy_options(raw)


def normalize_teracopy_structured_options(raw: Any) -> TeraCopyBackendOptions:
    return normalize_teracopy_options(raw)


def normalize_unstoppable_structured_options(raw: Any) -> UnstoppableBackendOptions:
    return normalize_unstoppable_options(raw)


def normalize_external_copymove_structured_options(
    raw: Any,
) -> ExternalCopyMoveBackendOptions:
    return normalize_external_copymove_options(raw)
