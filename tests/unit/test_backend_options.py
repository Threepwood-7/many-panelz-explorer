from __future__ import annotations

from many_panelz_explorer._operations.backend_options import (
    ExternalCopyMoveBackendOptions,
    RobocopyBackendOptions,
    TeraCopyBackendOptions,
    UnstoppableBackendOptions,
    generate_external_copymove_args_template,
    generate_robocopy_args,
    generate_teracopy_args_template,
    generate_unstoppable_args_template,
    normalize_external_copymove_options,
    normalize_robocopy_options,
    normalize_teracopy_options,
    normalize_unstoppable_options,
    resolve_copy_move_backend_args,
)


def test_robocopy_defaults_are_verbose() -> None:
    options = RobocopyBackendOptions()
    copy_args = generate_robocopy_args(options, kind="copy")
    move_args = generate_robocopy_args(options, kind="move")

    assert "/E" in copy_args
    assert "/R:0" in copy_args
    assert "/W:0" in copy_args
    assert "/NFL" not in copy_args
    assert "/NDL" not in copy_args
    assert "/MOVE" in move_args


def test_structured_normalization_clamps_ranges() -> None:
    options = normalize_robocopy_options(
        {
            "retry_count": 2_000_000,
            "wait_seconds": -3,
            "multithread_count": 0,
            "use_multithreading": True,
        },
        legacy_copy_args="/E /R:0 /W:0",
        legacy_move_args="/E /MOVE /R:0 /W:0",
    )
    assert options.retry_count == 1_000_000
    assert options.wait_seconds == 0
    assert options.multithread_count == 1


def test_resolve_precedence_prefers_raw_when_override_enabled() -> None:
    resolved = resolve_copy_move_backend_args(
        robocopy_options=RobocopyBackendOptions(use_raw_override=True),
        teracopy_options=TeraCopyBackendOptions(
            use_raw_override=True,
            close_on_finish=True,
        ),
        unstoppable_options=UnstoppableBackendOptions(use_raw_override=False),
        external_copymove_options=ExternalCopyMoveBackendOptions(use_raw_override=True),
        raw_robocopy_copy_args="/RAW-COPY",
        raw_robocopy_move_args="/RAW-MOVE",
        raw_teracopy_args_template="{operation} {sources} {target} /RawOnly",
        raw_unstoppable_args_template="{operation} {sources} {target} +x",
        raw_external_copymove_args_template="{sources} {target} --raw",
    )

    assert resolved.robocopy_copy_args == "/RAW-COPY"
    assert resolved.robocopy_move_args == "/RAW-MOVE"
    assert resolved.teracopy_args_template.endswith("/RawOnly")
    assert "/Close" not in resolved.teracopy_args_template
    assert "+x" not in resolved.unstoppable_args_template
    assert resolved.external_copymove_args_template.endswith("--raw")


def test_invalid_payloads_fallback_to_legacy_hydration() -> None:
    robocopy = normalize_robocopy_options(
        "invalid",
        legacy_copy_args="/E /R:3 /W:4 /MT:16 /XO",
        legacy_move_args="/E /MOVE /R:3 /W:4 /MT:16 /XO",
    )
    teracopy = normalize_teracopy_options(
        "invalid",
        legacy_args_template="{operation} {sources} {target} /Close /SkipAll /NoSound",
    )
    unstoppable = normalize_unstoppable_options(
        "invalid",
        legacy_args_template="{operation} {sources} {target} +a -o +s",
    )
    external = normalize_external_copymove_options(
        "invalid",
        legacy_args_template="{sources} {target} --flag",
    )

    assert robocopy.retry_count == 3
    assert robocopy.wait_seconds == 4
    assert robocopy.use_multithreading is True
    assert robocopy.extra_args == "/XO"
    assert teracopy.close_on_finish is True
    assert teracopy.conflict_mode == "/SkipAll"
    assert unstoppable.keep_attributes is True
    assert unstoppable.keep_owner is False
    assert unstoppable.skip_damaged is True
    assert external.include_operation_token is False
    assert external.include_sources is True
    assert external.include_target is True


def test_backend_generators_include_structured_values() -> None:
    teracopy = generate_teracopy_args_template(
        TeraCopyBackendOptions(
            close_on_finish=True,
            verify_after_copy=True,
            no_sound=True,
            conflict_mode="/RenameAll",
            extra_args="/NoHistory",
        )
    )
    unstoppable = generate_unstoppable_args_template(
        UnstoppableBackendOptions(
            use_defaults=False,
            keep_owner=False,
            skip_damaged=True,
            extra_args="+x",
        )
    )
    external = generate_external_copymove_args_template(
        ExternalCopyMoveBackendOptions(
            include_operation_token=False,
            include_sources=True,
            include_target=False,
            extra_args="--fast",
        )
    )

    assert "/Close" in teracopy
    assert "/Verify" in teracopy
    assert "/RenameAll" in teracopy
    assert "-d" in unstoppable
    assert "-o" in unstoppable
    assert "+s" in unstoppable
    assert external == "{sources} --fast"
