from __future__ import annotations

from typing import cast

from .types import (
    BACKEND_CMD_DELETE,
    BACKEND_EXPLORER,
    BACKEND_EXTERNAL_COPYMOVE,
    BACKEND_EXTERNAL_DELETE,
    BACKEND_PERMANENT_NATIVE,
    BACKEND_POWERSHELL_DELETE,
    BACKEND_PYTHON,
    BACKEND_RECYCLE_BIN,
    BACKEND_RIMRAF,
    BACKEND_ROBOCOPY,
    BACKEND_TERACOPY,
    BACKEND_UNSTOPPABLE,
    DISPATCH_MODE_LAUNCH_NO_WAIT,
    DISPATCH_MODE_QUEUE,
    DISPATCH_MODE_RUN_WAIT,
    QUEUE_VIEW_BOTH,
    QUEUE_VIEW_DOCK,
    QUEUE_VIEW_FLOATING,
    SHORTCUT_BEHAVIOR_DIALOG,
    SHORTCUT_BEHAVIOR_DIRECT,
    OperationConflictPolicy,
    OperationDispatchMode,
    OperationKind,
)


def normalize_operation_kind(
    value: str, *, fallback: OperationKind = "copy"
) -> OperationKind:
    normalized = str(value).strip().lower()
    if normalized in {"copy", "move", "delete"}:
        return cast("OperationKind", normalized)
    return fallback


def normalize_dispatch_mode(
    value: str,
    *,
    fallback: OperationDispatchMode = DISPATCH_MODE_QUEUE,
) -> OperationDispatchMode:
    normalized = str(value).strip().lower()
    if normalized in {
        DISPATCH_MODE_QUEUE,
        DISPATCH_MODE_LAUNCH_NO_WAIT,
        DISPATCH_MODE_RUN_WAIT,
    }:
        return cast("OperationDispatchMode", normalized)
    return fallback


def normalize_conflict_policy(
    value: str,
    *,
    fallback: OperationConflictPolicy = "rename",
) -> OperationConflictPolicy:
    normalized = str(value).strip().lower()
    if normalized in {"overwrite", "skip", "rename", "cancel"}:
        return cast("OperationConflictPolicy", normalized)
    return fallback


def normalize_shortcut_behavior(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {SHORTCUT_BEHAVIOR_DIRECT, SHORTCUT_BEHAVIOR_DIALOG}:
        return normalized
    return SHORTCUT_BEHAVIOR_DIRECT


def normalize_queue_view_mode(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {QUEUE_VIEW_DOCK, QUEUE_VIEW_FLOATING, QUEUE_VIEW_BOTH}:
        return normalized
    return QUEUE_VIEW_DOCK


def normalize_copy_move_backend(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {
        BACKEND_PYTHON,
        BACKEND_EXPLORER,
        BACKEND_ROBOCOPY,
        BACKEND_TERACOPY,
        BACKEND_UNSTOPPABLE,
        BACKEND_EXTERNAL_COPYMOVE,
    }:
        return normalized
    return BACKEND_PYTHON


def normalize_delete_backend(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in {
        BACKEND_RECYCLE_BIN,
        BACKEND_PERMANENT_NATIVE,
        BACKEND_CMD_DELETE,
        BACKEND_POWERSHELL_DELETE,
        BACKEND_RIMRAF,
        BACKEND_EXTERNAL_DELETE,
    }:
        return normalized
    return BACKEND_RECYCLE_BIN
