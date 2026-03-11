from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

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
    use_raw_override: bool = False


@dataclass(frozen=True)
class TeraCopyBackendOptions:
    close_on_finish: bool = False
    keep_open: bool = False
    verify_after_copy: bool = False
    no_sound: bool = False
    conflict_mode: str = ""
    extra_args: str = ""
    use_raw_override: bool = False


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
    use_raw_override: bool = False


@dataclass(frozen=True)
class ExternalCopyMoveBackendOptions:
    include_operation_token: bool = True
    include_sources: bool = True
    include_target: bool = True
    extra_args: str = ""
    use_raw_override: bool = False


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


def _parse_robocopy_args_line(raw: str, *, is_move: bool) -> RobocopyBackendOptions:
    defaults = RobocopyBackendOptions(move_files_for_move=is_move)
    tokens = split_args(raw)
    if not tokens:
        return defaults
    options = replace(
        defaults,
        include_subdirectories=False,
        mirror_target=False,
        move_files_for_move=False,
        restartable_mode=False,
        backup_mode=False,
        list_only=False,
        suppress_logs=False,
        retry_count=0,
        wait_seconds=0,
        use_multithreading=False,
        multithread_count=8,
        extra_args="",
    )
    quiet_flags = {"/NFL", "/NDL", "/NJH", "/NJS", "/NP"}
    seen_quiet: set[str] = set()
    extra_tokens: list[str] = []

    for token in tokens:
        upper = token.upper()
        if upper == "/E":
            options = replace(options, include_subdirectories=True)
            continue
        if upper == "/MIR":
            options = replace(options, mirror_target=True)
            continue
        if upper == "/MOVE":
            options = replace(options, move_files_for_move=True)
            continue
        if upper == "/Z":
            options = replace(options, restartable_mode=True)
            continue
        if upper == "/B":
            options = replace(options, backup_mode=True)
            continue
        if upper == "/L":
            options = replace(options, list_only=True)
            continue
        if upper.startswith("/R:"):
            options = replace(
                options,
                retry_count=_normalize_int(
                    upper.split(":", 1)[1],
                    fallback=0,
                    minimum=0,
                    maximum=1_000_000,
                ),
            )
            continue
        if upper.startswith("/W:"):
            options = replace(
                options,
                wait_seconds=_normalize_int(
                    upper.split(":", 1)[1],
                    fallback=0,
                    minimum=0,
                    maximum=3_600,
                ),
            )
            continue
        if upper.startswith("/MT:"):
            options = replace(
                options,
                use_multithreading=True,
                multithread_count=_normalize_int(
                    upper.split(":", 1)[1],
                    fallback=8,
                    minimum=1,
                    maximum=128,
                ),
            )
            continue
        if upper == "/MT":
            options = replace(options, use_multithreading=True)
            continue
        if upper in quiet_flags:
            seen_quiet.add(upper)
            continue
        extra_tokens.append(token)

    options = replace(
        options,
        suppress_logs=seen_quiet == quiet_flags,
        extra_args=" ".join(extra_tokens).strip(),
    )
    return options


def hydrate_robocopy_options_from_legacy(
    copy_args: str,
    move_args: str,
) -> RobocopyBackendOptions:
    copy_options = _parse_robocopy_args_line(copy_args, is_move=False)
    move_options = _parse_robocopy_args_line(move_args, is_move=True)
    if str(copy_args or "").strip():
        merged = copy_options
    elif str(move_args or "").strip():
        merged = replace(move_options, move_files_for_move=move_options.move_files_for_move)
    else:
        merged = RobocopyBackendOptions()

    merged = replace(merged, move_files_for_move=move_options.move_files_for_move)
    if not merged.extra_args and move_options.extra_args:
        merged = replace(merged, extra_args=move_options.extra_args)
    return merged


def normalize_robocopy_options(
    raw: Any,
    *,
    legacy_copy_args: str,
    legacy_move_args: str,
) -> RobocopyBackendOptions:
    if not isinstance(raw, dict):
        return hydrate_robocopy_options_from_legacy(legacy_copy_args, legacy_move_args)
    options = RobocopyBackendOptions(
        include_subdirectories=_normalize_bool(
            raw.get("include_subdirectories"),
            fallback=RobocopyBackendOptions.include_subdirectories,
        ),
        mirror_target=_normalize_bool(
            raw.get("mirror_target"),
            fallback=RobocopyBackendOptions.mirror_target,
        ),
        move_files_for_move=_normalize_bool(
            raw.get("move_files_for_move"),
            fallback=RobocopyBackendOptions.move_files_for_move,
        ),
        restartable_mode=_normalize_bool(
            raw.get("restartable_mode"),
            fallback=RobocopyBackendOptions.restartable_mode,
        ),
        backup_mode=_normalize_bool(
            raw.get("backup_mode"),
            fallback=RobocopyBackendOptions.backup_mode,
        ),
        list_only=_normalize_bool(
            raw.get("list_only"),
            fallback=RobocopyBackendOptions.list_only,
        ),
        suppress_logs=_normalize_bool(
            raw.get("suppress_logs"),
            fallback=RobocopyBackendOptions.suppress_logs,
        ),
        retry_count=_normalize_int(
            raw.get("retry_count"),
            fallback=RobocopyBackendOptions.retry_count,
            minimum=0,
            maximum=1_000_000,
        ),
        wait_seconds=_normalize_int(
            raw.get("wait_seconds"),
            fallback=RobocopyBackendOptions.wait_seconds,
            minimum=0,
            maximum=3_600,
        ),
        use_multithreading=_normalize_bool(
            raw.get("use_multithreading"),
            fallback=RobocopyBackendOptions.use_multithreading,
        ),
        multithread_count=_normalize_int(
            raw.get("multithread_count"),
            fallback=RobocopyBackendOptions.multithread_count,
            minimum=1,
            maximum=128,
        ),
        extra_args=_normalize_text(raw.get("extra_args"), fallback=""),
        use_raw_override=_normalize_bool(raw.get("use_raw_override"), fallback=False),
    )
    return options


def hydrate_teracopy_options_from_legacy(raw_template: str) -> TeraCopyBackendOptions:
    options = TeraCopyBackendOptions()
    tokens = split_args(raw_template)
    if not tokens:
        return options
    extra_tokens: list[str] = []
    for token in tokens:
        upper = token.upper()
        if token in {"{operation}", "{sources}", "{target}"}:
            continue
        if upper == "/CLOSE":
            options = replace(options, close_on_finish=True)
            continue
        if upper == "/NOCLOSE":
            options = replace(options, keep_open=True)
            continue
        if upper == "/VERIFY":
            options = replace(options, verify_after_copy=True)
            continue
        if upper == "/NOSOUND":
            options = replace(options, no_sound=True)
            continue
        if upper in _TERACOPY_CONFLICT_OPTIONS:
            options = replace(options, conflict_mode=token)
            continue
        extra_tokens.append(token)
    options = replace(options, extra_args=" ".join(extra_tokens).strip())
    if options.close_on_finish and options.keep_open:
        options = replace(options, keep_open=False)
    return options


def normalize_teracopy_options(
    raw: Any,
    *,
    legacy_args_template: str,
) -> TeraCopyBackendOptions:
    if not isinstance(raw, dict):
        return hydrate_teracopy_options_from_legacy(legacy_args_template)
    options = TeraCopyBackendOptions(
        close_on_finish=_normalize_bool(
            raw.get("close_on_finish"),
            fallback=TeraCopyBackendOptions.close_on_finish,
        ),
        keep_open=_normalize_bool(
            raw.get("keep_open"),
            fallback=TeraCopyBackendOptions.keep_open,
        ),
        verify_after_copy=_normalize_bool(
            raw.get("verify_after_copy"),
            fallback=TeraCopyBackendOptions.verify_after_copy,
        ),
        no_sound=_normalize_bool(
            raw.get("no_sound"),
            fallback=TeraCopyBackendOptions.no_sound,
        ),
        conflict_mode=_normalize_conflict_mode(raw.get("conflict_mode")),
        extra_args=_normalize_text(raw.get("extra_args"), fallback=""),
        use_raw_override=_normalize_bool(raw.get("use_raw_override"), fallback=False),
    )
    if options.close_on_finish and options.keep_open:
        options = replace(options, keep_open=False)
    return options


def hydrate_unstoppable_options_from_legacy(raw_template: str) -> UnstoppableBackendOptions:
    options = UnstoppableBackendOptions()
    tokens = split_args(raw_template)
    if not tokens:
        return options
    extra_tokens: list[str] = []
    flag_map = {
        "d": "use_defaults",
        "a": "keep_attributes",
        "o": "keep_owner",
        "t": "keep_time",
        "e": "overwrite_existing",
        "i": "include_subfolders",
        "r": "recover_and_resume",
        "c": "copy_newer_only",
        "s": "skip_damaged",
        "u": "undamaged_first",
        "w": "overwrite_readonly",
        "f": "copy_empty_folders",
        "z": "show_eta",
        "p": "power_down_when_done",
    }
    for token in tokens:
        if token in {"{operation}", "{sources}", "{target}"}:
            continue
        if len(token) == 2 and token[0] in {"+", "-"} and token[1].lower() in flag_map:
            field = flag_map[token[1].lower()]
            options = replace(options, **{field: token[0] == "+"})
            continue
        if token.startswith("+dm") or token.startswith("+d") or token.startswith("-d"):
            if token.startswith("-d"):
                options = replace(options, use_defaults=False)
            elif token.startswith("+d"):
                options = replace(options, use_defaults=True)
            continue
        extra_tokens.append(token)
    return replace(options, extra_args=" ".join(extra_tokens).strip())


def normalize_unstoppable_options(
    raw: Any,
    *,
    legacy_args_template: str,
) -> UnstoppableBackendOptions:
    if not isinstance(raw, dict):
        return hydrate_unstoppable_options_from_legacy(legacy_args_template)
    return UnstoppableBackendOptions(
        use_defaults=_normalize_bool(
            raw.get("use_defaults"),
            fallback=UnstoppableBackendOptions.use_defaults,
        ),
        keep_attributes=_normalize_bool(
            raw.get("keep_attributes"),
            fallback=UnstoppableBackendOptions.keep_attributes,
        ),
        keep_owner=_normalize_bool(
            raw.get("keep_owner"),
            fallback=UnstoppableBackendOptions.keep_owner,
        ),
        keep_time=_normalize_bool(
            raw.get("keep_time"),
            fallback=UnstoppableBackendOptions.keep_time,
        ),
        overwrite_existing=_normalize_bool(
            raw.get("overwrite_existing"),
            fallback=UnstoppableBackendOptions.overwrite_existing,
        ),
        include_subfolders=_normalize_bool(
            raw.get("include_subfolders"),
            fallback=UnstoppableBackendOptions.include_subfolders,
        ),
        recover_and_resume=_normalize_bool(
            raw.get("recover_and_resume"),
            fallback=UnstoppableBackendOptions.recover_and_resume,
        ),
        copy_newer_only=_normalize_bool(
            raw.get("copy_newer_only"),
            fallback=UnstoppableBackendOptions.copy_newer_only,
        ),
        skip_damaged=_normalize_bool(
            raw.get("skip_damaged"),
            fallback=UnstoppableBackendOptions.skip_damaged,
        ),
        undamaged_first=_normalize_bool(
            raw.get("undamaged_first"),
            fallback=UnstoppableBackendOptions.undamaged_first,
        ),
        overwrite_readonly=_normalize_bool(
            raw.get("overwrite_readonly"),
            fallback=UnstoppableBackendOptions.overwrite_readonly,
        ),
        copy_empty_folders=_normalize_bool(
            raw.get("copy_empty_folders"),
            fallback=UnstoppableBackendOptions.copy_empty_folders,
        ),
        show_eta=_normalize_bool(
            raw.get("show_eta"),
            fallback=UnstoppableBackendOptions.show_eta,
        ),
        power_down_when_done=_normalize_bool(
            raw.get("power_down_when_done"),
            fallback=UnstoppableBackendOptions.power_down_when_done,
        ),
        extra_args=_normalize_text(raw.get("extra_args"), fallback=""),
        use_raw_override=_normalize_bool(raw.get("use_raw_override"), fallback=False),
    )


def hydrate_external_copymove_options_from_legacy(
    raw_template: str,
) -> ExternalCopyMoveBackendOptions:
    options = ExternalCopyMoveBackendOptions()
    tokens = split_args(raw_template)
    if not tokens:
        return options
    include_operation = False
    include_sources = False
    include_target = False
    extra_tokens: list[str] = []
    for token in tokens:
        if token == "{operation}":
            include_operation = True
            continue
        if token in {"{source}", "{sources}"}:
            include_sources = True
            continue
        if token == "{target}":
            include_target = True
            continue
        extra_tokens.append(token)
    if not include_operation and not include_sources and not include_target:
        include_operation = True
        include_sources = True
        include_target = True
    return ExternalCopyMoveBackendOptions(
        include_operation_token=include_operation,
        include_sources=include_sources,
        include_target=include_target,
        extra_args=" ".join(extra_tokens).strip(),
    )


def normalize_external_copymove_options(
    raw: Any,
    *,
    legacy_args_template: str,
) -> ExternalCopyMoveBackendOptions:
    if not isinstance(raw, dict):
        return hydrate_external_copymove_options_from_legacy(legacy_args_template)
    options = ExternalCopyMoveBackendOptions(
        include_operation_token=_normalize_bool(
            raw.get("include_operation_token"),
            fallback=ExternalCopyMoveBackendOptions.include_operation_token,
        ),
        include_sources=_normalize_bool(
            raw.get("include_sources"),
            fallback=ExternalCopyMoveBackendOptions.include_sources,
        ),
        include_target=_normalize_bool(
            raw.get("include_target"),
            fallback=ExternalCopyMoveBackendOptions.include_target,
        ),
        extra_args=_normalize_text(raw.get("extra_args"), fallback=""),
        use_raw_override=_normalize_bool(raw.get("use_raw_override"), fallback=False),
    )
    if not options.include_operation_token and not options.include_sources and not options.include_target:
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


def generate_unstoppable_args_template(options: UnstoppableBackendOptions) -> str:
    parts = ["{operation}", "{sources}", "{target}"]
    if not options.use_defaults:
        parts.append("-d")
    flag_map = [
        ("a", options.keep_attributes),
        ("o", options.keep_owner),
        ("t", options.keep_time),
        ("e", options.overwrite_existing),
        ("i", options.include_subfolders),
        ("r", options.recover_and_resume),
        ("c", options.copy_newer_only),
        ("s", options.skip_damaged),
        ("u", options.undamaged_first),
        ("w", options.overwrite_readonly),
        ("f", options.copy_empty_folders),
        ("z", options.show_eta),
        ("p", options.power_down_when_done),
    ]
    for code, enabled in flag_map:
        parts.append(f"+{code}" if enabled else f"-{code}")
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


def _resolve_value(*, raw_value: str, generated_value: str, use_raw_override: bool, fallback: str) -> str:
    generated = _normalize_text(generated_value, fallback="")
    if use_raw_override:
        raw = _normalize_text(raw_value, fallback="")
        if raw:
            return raw
    if generated:
        return generated
    return fallback


def resolve_copy_move_backend_args(
    *,
    robocopy_options: RobocopyBackendOptions,
    teracopy_options: TeraCopyBackendOptions,
    unstoppable_options: UnstoppableBackendOptions,
    external_copymove_options: ExternalCopyMoveBackendOptions,
    raw_robocopy_copy_args: str,
    raw_robocopy_move_args: str,
    raw_teracopy_args_template: str,
    raw_unstoppable_args_template: str,
    raw_external_copymove_args_template: str,
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
            raw_value=raw_robocopy_copy_args,
            generated_value=generated_robocopy_copy,
            use_raw_override=robocopy_options.use_raw_override,
            fallback=DEFAULT_ROBOCOPY_COPY_ARGS,
        ),
        robocopy_move_args=_resolve_value(
            raw_value=raw_robocopy_move_args,
            generated_value=generated_robocopy_move,
            use_raw_override=robocopy_options.use_raw_override,
            fallback=DEFAULT_ROBOCOPY_MOVE_ARGS,
        ),
        teracopy_args_template=_resolve_value(
            raw_value=raw_teracopy_args_template,
            generated_value=generated_teracopy,
            use_raw_override=teracopy_options.use_raw_override,
            fallback=DEFAULT_TERA_COPY_ARGS,
        ),
        unstoppable_args_template=_resolve_value(
            raw_value=raw_unstoppable_args_template,
            generated_value=generated_unstoppable,
            use_raw_override=unstoppable_options.use_raw_override,
            fallback=DEFAULT_UNSTOPPABLE_ARGS,
        ),
        external_copymove_args_template=_resolve_value(
            raw_value=raw_external_copymove_args_template,
            generated_value=generated_external,
            use_raw_override=external_copymove_options.use_raw_override,
            fallback=DEFAULT_GENERIC_COPYMOVE_ARGS,
        ),
    )
