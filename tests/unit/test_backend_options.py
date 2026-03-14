from __future__ import annotations

from collections import UserDict

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
        }
    )
    assert options.retry_count == 1_000_000
    assert options.wait_seconds == 0
    assert options.multithread_count == 1


def test_teracopy_normalization_normalizes_conflicts_and_mutual_exclusion() -> None:
    options = normalize_teracopy_options(
        {
            "close_on_finish": True,
            "keep_open": True,
            "conflict_mode": "renameall",
        }
    )

    assert options.close_on_finish is True
    assert options.keep_open is False
    assert options.conflict_mode == "/renameall"


def test_resolve_uses_structured_generation_only() -> None:
    resolved = resolve_copy_move_backend_args(
        robocopy_options=RobocopyBackendOptions(
            retry_count=5,
            wait_seconds=2,
            extra_args="/XO",
        ),
        teracopy_options=TeraCopyBackendOptions(
            close_on_finish=True,
            extra_args="/NoHistory",
        ),
        unstoppable_options=UnstoppableBackendOptions(extra_args="+x"),
        external_copymove_options=ExternalCopyMoveBackendOptions(
            include_operation_token=False,
            include_sources=True,
            include_target=True,
            extra_args="--raw",
        ),
    )

    assert "/R:5" in resolved.robocopy_copy_args
    assert "/W:2" in resolved.robocopy_copy_args
    assert "/XO" in resolved.robocopy_copy_args
    assert "/MOVE" not in resolved.robocopy_copy_args
    assert "/Close" in resolved.teracopy_args_template
    assert "/NoHistory" in resolved.teracopy_args_template
    assert "+x" in resolved.unstoppable_args_template
    assert resolved.external_copymove_args_template.endswith("--raw")


def test_invalid_payloads_fallback_to_defaults() -> None:
    robocopy = normalize_robocopy_options(
        "invalid",
    )
    teracopy = normalize_teracopy_options(
        "invalid",
    )
    unstoppable = normalize_unstoppable_options(
        "invalid",
    )
    external = normalize_external_copymove_options(
        "invalid",
    )

    assert robocopy == RobocopyBackendOptions()
    assert teracopy == TeraCopyBackendOptions()
    assert unstoppable == UnstoppableBackendOptions()
    assert external == ExternalCopyMoveBackendOptions()


def test_mapping_payloads_are_supported_and_empty_external_tokens_reset() -> None:
    options = normalize_external_copymove_options(
        UserDict[str, object](
            {
                "include_operation_token": False,
                "include_sources": False,
                "include_target": False,
                "extra_args": " --fast ",
            }
        )
    )

    assert options.include_operation_token is True
    assert options.include_sources is True
    assert options.include_target is True
    assert options.extra_args == "--fast"


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
    assert "-o" in unstoppable
    assert "+s" in unstoppable
    assert "+a" not in unstoppable
    assert "+o" not in unstoppable
    assert "+t" not in unstoppable
    assert "-d" not in unstoppable
    assert external == "{sources} --fast"


def test_unstoppable_generator_groups_switches_and_omits_defaults() -> None:
    unstoppable = generate_unstoppable_args_template(
        UnstoppableBackendOptions(
            use_defaults=False,
            keep_owner=False,
            skip_damaged=True,
            power_down_when_done=True,
            extra_args="+x",
        )
    )

    assert unstoppable == "+ps -o +x"
