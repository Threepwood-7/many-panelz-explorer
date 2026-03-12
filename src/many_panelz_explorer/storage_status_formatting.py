from __future__ import annotations

from dataclasses import dataclass
from html import escape
from string import Formatter
from typing import TYPE_CHECKING, Final, TypedDict, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from . import mounts

DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE: Final[str] = (
    "{disk_root} {disk_label} {used_space}/{total_space}"
)

ALLOWED_STORAGE_LABEL_TEMPLATE_FIELDS: Final[set[str]] = {
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

_FORMATTER = Formatter()
_INDICATOR_FILLED_BLOCK = "\u2588"
_INDICATOR_EMPTY_BLOCK = "\u2591"


@dataclass(frozen=True)
class StorageStatusRenderResult:
    label_text: str
    tooltip_html: str


class _StorageRenderContext(TypedDict):
    disk_label: str
    disk_root: str
    root_path: str
    used_space: str
    free_space: str
    total_space: str
    used_bytes: int
    free_bytes: int
    total_bytes: int
    usage_percentage: float
    free_percentage: float
    usage_ratio: float
    free_ratio: float
    usage_indicator: str
    free_indicator: str


def format_storage_usage_entry(
    entry: mounts.StorageUsageEntry,
    *,
    bytes_formatter: Callable[[int], str],
    label_template: str,
) -> StorageStatusRenderResult:
    context = _build_context(entry, bytes_formatter)
    label_text = _render_label_template(label_template, context)
    tooltip_html = _render_tooltip_html(context)
    return StorageStatusRenderResult(label_text=label_text, tooltip_html=tooltip_html)


def _build_context(
    entry: mounts.StorageUsageEntry,
    bytes_formatter: Callable[[int], str],
) -> _StorageRenderContext:
    total_bytes = max(0, int(entry.bytes_total))
    used_bytes = max(0, int(entry.bytes_used))
    if total_bytes > 0:
        used_bytes = min(used_bytes, total_bytes)
        usage_ratio = _clamp_ratio(float(used_bytes) / float(total_bytes))
    else:
        usage_ratio = 0.0
    free_bytes = max(0, total_bytes - used_bytes)
    free_ratio = _clamp_ratio(1.0 - usage_ratio)

    disk_label = str(entry.volume_label or "").strip() or "volume"
    disk_root = str(entry.display_root or "").strip() or str(entry.root_path)
    root_path = str(entry.root_path)

    return {
        "disk_label": disk_label,
        "disk_root": disk_root,
        "root_path": root_path,
        "used_space": _format_bytes_value(used_bytes, bytes_formatter),
        "free_space": _format_bytes_value(free_bytes, bytes_formatter),
        "total_space": _format_bytes_value(total_bytes, bytes_formatter),
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "total_bytes": total_bytes,
        "usage_percentage": usage_ratio * 100.0,
        "free_percentage": free_ratio * 100.0,
        "usage_ratio": usage_ratio,
        "free_ratio": free_ratio,
        "usage_indicator": _ratio_indicator(usage_ratio),
        "free_indicator": _ratio_indicator(free_ratio),
    }


def _render_label_template(template: str, context: _StorageRenderContext) -> str:
    rendered = _safe_template_format(str(template or ""), context)
    if rendered is None:
        rendered = _safe_template_format(DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE, context)
    if rendered is not None:
        return rendered
    return (
        f"{context['disk_root']} {context['disk_label']} "
        f"{context['used_space']}/{context['total_space']}"
    )


def _safe_template_format(
    template: str,
    context: _StorageRenderContext,
) -> str | None:
    if not template:
        return None
    try:
        parsed = list(_FORMATTER.parse(template))
    except ValueError:
        return None

    rendered_parts: list[str] = []
    has_field = False
    for literal, field_name, format_spec, conversion in parsed:
        rendered_parts.append(literal)
        if field_name is None:
            continue
        has_field = True
        key = str(field_name)
        if key not in ALLOWED_STORAGE_LABEL_TEMPLATE_FIELDS:
            return None
        if conversion is not None:
            return None
        value = cast("object", context[key])
        try:
            rendered_parts.append(
                format(value, format_spec) if format_spec else str(value)
            )
        except (TypeError, ValueError):
            return None
    if not has_field:
        return None
    return "".join(rendered_parts)


def _render_tooltip_html(context: _StorageRenderContext) -> str:
    disk_identity = (
        f"{escape(str(context['disk_root']))} {escape(str(context['disk_label']))}"
    )
    root_path = escape(str(context["root_path"]))
    used_space = escape(str(context["used_space"]))
    free_space = escape(str(context["free_space"]))
    total_space = escape(str(context["total_space"]))
    usage_indicator = escape(str(context["usage_indicator"]))
    free_indicator = escape(str(context["free_indicator"]))

    used_bytes = f"{int(context['used_bytes']):,}"
    free_bytes = f"{int(context['free_bytes']):,}"
    total_bytes = f"{int(context['total_bytes']):,}"
    usage_percentage = float(context["usage_percentage"])
    free_percentage = float(context["free_percentage"])
    usage_ratio = float(context["usage_ratio"])
    free_ratio = float(context["free_ratio"])

    return (
        "<div style='white-space:nowrap;'>"
        f"<b>{disk_identity}</b><br/>"
        f"<span style='color:#888;'>Root:</span> {root_path}<br/>"
        f"<span style='color:#888;'>Used:</span> {used_space} ({used_bytes} B)<br/>"
        f"<span style='color:#888;'>Free:</span> {free_space} ({free_bytes} B)<br/>"
        f"<span style='color:#888;'>Total:</span> {total_space} ({total_bytes} B)<br/>"
        f"<span style='color:#888;'>Usage:</span> {usage_percentage:.2f}% ({usage_ratio:.4f})<br/>"
        f"<span style='color:#888;'>Free:</span> {free_percentage:.2f}% ({free_ratio:.4f})<br/>"
        "<span style='color:#888;'>Usage bar:</span> "
        "<span style=\"font-family:'Cascadia Mono','Consolas',monospace;\">"
        f"{usage_indicator}</span><br/>"
        "<span style='color:#888;'>Free bar:</span> "
        "<span style=\"font-family:'Cascadia Mono','Consolas',monospace;\">"
        f"{free_indicator}</span>"
        "</div>"
    )


def _format_bytes_value(value: int, bytes_formatter: Callable[[int], str]) -> str:
    try:
        return str(bytes_formatter(int(value)))
    except Exception:  # pragma: no cover - defensive fallback
        return f"{int(value):,}"


def _clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _ratio_indicator(value: float, *, steps: int = 10) -> str:
    clamped = _clamp_ratio(float(value))
    filled = round(clamped * steps)
    if filled < 0:
        filled = 0
    if filled > steps:
        filled = steps
    return (_INDICATOR_FILLED_BLOCK * filled) + (
        _INDICATOR_EMPTY_BLOCK * (steps - filled)
    )
