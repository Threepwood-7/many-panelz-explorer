"""Structured backend option models and payload serializers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type BackendPayloadScalar = bool | int | str
type BackendOptionsPayload = dict[str, BackendPayloadScalar]
type CopyMoveKind = Literal["copy", "move"]
type UnstoppableOptionName = Literal[
    "keep_attributes",
    "keep_owner",
    "keep_time",
    "overwrite_existing",
    "recover_and_resume",
    "power_down_when_done",
    "copy_newer_only",
    "skip_damaged",
    "undamaged_first",
    "include_subfolders",
    "overwrite_readonly",
    "copy_empty_folders",
    "show_eta",
]


@dataclass(frozen=True)
class RobocopyBackendOptions:
    """Structured Robocopy options stored in settings and dialogs."""

    include_subdirectories: bool = True
    mirror_target: bool = False
    move_files_for_move: bool = True
    restartable_mode: bool = False
    backup_mode: bool = False
    list_only: bool = False
    suppress_logs: bool = False
    retry_count: int = 0
    wait_seconds: int = 0
    use_multithreading: bool = False
    multithread_count: int = 8
    extra_args: str = ""


@dataclass(frozen=True)
class TeraCopyBackendOptions:
    """Structured TeraCopy options stored in settings and dialogs."""

    close_on_finish: bool = False
    keep_open: bool = False
    verify_after_copy: bool = False
    no_sound: bool = False
    conflict_mode: str = ""
    extra_args: str = ""


@dataclass(frozen=True)
class UnstoppableBackendOptions:
    """Structured Unstoppable Copier options stored in settings and dialogs."""

    use_defaults: bool = True
    keep_attributes: bool = True
    keep_owner: bool = True
    keep_time: bool = True
    overwrite_existing: bool = True
    include_subfolders: bool = True
    recover_and_resume: bool = False
    copy_newer_only: bool = False
    skip_damaged: bool = False
    undamaged_first: bool = False
    overwrite_readonly: bool = False
    copy_empty_folders: bool = False
    show_eta: bool = False
    power_down_when_done: bool = False
    extra_args: str = ""


@dataclass(frozen=True)
class _UnstoppableFlagState:
    """Describe one toggleable Unstoppable Copier flag."""

    code: str
    default_enabled: bool
    attribute_name: UnstoppableOptionName


UNSTOPPABLE_DEFAULT_FLAG_STATES: tuple[_UnstoppableFlagState, ...] = (
    _UnstoppableFlagState(
        "a",
        UnstoppableBackendOptions.keep_attributes,
        "keep_attributes",
    ),
    _UnstoppableFlagState("o", UnstoppableBackendOptions.keep_owner, "keep_owner"),
    _UnstoppableFlagState("t", UnstoppableBackendOptions.keep_time, "keep_time"),
    _UnstoppableFlagState(
        "e",
        UnstoppableBackendOptions.overwrite_existing,
        "overwrite_existing",
    ),
    _UnstoppableFlagState(
        "r",
        UnstoppableBackendOptions.recover_and_resume,
        "recover_and_resume",
    ),
    _UnstoppableFlagState(
        "p",
        UnstoppableBackendOptions.power_down_when_done,
        "power_down_when_done",
    ),
    _UnstoppableFlagState(
        "c",
        UnstoppableBackendOptions.copy_newer_only,
        "copy_newer_only",
    ),
    _UnstoppableFlagState("s", UnstoppableBackendOptions.skip_damaged, "skip_damaged"),
    _UnstoppableFlagState(
        "u",
        UnstoppableBackendOptions.undamaged_first,
        "undamaged_first",
    ),
    _UnstoppableFlagState(
        "i",
        UnstoppableBackendOptions.include_subfolders,
        "include_subfolders",
    ),
    _UnstoppableFlagState(
        "w",
        UnstoppableBackendOptions.overwrite_readonly,
        "overwrite_readonly",
    ),
    _UnstoppableFlagState(
        "f",
        UnstoppableBackendOptions.copy_empty_folders,
        "copy_empty_folders",
    ),
    _UnstoppableFlagState("z", UnstoppableBackendOptions.show_eta, "show_eta"),
)


@dataclass(frozen=True)
class ExternalCopyMoveBackendOptions:
    """Structured generic external copy/move command options."""

    include_operation_token: bool = True
    include_sources: bool = True
    include_target: bool = True
    extra_args: str = ""


@dataclass(frozen=True)
class ResolvedCopyMoveBackendArgs:
    """Resolved command-line templates derived from structured options."""

    robocopy_copy_args: str
    robocopy_move_args: str
    teracopy_args_template: str
    unstoppable_args_template: str
    external_copymove_args_template: str


def robocopy_options_payload(options: RobocopyBackendOptions) -> BackendOptionsPayload:
    """Serialize Robocopy options into a settings-friendly mapping."""

    return {
        "include_subdirectories": options.include_subdirectories,
        "mirror_target": options.mirror_target,
        "move_files_for_move": options.move_files_for_move,
        "restartable_mode": options.restartable_mode,
        "backup_mode": options.backup_mode,
        "list_only": options.list_only,
        "suppress_logs": options.suppress_logs,
        "retry_count": options.retry_count,
        "wait_seconds": options.wait_seconds,
        "use_multithreading": options.use_multithreading,
        "multithread_count": options.multithread_count,
        "extra_args": options.extra_args,
    }


def teracopy_options_payload(options: TeraCopyBackendOptions) -> BackendOptionsPayload:
    """Serialize TeraCopy options into a settings-friendly mapping."""

    return {
        "close_on_finish": options.close_on_finish,
        "keep_open": options.keep_open,
        "verify_after_copy": options.verify_after_copy,
        "no_sound": options.no_sound,
        "conflict_mode": options.conflict_mode,
        "extra_args": options.extra_args,
    }


def unstoppable_options_payload(
    options: UnstoppableBackendOptions,
) -> BackendOptionsPayload:
    """Serialize Unstoppable Copier options into a settings-friendly mapping."""

    return {
        "use_defaults": options.use_defaults,
        "keep_attributes": options.keep_attributes,
        "keep_owner": options.keep_owner,
        "keep_time": options.keep_time,
        "overwrite_existing": options.overwrite_existing,
        "include_subfolders": options.include_subfolders,
        "recover_and_resume": options.recover_and_resume,
        "copy_newer_only": options.copy_newer_only,
        "skip_damaged": options.skip_damaged,
        "undamaged_first": options.undamaged_first,
        "overwrite_readonly": options.overwrite_readonly,
        "copy_empty_folders": options.copy_empty_folders,
        "show_eta": options.show_eta,
        "power_down_when_done": options.power_down_when_done,
        "extra_args": options.extra_args,
    }


def external_copymove_options_payload(
    options: ExternalCopyMoveBackendOptions,
) -> BackendOptionsPayload:
    """Serialize external copy/move options into a settings-friendly mapping."""

    return {
        "include_operation_token": options.include_operation_token,
        "include_sources": options.include_sources,
        "include_target": options.include_target,
        "extra_args": options.extra_args,
    }
