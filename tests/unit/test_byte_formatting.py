from many_panelz_explorer.byte_formatting import (
    BYTE_FORMAT_MODE_ALWAYS_MB,
    BYTE_FORMAT_MODE_ALWAYS_MIB,
    BYTE_FORMAT_MODE_BYTES,
    BYTE_FORMAT_MODE_CUSTOM,
    BYTE_FORMAT_MODE_HUMAN_READABLE,
    ByteFormatScopeConfig,
    format_bytes,
)


def test_format_bytes_human_readable_binary_units() -> None:
    rendered = format_bytes(
        1_536,
        ByteFormatScopeConfig(mode=BYTE_FORMAT_MODE_HUMAN_READABLE),
    )
    assert rendered == "1.50 KiB"


def test_format_bytes_always_mb_and_always_mib() -> None:
    assert format_bytes(
        3_000_000,
        ByteFormatScopeConfig(mode=BYTE_FORMAT_MODE_ALWAYS_MB),
    ) == "3.00 MB"
    assert format_bytes(
        3_145_728,
        ByteFormatScopeConfig(mode=BYTE_FORMAT_MODE_ALWAYS_MIB),
    ) == "3.00 MiB"


def test_format_bytes_bytes_mode_respects_grouping_separator() -> None:
    rendered = format_bytes(
        1_234_567,
        ByteFormatScopeConfig(mode=BYTE_FORMAT_MODE_BYTES),
        separators=(".", ","),
    )
    assert rendered == "1.234.567"


def test_format_bytes_custom_template_localizes_output() -> None:
    rendered = format_bytes(
        3_500,
        ByteFormatScopeConfig(
            mode=BYTE_FORMAT_MODE_CUSTOM,
            custom_template="{b} ({KiB:.2f} KiB)",
        ),
        separators=(".", ","),
    )
    assert rendered == "3.500 (3,42 KiB)"


def test_format_bytes_custom_template_requires_fields_and_known_tokens() -> None:
    assert format_bytes(
        1234,
        ByteFormatScopeConfig(mode=BYTE_FORMAT_MODE_CUSTOM, custom_template="plain text"),
    ) == "1,234"
    assert format_bytes(
        1234,
        ByteFormatScopeConfig(
            mode=BYTE_FORMAT_MODE_CUSTOM, custom_template="{M:.2f} M"
        ),
    ) == "1,234"


def test_format_bytes_custom_template_never_evaluates_expressions() -> None:
    rendered = format_bytes(
        12_345,
        ByteFormatScopeConfig(
            mode=BYTE_FORMAT_MODE_CUSTOM,
            custom_template="{__import__('os').system('echo hi')}",
        ),
    )
    assert rendered == "12,345"


def test_format_bytes_clamps_negative_values_to_zero() -> None:
    assert format_bytes(
        -999,
        ByteFormatScopeConfig(mode=BYTE_FORMAT_MODE_BYTES),
    ) == "0"
