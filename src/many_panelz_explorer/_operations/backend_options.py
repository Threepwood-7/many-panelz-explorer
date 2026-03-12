from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, cast

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


def _string_object_mapping(value: Any) -> dict[str, Any] | None:
    """Normalize backend-option payloads into string-key mappings."""

    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in cast("dict[object, object]", value).items()}


@dataclass(frozen=True)
class RobocopyBackendOptions:
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
    close_on_finish: bool = False
    keep_open: bool = False
    verify_after_copy: bool = False
    no_sound: bool = False
    conflict_mode: str = ""
    extra_args: str = ""


@dataclass(frozen=True)
class UnstoppableBackendOptions:
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


_UNSTOPPABLE_DEFAULT_FLAG_STATES: tuple[tuple[str, bool, str], ...] = (
    ("a", UnstoppableBackendOptions.keep_attributes, "keep_attributes"),
    ("o", UnstoppableBackendOptions.keep_owner, "keep_owner"),
    ("t", UnstoppableBackendOptions.keep_time, "keep_time"),
    ("e", UnstoppableBackendOptions.overwrite_existing, "overwrite_existing"),
    ("r", UnstoppableBackendOptions.recover_and_resume, "recover_and_resume"),
    ("p", UnstoppableBackendOptions.power_down_when_done, "power_down_when_done"),
    ("c", UnstoppableBackendOptions.copy_newer_only, "copy_newer_only"),
    ("s", UnstoppableBackendOptions.skip_damaged, "skip_damaged"),
    ("u", UnstoppableBackendOptions.undamaged_first, "undamaged_first"),
    ("i", UnstoppableBackendOptions.include_subfolders, "include_subfolders"),
    ("w", UnstoppableBackendOptions.overwrite_readonly, "overwrite_readonly"),
    ("f", UnstoppableBackendOptions.copy_empty_folders, "copy_empty_folders"),
    ("z", UnstoppableBackendOptions.show_eta, "show_eta"),
)


@dataclass(frozen=True)
class ExternalCopyMoveBackendOptions:
    include_operation_token: bool = True
    include_sources: bool = True
    include_target: bool = True
    extra_args: str = ""


@dataclass(frozen=True)
class ResolvedCopyMoveBackendArgs:
    robocopy_copy_args: str
    robocopy_move_args: str
    teracopy_args_template: str
    unstoppable_args_template: str
    external_copymove_args_template: str


def _normalize_bool(raw: Any, *, fallback: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if raw is None:
        return fallback
    return bool(raw)


def _normalize_int(raw: Any, *, fallback: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _normalize_text(raw: Any, *, fallback: str = "") -> str:
    if raw is None:
        return fallback
    text = str(raw).strip()
    if text:
        return text
    return fallback


def _normalize_conflict_mode(raw: Any) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    normalized = value.upper()
    if normalized in _TERACOPY_CONFLICT_OPTIONS:
        return value if value.startswith("/") else f"/{value.lstrip('/')}"
    return ""


def robocopy_options_payload(options: RobocopyBackendOptions) -> dict[str, Any]:
    return asdict(options)


def teracopy_options_payload(options: TeraCopyBackendOptions) -> dict[str, Any]:
    return asdict(options)


def unstoppable_options_payload(options: UnstoppableBackendOptions) -> dict[str, Any]:
    return asdict(options)


def external_copymove_options_payload(
    options: ExternalCopyMoveBackendOptions,
) -> dict[str, Any]:
    return asdict(options)


def normalize_robocopy_options(raw: Any) -> RobocopyBackendOptions:
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


def normalize_teracopy_options(raw: Any) -> TeraCopyBackendOptions:
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


def normalize_unstoppable_options(raw: Any) -> UnstoppableBackendOptions:
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


def normalize_external_copymove_options(raw: Any) -> ExternalCopyMoveBackendOptions:
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


def generate_robocopy_args(options: RobocopyBackendOptions, *, kind: str) -> str:
    parts: list[str] = []
    if options.include_subdirectories:
        parts.append("/E")
    if options.mirror_target:
        parts.append("/MIR")
    if str(kind).strip().lower() == "move" and options.move_files_for_move:
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


def generate_unstoppable_switch_args(
    options: UnstoppableBackendOptions,
) -> list[str]:
    plus_letters: list[str] = []
    minus_letters: list[str] = []
    if options.use_defaults:
        plus_letters.append("d")
    for code, default_enabled, attr_name in _UNSTOPPABLE_DEFAULT_FLAG_STATES:
        enabled = bool(getattr(options, attr_name))
        if enabled == bool(default_enabled):
            continue
        if enabled:
            plus_letters.append(code)
        else:
            minus_letters.append(code)

    tokens: list[str] = []
    if plus_letters:
        tokens.append(f"+{''.join(plus_letters)}")
    if minus_letters:
        tokens.append(f"-{''.join(minus_letters)}")
    return tokens


def generate_unstoppable_args_template(options: UnstoppableBackendOptions) -> str:
    parts = generate_unstoppable_switch_args(options)
    extra = _normalize_text(options.extra_args, fallback="")
    if extra:
        parts.extend(split_args(extra))
    return " ".join(parts).strip()


def generate_external_copymove_args_template(
    options: ExternalCopyMoveBackendOptions,
) -> str:
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
