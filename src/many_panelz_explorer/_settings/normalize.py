from __future__ import annotations

import json
import re
from typing import Any, cast


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


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
            editor = str(source.get("editor", "")).strip()
            viewer = str(source.get("viewer", "")).strip()
        else:
            editor = ""
            viewer = ""
        normalized[ext_text] = {"editor": editor, "viewer": viewer}
    return json.dumps(normalized, sort_keys=True)
