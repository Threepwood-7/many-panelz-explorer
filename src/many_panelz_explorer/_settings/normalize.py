"""Normalization helpers for persisted settings values."""

from __future__ import annotations

import json
import re
from string import Formatter
from typing import Any, TypedDict, cast

from threep_commons.fs_paths import (
    normalize_windows_path_text as _normalize_windows_path_text,
)

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


class FileOpenOverrideEntry(TypedDict):
    """Typed editor/viewer override paths for one file extension."""

    editor: str
    viewer: str


def normalize_percent(raw: Any, *, fallback: int) -> int:
    """Clamp a numeric percentage into the inclusive `0..100` range."""

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
    """Normalize truthy persisted values into a boolean."""

    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw)


def normalize_font_family(raw: Any) -> str:
    """Normalize a stored font family name."""

    return str(raw or "").strip()


def normalize_font_size(
    raw: Any,
    *,
    fallback: int,
    allow_zero: bool = False,
) -> int:
    """Clamp a persisted font size into the supported UI range."""

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
    """Normalize a stored RGB color into uppercase `#RRGGBB` form."""

    text = str(raw).strip()
    if not text:
        return fallback
    if not text.startswith("#"):
        text = f"#{text}"
    if HEX_COLOR_RE.fullmatch(text) is None:
        return fallback
    return text.upper()


def normalize_text(raw: Any, *, fallback: str) -> str:
    """Return a stripped string or the supplied fallback."""

    text = str(raw or "").strip()
    if text:
        return text
    return str(fallback)


def normalize_windows_path_text(raw: Any, *, fallback: str) -> str:
    """Normalize user-supplied path text into canonical Windows form."""

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
    """Clamp a persisted integer into the configured positive range."""

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
    """Normalize file-open override JSON into a canonical mapping string."""

    text = str(raw or "").strip()
    if not text:
        return str(fallback)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return str(fallback)
    normalized = normalize_file_open_override_mapping(payload)
    if normalized is None:
        return str(fallback)
    return json.dumps(normalized, sort_keys=True)


def normalize_file_open_override_mapping(
    raw: object,
) -> dict[str, FileOpenOverrideEntry] | None:
    """Normalize a JSON-like override mapping into typed extension entries."""

    source_mapping = _string_object_mapping(raw)
    if source_mapping is None:
        return None

    normalized: dict[str, FileOpenOverrideEntry] = {}
    for ext, value in source_mapping.items():
        ext_text = str(ext or "").strip().lower()
        if not ext_text:
            continue
        if not ext_text.startswith("."):
            ext_text = f".{ext_text}"
        value_mapping = _string_object_mapping(value)
        if value_mapping is None:
            normalized[ext_text] = {"editor": "", "viewer": ""}
            continue
        normalized[ext_text] = {
            "editor": normalize_windows_path_text(
                value_mapping.get("editor", ""),
                fallback="",
            ),
            "viewer": normalize_windows_path_text(
                value_mapping.get("viewer", ""),
                fallback="",
            ),
        }
    return normalized


def normalize_byte_separator(
    raw: Any,
    *,
    fallback: str,
    allow_empty: bool = False,
) -> str:
    """Normalize a byte-format separator to a single safe character."""

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
    """Normalize thousands and decimal separators as a compatible pair."""

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
    """Normalize a byte display mode against the allowed mode set."""

    mode = str(raw or "").strip().lower()
    if mode in allowed_modes:
        return mode
    return str(fallback)


def normalize_byte_custom_template(raw: Any, *, fallback: str = "") -> str:
    """Normalize an optional custom byte-format template string."""

    if raw is None:
        return str(fallback)
    text = str(raw)
    if text:
        return text
    return str(fallback)


def normalize_status_storage_label_template(raw: Any, *, fallback: str) -> str:
    """Validate a status label template against the supported field names."""

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
    """Normalize persisted Robocopy options into their typed model."""

    return normalize_robocopy_options(raw)


def normalize_teracopy_structured_options(raw: Any) -> TeraCopyBackendOptions:
    """Normalize persisted TeraCopy options into their typed model."""

    return normalize_teracopy_options(raw)


def normalize_unstoppable_structured_options(raw: Any) -> UnstoppableBackendOptions:
    """Normalize persisted Unstoppable options into their typed model."""

    return normalize_unstoppable_options(raw)


def normalize_external_copymove_structured_options(
    raw: Any,
) -> ExternalCopyMoveBackendOptions:
    """Normalize persisted external copy-move options into their model."""

    return normalize_external_copymove_options(raw)


def _string_object_mapping(value: object) -> dict[str, object] | None:
    """Return a string-key mapping view for JSON-like dictionary input."""

    if not isinstance(value, dict):
        return None
    mapping = cast("dict[object, object]", value)
    return {str(key): item for key, item in mapping.items()}
