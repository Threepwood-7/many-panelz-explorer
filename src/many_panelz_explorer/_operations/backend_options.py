"""Normalize and render structured backend option payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import cast

from .backend_option_models import (
    UNSTOPPABLE_DEFAULT_FLAG_STATES,
    BackendOptionsPayload,
    CopyMoveKind,
    ExternalCopyMoveBackendOptions,
    ResolvedCopyMoveBackendArgs,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    UnstoppableOptionName,
    external_copymove_options_payload,
    robocopy_options_payload,
    teracopy_options_payload,
    unstoppable_options_payload,
)
from .path_helpers import split_args
from .types import (
    DEFAULT_GENERIC_COPYMOVE_ARGS,
    DEFAULT_ROBOCOPY_COPY_ARGS,
    DEFAULT_ROBOCOPY_MOVE_ARGS,
    DEFAULT_TERA_COPY_ARGS,
    DEFAULT_UNSTOPPABLE_ARGS,
)

_TERACOPY_CONFLICT_OPTIONS = {
    "",
    "/OVERWRITEALL",
    "/SKIPALL",
    "/RENAMEALL",
    "/OVERWRITEOLDER",
    "/OVERWRITEDIFFSIZE",
    "/RENAMECOPIED",
    "/RENAMEDESTINATION",
}


def _string_object_mapping(value: object) -> dict[str, object] | None:
    """Normalize backend-option payloads into string-key mappings."""

    if not isinstance(value, Mapping):
        return None
    mapping = cast("Mapping[object, object]", value)
    return {str(key): item for key, item in mapping.items()}


def _normalize_bool(raw: object, *, fallback: bool) -> bool:
    """Normalize a raw payload value into a boolean."""

    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if raw is None:
        return fallback
    return bool(raw)


def _normalize_int(
    raw: object,
    *,
    fallback: int,
    minimum: int,
    maximum: int,
) -> int:
    """Normalize a raw payload value into a bounded integer."""

    value: int
    if isinstance(raw, bool):
        value = int(raw)
    elif isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        try:
            value = int(raw)
        except ValueError:
            return fallback
    else:
        return fallback
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _normalize_text(raw: object, *, fallback: str = "") -> str:
    """Normalize a raw payload value into a trimmed string."""

    if raw is None:
        return fallback
    text = str(raw).strip()
    if text:
        return text
    return fallback


def _normalize_conflict_mode(raw: object) -> str:
    """Normalize a TeraCopy conflict mode token."""

    value = str(raw or "").strip()
    if not value:
        return ""
    normalized = value.upper()
    if not normalized.startswith("/"):
        normalized = f"/{normalized.lstrip('/')}"
    if normalized in _TERACOPY_CONFLICT_OPTIONS:
        return value if value.startswith("/") else f"/{value.lstrip('/')}"
    return ""


def normalize_robocopy_options(raw: object) -> RobocopyBackendOptions:
    """Normalize stored or UI-provided Robocopy option payloads."""

    raw_map = _string_object_mapping(raw)
    if raw_map is None:
        return RobocopyBackendOptions()
    options = RobocopyBackendOptions(
        include_subdirectories=_normalize_bool(
            raw_map.get("include_subdirectories"),
            fallback=RobocopyBackendOptions.include_subdirectories,
        ),
        mirror_target=_normalize_bool(
            raw_map.get("mirror_target"),
            fallback=RobocopyBackendOptions.mirror_target,
        ),
        move_files_for_move=_normalize_bool(
            raw_map.get("move_files_for_move"),
            fallback=RobocopyBackendOptions.move_files_for_move,
        ),
        restartable_mode=_normalize_bool(
            raw_map.get("restartable_mode"),
            fallback=RobocopyBackendOptions.restartable_mode,
        ),
        backup_mode=_normalize_bool(
            raw_map.get("backup_mode"),
            fallback=RobocopyBackendOptions.backup_mode,
        ),
        list_only=_normalize_bool(
            raw_map.get("list_only"),
            fallback=RobocopyBackendOptions.list_only,
        ),
        suppress_logs=_normalize_bool(
            raw_map.get("suppress_logs"),
            fallback=RobocopyBackendOptions.suppress_logs,
        ),
        retry_count=_normalize_int(
            raw_map.get("retry_count"),
            fallback=RobocopyBackendOptions.retry_count,
            minimum=0,
            maximum=1_000_000,
        ),
        wait_seconds=_normalize_int(
            raw_map.get("wait_seconds"),
            fallback=RobocopyBackendOptions.wait_seconds,
            minimum=0,
            maximum=3_600,
        ),
        use_multithreading=_normalize_bool(
            raw_map.get("use_multithreading"),
            fallback=RobocopyBackendOptions.use_multithreading,
        ),
        multithread_count=_normalize_int(
            raw_map.get("multithread_count"),
            fallback=RobocopyBackendOptions.multithread_count,
            minimum=1,
            maximum=128,
        ),
        extra_args=_normalize_text(raw_map.get("extra_args"), fallback=""),
    )
    if options.use_multithreading:
        return options
    return replace(options, multithread_count=RobocopyBackendOptions.multithread_count)


def normalize_teracopy_options(raw: object) -> TeraCopyBackendOptions:
    """Normalize stored or UI-provided TeraCopy option payloads."""

    raw_map = _string_object_mapping(raw)
    if raw_map is None:
        return TeraCopyBackendOptions()
    options = TeraCopyBackendOptions(
        close_on_finish=_normalize_bool(
            raw_map.get("close_on_finish"),
            fallback=TeraCopyBackendOptions.close_on_finish,
        ),
        keep_open=_normalize_bool(
            raw_map.get("keep_open"),
            fallback=TeraCopyBackendOptions.keep_open,
        ),
        verify_after_copy=_normalize_bool(
            raw_map.get("verify_after_copy"),
            fallback=TeraCopyBackendOptions.verify_after_copy,
        ),
        no_sound=_normalize_bool(
            raw_map.get("no_sound"),
            fallback=TeraCopyBackendOptions.no_sound,
        ),
        conflict_mode=_normalize_conflict_mode(raw_map.get("conflict_mode")),
        extra_args=_normalize_text(raw_map.get("extra_args"), fallback=""),
    )
    if options.close_on_finish and options.keep_open:
        options = replace(options, keep_open=False)
    return options


def normalize_unstoppable_options(raw: object) -> UnstoppableBackendOptions:
    """Normalize stored or UI-provided Unstoppable Copier payloads."""

    raw_map = _string_object_mapping(raw)
    if raw_map is None:
        return UnstoppableBackendOptions()
    return UnstoppableBackendOptions(
        use_defaults=_normalize_bool(
            raw_map.get("use_defaults"),
            fallback=UnstoppableBackendOptions.use_defaults,
        ),
        keep_attributes=_normalize_bool(
            raw_map.get("keep_attributes"),
            fallback=UnstoppableBackendOptions.keep_attributes,
        ),
        keep_owner=_normalize_bool(
            raw_map.get("keep_owner"),
            fallback=UnstoppableBackendOptions.keep_owner,
        ),
        keep_time=_normalize_bool(
            raw_map.get("keep_time"),
            fallback=UnstoppableBackendOptions.keep_time,
        ),
        overwrite_existing=_normalize_bool(
            raw_map.get("overwrite_existing"),
            fallback=UnstoppableBackendOptions.overwrite_existing,
        ),
        include_subfolders=_normalize_bool(
            raw_map.get("include_subfolders"),
            fallback=UnstoppableBackendOptions.include_subfolders,
        ),
        recover_and_resume=_normalize_bool(
            raw_map.get("recover_and_resume"),
            fallback=UnstoppableBackendOptions.recover_and_resume,
        ),
        copy_newer_only=_normalize_bool(
            raw_map.get("copy_newer_only"),
            fallback=UnstoppableBackendOptions.copy_newer_only,
        ),
        skip_damaged=_normalize_bool(
            raw_map.get("skip_damaged"),
            fallback=UnstoppableBackendOptions.skip_damaged,
        ),
        undamaged_first=_normalize_bool(
            raw_map.get("undamaged_first"),
            fallback=UnstoppableBackendOptions.undamaged_first,
        ),
        overwrite_readonly=_normalize_bool(
            raw_map.get("overwrite_readonly"),
            fallback=UnstoppableBackendOptions.overwrite_readonly,
        ),
        copy_empty_folders=_normalize_bool(
            raw_map.get("copy_empty_folders"),
            fallback=UnstoppableBackendOptions.copy_empty_folders,
        ),
        show_eta=_normalize_bool(
            raw_map.get("show_eta"),
            fallback=UnstoppableBackendOptions.show_eta,
        ),
        power_down_when_done=_normalize_bool(
            raw_map.get("power_down_when_done"),
            fallback=UnstoppableBackendOptions.power_down_when_done,
        ),
        extra_args=_normalize_text(raw_map.get("extra_args"), fallback=""),
    )


def normalize_external_copymove_options(raw: object) -> ExternalCopyMoveBackendOptions:
    """Normalize stored or UI-provided external command option payloads."""

    raw_map = _string_object_mapping(raw)
    if raw_map is None:
        return ExternalCopyMoveBackendOptions()
    options = ExternalCopyMoveBackendOptions(
        include_operation_token=_normalize_bool(
            raw_map.get("include_operation_token"),
            fallback=ExternalCopyMoveBackendOptions.include_operation_token,
        ),
        include_sources=_normalize_bool(
            raw_map.get("include_sources"),
            fallback=ExternalCopyMoveBackendOptions.include_sources,
        ),
        include_target=_normalize_bool(
            raw_map.get("include_target"),
            fallback=ExternalCopyMoveBackendOptions.include_target,
        ),
        extra_args=_normalize_text(raw_map.get("extra_args"), fallback=""),
    )
    if (
        not options.include_operation_token
        and not options.include_sources
        and not options.include_target
    ):
        return replace(
            options,
            include_operation_token=True,
            include_sources=True,
            include_target=True,
        )
    return options


def generate_robocopy_args(
    options: RobocopyBackendOptions,
    *,
    kind: CopyMoveKind,
) -> str:
    """Render Robocopy options into a command-line argument string."""
    parts: list[str] = []
    if options.include_subdirectories:
        parts.append("/E")
    if options.mirror_target:
        parts.append("/MIR")
    if kind == "move" and options.move_files_for_move:
        parts.append("/MOVE")
    if options.restartable_mode:
        parts.append("/Z")
    if options.backup_mode:
        parts.append("/B")
    if options.list_only:
        parts.append("/L")
    parts.append(f"/R:{int(options.retry_count)}")
    parts.append(f"/W:{int(options.wait_seconds)}")
    if options.use_multithreading:
        parts.append(f"/MT:{int(options.multithread_count)}")
    if options.suppress_logs:
        parts.extend(["/NFL", "/NDL", "/NJH", "/NJS", "/NP"])
    extra = _normalize_text(options.extra_args, fallback="")
    if extra:
        parts.extend(split_args(extra))
    return " ".join(parts).strip()


def generate_teracopy_args_template(options: TeraCopyBackendOptions) -> str:
    """Render TeraCopy options into an argument template string."""
    parts = ["{operation}", "{sources}", "{target}"]
    if options.close_on_finish:
        parts.append("/Close")
    if options.keep_open:
        parts.append("/NoClose")
    if options.verify_after_copy:
        parts.append("/Verify")
    if options.no_sound:
        parts.append("/NoSound")
    conflict = _normalize_conflict_mode(options.conflict_mode)
    if conflict:
        parts.append(conflict)
    extra = _normalize_text(options.extra_args, fallback="")
    if extra:
        parts.extend(split_args(extra))
    return " ".join(parts).strip()


def _unstoppable_option_enabled(
    options: UnstoppableBackendOptions,
    attribute_name: UnstoppableOptionName,
) -> bool:
    """Return the current value for one named Unstoppable option."""

    match attribute_name:
        case "keep_attributes":
            return options.keep_attributes
        case "keep_owner":
            return options.keep_owner
        case "keep_time":
            return options.keep_time
        case "overwrite_existing":
            return options.overwrite_existing
        case "recover_and_resume":
            return options.recover_and_resume
        case "power_down_when_done":
            return options.power_down_when_done
        case "copy_newer_only":
            return options.copy_newer_only
        case "skip_damaged":
            return options.skip_damaged
        case "undamaged_first":
            return options.undamaged_first
        case "include_subfolders":
            return options.include_subfolders
        case "overwrite_readonly":
            return options.overwrite_readonly
        case "copy_empty_folders":
            return options.copy_empty_folders
        case "show_eta":
            return options.show_eta


def generate_unstoppable_switch_args(
    options: UnstoppableBackendOptions,
) -> list[str]:
    """Render Unstoppable Copier switches as grouped plus/minus tokens."""
    plus_letters: list[str] = []
    minus_letters: list[str] = []
    if options.use_defaults:
        plus_letters.append("d")
    for flag in UNSTOPPABLE_DEFAULT_FLAG_STATES:
        enabled = _unstoppable_option_enabled(options, flag.attribute_name)
        if enabled == flag.default_enabled:
            continue
        if enabled:
            plus_letters.append(flag.code)
        else:
            minus_letters.append(flag.code)

    tokens: list[str] = []
    if plus_letters:
        tokens.append(f"+{''.join(plus_letters)}")
    if minus_letters:
        tokens.append(f"-{''.join(minus_letters)}")
    return tokens


def generate_unstoppable_args_template(options: UnstoppableBackendOptions) -> str:
    """Render Unstoppable Copier options into an argument template string."""
    parts = generate_unstoppable_switch_args(options)
    extra = _normalize_text(options.extra_args, fallback="")
    if extra:
        parts.extend(split_args(extra))
    return " ".join(parts).strip()


def generate_external_copymove_args_template(
    options: ExternalCopyMoveBackendOptions,
) -> str:
    """Render external command options into an argument template string."""
    parts: list[str] = []
    if options.include_operation_token:
        parts.append("{operation}")
    if options.include_sources:
        parts.append("{sources}")
    if options.include_target:
        parts.append("{target}")
    if not parts:
        parts = ["{operation}", "{sources}", "{target}"]
    extra = _normalize_text(options.extra_args, fallback="")
    if extra:
        parts.extend(split_args(extra))
    return " ".join(parts).strip()


def _resolve_value(*, generated_value: str, fallback: str) -> str:
    """Return the generated value, or the configured fallback when empty."""

    generated = _normalize_text(generated_value, fallback="")
    if generated:
        return generated
    return fallback


def resolve_copy_move_backend_args(
    *,
    robocopy_options: RobocopyBackendOptions,
    teracopy_options: TeraCopyBackendOptions,
    unstoppable_options: UnstoppableBackendOptions,
    external_copymove_options: ExternalCopyMoveBackendOptions,
) -> ResolvedCopyMoveBackendArgs:
    """Resolve structured backend options into executable argument templates."""
    generated_robocopy_copy = generate_robocopy_args(robocopy_options, kind="copy")
    generated_robocopy_move = generate_robocopy_args(robocopy_options, kind="move")
    generated_teracopy = generate_teracopy_args_template(teracopy_options)
    generated_unstoppable = generate_unstoppable_args_template(unstoppable_options)
    generated_external = generate_external_copymove_args_template(
        external_copymove_options
    )

    return ResolvedCopyMoveBackendArgs(
        robocopy_copy_args=_resolve_value(
            generated_value=generated_robocopy_copy,
            fallback=DEFAULT_ROBOCOPY_COPY_ARGS,
        ),
        robocopy_move_args=_resolve_value(
            generated_value=generated_robocopy_move,
            fallback=DEFAULT_ROBOCOPY_MOVE_ARGS,
        ),
        teracopy_args_template=_resolve_value(
            generated_value=generated_teracopy,
            fallback=DEFAULT_TERA_COPY_ARGS,
        ),
        unstoppable_args_template=_resolve_value(
            generated_value=generated_unstoppable,
            fallback=DEFAULT_UNSTOPPABLE_ARGS,
        ),
        external_copymove_args_template=_resolve_value(
            generated_value=generated_external,
            fallback=DEFAULT_GENERIC_COPYMOVE_ARGS,
        ),
    )


__all__ = [
    "BackendOptionsPayload",
    "CopyMoveKind",
    "ExternalCopyMoveBackendOptions",
    "ResolvedCopyMoveBackendArgs",
    "RobocopyBackendOptions",
    "TeraCopyBackendOptions",
    "UnstoppableBackendOptions",
    "external_copymove_options_payload",
    "generate_external_copymove_args_template",
    "generate_robocopy_args",
    "generate_teracopy_args_template",
    "generate_unstoppable_args_template",
    "generate_unstoppable_switch_args",
    "normalize_external_copymove_options",
    "normalize_robocopy_options",
    "normalize_teracopy_options",
    "normalize_unstoppable_options",
    "resolve_copy_move_backend_args",
    "robocopy_options_payload",
    "teracopy_options_payload",
    "unstoppable_options_payload",
]
