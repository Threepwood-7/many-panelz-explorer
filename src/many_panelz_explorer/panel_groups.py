"""Shared helpers for panel-local tab groups."""

from __future__ import annotations

import uuid

DEFAULT_TAB_GROUP_ID = "main"
DEFAULT_TAB_GROUP_TITLE = "Main"


def normalize_tab_group_id(
    value: object,
    *,
    fallback: str = DEFAULT_TAB_GROUP_ID,
) -> str:
    """Normalize a persisted tab-group identifier into a non-empty string."""

    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return str(fallback).strip() or DEFAULT_TAB_GROUP_ID


def normalize_tab_group_title(
    value: object,
    *,
    fallback: str = DEFAULT_TAB_GROUP_TITLE,
) -> str:
    """Normalize a user-visible tab-group title into compact text."""

    normalized = " ".join(str(value or "").split()).strip()
    if normalized:
        return normalized
    fallback_text = " ".join(str(fallback or "").split()).strip()
    if fallback_text:
        return fallback_text
    return DEFAULT_TAB_GROUP_TITLE


def new_tab_group_id() -> str:
    """Return a new opaque identifier for one panel-local tab group."""

    return uuid.uuid4().hex


def is_default_tab_group(*, group_id: str, title: str) -> bool:
    """Return whether the provided group matches the implicit default group."""

    return (
        normalize_tab_group_id(group_id) == DEFAULT_TAB_GROUP_ID
        and normalize_tab_group_title(title) == DEFAULT_TAB_GROUP_TITLE
    )
