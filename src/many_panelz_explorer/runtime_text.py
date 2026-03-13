"""Helpers for runtime-generated text files with centralized newline policy."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

_UTF8_RUNTIME_SUFFIXES = frozenset({".txt", ".cmd", ".bat", ".ps1"})

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def runtime_text_linesep() -> str:
    """Return the centralized native line separator for runtime text files."""

    return os.linesep


def runtime_text_encoding(path: Path) -> str:
    """Resolve the runtime text encoding for the given output path."""

    suffix = path.suffix.casefold()
    if suffix == ".ucb":
        return "utf-16"
    if suffix in _UTF8_RUNTIME_SUFFIXES:
        return "utf-8"
    return "utf-8"


def write_runtime_text(path: Path, text: str) -> Path:
    """Write runtime text using centralized encoding and newline normalization."""

    normalized = _normalize_runtime_text(str(text))
    return _write_runtime_payload(path, normalized)


def write_runtime_lines(
    path: Path,
    lines: Iterable[str],
    *,
    trailing_newline: bool = False,
) -> Path:
    """Write logical lines using the centralized runtime line separator."""

    line_separator = runtime_text_linesep()
    text = line_separator.join(str(line) for line in lines)
    if trailing_newline and text:
        text = f"{text}{line_separator}"
    return _write_runtime_payload(path, text)


def _normalize_runtime_text(text: str) -> str:
    """Normalize mixed newline text into the centralized runtime separator."""

    if not text:
        return ""
    line_separator = runtime_text_linesep()
    normalized = line_separator.join(text.splitlines())
    if _has_trailing_linebreak(text):
        return f"{normalized}{line_separator}"
    return normalized


def _has_trailing_linebreak(text: str) -> bool:
    """Return whether the provided text ends with a line break."""

    return bool(text) and text[-1] in "\r\n"


def _write_runtime_payload(path: Path, text: str) -> Path:
    """Write an already-normalized runtime text payload to disk."""

    path.write_text(
        text,
        encoding=runtime_text_encoding(path),
        newline="",
    )
    return path
