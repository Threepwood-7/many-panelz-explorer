from __future__ import annotations

from pathlib import Path

from many_panelz_explorer import mounts
from many_panelz_explorer.storage_status_formatting import (
    DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE,
    format_storage_usage_entry,
)


def _entry(*, used: int, total: int, ratio: float = 0.0) -> mounts.StorageUsageEntry:
    return mounts.StorageUsageEntry(
        root_path=Path("C:\\"),
        display_root="C:",
        volume_label="System",
        bytes_used=used,
        bytes_total=total,
        usage_ratio=ratio,
    )


def test_storage_label_template_renders_supported_placeholders() -> None:
    rendered = format_storage_usage_entry(
        _entry(used=600, total=1_000),
        bytes_formatter=lambda value: f"{value} B",
        label_template=(
            "{disk_root} {disk_label} {used_space}/{total_space} "
            "{usage_percentage:.0f}% {usage_indicator}"
        ),
    )
    assert rendered.label_text == (
        "C: System 600 B/1000 B 60% "
        "\u2588\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591"
    )


def test_storage_label_template_supports_numeric_format_specs() -> None:
    rendered = format_storage_usage_entry(
        _entry(used=1_536, total=4_096),
        bytes_formatter=lambda value: f"{value} B",
        label_template="{usage_percentage:.1f}% {usage_ratio:.2f} {used_bytes:,}",
    )
    assert rendered.label_text == "37.5% 0.38 1,536"


def test_storage_label_template_invalid_input_falls_back_to_default() -> None:
    rendered = format_storage_usage_entry(
        _entry(used=1_536, total=4_096),
        bytes_formatter=lambda value: f"{value} B",
        label_template="{unknown_field}",
    )
    assert rendered.label_text == "C: System 1536 B/4096 B"
    assert DEFAULT_STORAGE_STATUS_LABEL_TEMPLATE.startswith("{disk_root}")


def test_storage_tooltip_contains_full_metrics_and_indicators() -> None:
    rendered = format_storage_usage_entry(
        _entry(used=1_500_000, total=3_000_000),
        bytes_formatter=lambda value: f"{value} B",
        label_template="{disk_root}",
    )
    tooltip = rendered.tooltip_html
    assert "<b>C: System</b>" in tooltip
    assert "Used:" in tooltip and "1500000 B" in tooltip
    assert "Free:" in tooltip and "1500000 B" in tooltip
    assert "Total:" in tooltip and "3000000 B" in tooltip
    assert "Usage:" in tooltip and "50.00%" in tooltip
    assert "Free:" in tooltip and "50.00%" in tooltip
    assert (
        "Usage bar:" in tooltip
        and "\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591" in tooltip
    )
    assert (
        "Free bar:" in tooltip
        and "\u2588\u2588\u2588\u2588\u2588\u2591\u2591\u2591\u2591\u2591" in tooltip
    )
