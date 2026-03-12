from __future__ import annotations

from dataclasses import dataclass, field
from string import Formatter
from typing import Final

BYTE_FORMAT_MODE_HUMAN_READABLE: Final[str] = "human_readable"
BYTE_FORMAT_MODE_ALWAYS_MB: Final[str] = "always_mb"
BYTE_FORMAT_MODE_ALWAYS_MIB: Final[str] = "always_mib"
BYTE_FORMAT_MODE_BYTES: Final[str] = "bytes"
BYTE_FORMAT_MODE_CUSTOM: Final[str] = "custom"

ALLOWED_BYTE_FORMAT_MODES: Final[set[str]] = {
    BYTE_FORMAT_MODE_HUMAN_READABLE,
    BYTE_FORMAT_MODE_ALWAYS_MB,
    BYTE_FORMAT_MODE_ALWAYS_MIB,
    BYTE_FORMAT_MODE_BYTES,
    BYTE_FORMAT_MODE_CUSTOM,
}

_FORMATTER = Formatter()
_GROUP_SEP_MARKER = "\x00"
_DECIMAL_SEP_MARKER = "\x01"
_BINARY_UNITS: Final[tuple[str, ...]] = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
_CUSTOM_FIELD_FACTORS: Final[dict[str, int]] = {
    "KB": 1_000,
    "MB": 1_000_000,
    "GB": 1_000_000_000,
    "TB": 1_000_000_000_000,
    "PB": 1_000_000_000_000_000,
    "KiB": 1_024,
    "MiB": 1_048_576,
    "GiB": 1_073_741_824,
    "TiB": 1_099_511_627_776,
    "PiB": 1_125_899_906_842_624,
}
_ALLOWED_CUSTOM_FIELDS: Final[set[str]] = {"b", *_CUSTOM_FIELD_FACTORS.keys()}


@dataclass(frozen=True)
class ByteFormatScopeConfig:
    mode: str = BYTE_FORMAT_MODE_BYTES
    custom_template: str = ""


@dataclass(frozen=True)
class ByteFormatPreferences:
    thousands_sep: str = ","
    decimal_sep: str = "."
    file_list: ByteFormatScopeConfig = field(default_factory=ByteFormatScopeConfig)
    status_bar: ByteFormatScopeConfig = field(default_factory=ByteFormatScopeConfig)
    properties: ByteFormatScopeConfig = field(default_factory=ByteFormatScopeConfig)


def format_bytes(
    value: int,
    scope_config: ByteFormatScopeConfig,
    separators: tuple[str, str] | None = None,
) -> str:
    size = max(0, int(value))
    mode = _normalized_mode(scope_config.mode)
    thousands_sep, decimal_sep = _normalized_separators(separators)

    if mode == BYTE_FORMAT_MODE_HUMAN_READABLE:
        return _format_human_readable(size, thousands_sep, decimal_sep)
    if mode == BYTE_FORMAT_MODE_ALWAYS_MB:
        return _format_fixed_unit(
            size=size,
            divisor=1_000_000,
            unit="MB",
            thousands_sep=thousands_sep,
            decimal_sep=decimal_sep,
        )
    if mode == BYTE_FORMAT_MODE_ALWAYS_MIB:
        return _format_fixed_unit(
            size=size,
            divisor=1_048_576,
            unit="MiB",
            thousands_sep=thousands_sep,
            decimal_sep=decimal_sep,
        )
    if mode == BYTE_FORMAT_MODE_CUSTOM:
        custom = _format_custom_template(
            size=size,
            template=str(scope_config.custom_template or ""),
            thousands_sep=thousands_sep,
            decimal_sep=decimal_sep,
        )
        if custom is not None:
            return custom
    return _format_plain_bytes(size, thousands_sep)


def _normalized_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized in ALLOWED_BYTE_FORMAT_MODES:
        return normalized
    return BYTE_FORMAT_MODE_BYTES


def _normalized_separators(separators: tuple[str, str] | None) -> tuple[str, str]:
    if separators is None:
        return ",", "."
    thousands_raw, decimal_raw = separators

    thousands = str(thousands_raw or "")
    thousands = "" if thousands == "" else thousands[0]
    if thousands in {"\n", "\r", "\t"}:
        thousands = ""

    decimal = str(decimal_raw or ".")
    decimal = decimal[0] if decimal else "."
    if decimal in {"\n", "\r", "\t"}:
        decimal = "."

    if thousands == decimal:
        return ",", "."
    return thousands, decimal


def _format_plain_bytes(size: int, thousands_sep: str) -> str:
    return _grouped_int(size, thousands_sep)


def _format_human_readable(size: int, thousands_sep: str, decimal_sep: str) -> str:
    scaled = float(size)
    unit_idx = 0
    while scaled >= 1024.0 and unit_idx < len(_BINARY_UNITS) - 1:
        scaled /= 1024.0
        unit_idx += 1

    if unit_idx == 0:
        return f"{_grouped_int(size, thousands_sep)} {_BINARY_UNITS[unit_idx]}"
    precision = _precision_for_scaled(scaled)
    rendered = _format_decimal(
        scaled,
        precision=precision,
        thousands_sep=thousands_sep,
        decimal_sep=decimal_sep,
    )
    return f"{rendered} {_BINARY_UNITS[unit_idx]}"


def _format_fixed_unit(
    *,
    size: int,
    divisor: int,
    unit: str,
    thousands_sep: str,
    decimal_sep: str,
) -> str:
    scaled = float(size) / float(divisor)
    precision = _precision_for_scaled(scaled)
    rendered = _format_decimal(
        scaled,
        precision=precision,
        thousands_sep=thousands_sep,
        decimal_sep=decimal_sep,
    )
    return f"{rendered} {unit}"


def _format_custom_template(
    *,
    size: int,
    template: str,
    thousands_sep: str,
    decimal_sep: str,
) -> str | None:
    if not template:
        return None

    fields = _custom_field_values(size)
    parts: list[str] = []
    has_field = False

    try:
        parsed = list(_FORMATTER.parse(template))
    except ValueError:
        return None

    for literal, field_name, format_spec, conversion in parsed:
        parts.append(literal)
        if field_name is None:
            continue
        has_field = True
        key = str(field_name)
        if key not in _ALLOWED_CUSTOM_FIELDS:
            return None
        if conversion is not None:
            return None
        if not format_spec:
            if key == "b":
                parts.append(_grouped_int(int(fields[key]), thousands_sep))
                continue
            rendered = str(fields[key])
            parts.append(_localize_number_text(rendered, thousands_sep, decimal_sep))
            continue
        try:
            rendered = format(fields[key], format_spec)
        except (TypeError, ValueError):
            return None
        parts.append(_localize_number_text(rendered, thousands_sep, decimal_sep))

    if not has_field:
        return None
    return "".join(parts)


def _custom_field_values(size: int) -> dict[str, int | float]:
    values: dict[str, int | float] = {"b": size}
    for key, factor in _CUSTOM_FIELD_FACTORS.items():
        values[key] = float(size) / float(factor)
    return values


def _precision_for_scaled(value: float) -> int:
    if value >= 100:
        return 0
    if value >= 10:
        return 1
    return 2


def _format_decimal(
    value: float,
    *,
    precision: int,
    thousands_sep: str,
    decimal_sep: str,
) -> str:
    if precision <= 0:
        rounded = round(value)
        return _grouped_int(rounded, thousands_sep)
    text = f"{value:,.{precision}f}"
    return _localize_number_text(text, thousands_sep, decimal_sep)


def _grouped_int(value: int, thousands_sep: str) -> str:
    text = f"{int(value):,}"
    if thousands_sep == ",":
        return text
    return text.replace(",", thousands_sep)


def _localize_number_text(text: str, thousands_sep: str, decimal_sep: str) -> str:
    localized = text.replace(",", _GROUP_SEP_MARKER).replace(".", _DECIMAL_SEP_MARKER)
    localized = localized.replace(_GROUP_SEP_MARKER, thousands_sep)
    localized = localized.replace(_DECIMAL_SEP_MARKER, decimal_sep)
    return localized
