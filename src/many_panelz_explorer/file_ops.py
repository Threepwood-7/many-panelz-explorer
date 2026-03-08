from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from send2trash import send2trash

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class ClipboardPayload:
    paths: list[Path]
    cut: bool


_clipboard_payload: ClipboardPayload | None = None
_default_editor_executable = ""
_default_viewer_executable = ""
_file_open_overrides: dict[str, dict[str, str]] = {}


def set_clipboard(paths: Iterable[Path], cut: bool) -> None:
    global _clipboard_payload
    _clipboard_payload = ClipboardPayload(paths=[Path(p) for p in paths], cut=cut)


def get_clipboard() -> ClipboardPayload | None:
    return _clipboard_payload


def clear_clipboard() -> None:
    global _clipboard_payload
    _clipboard_payload = None


def _safe_target(destination: Path, source_name: str) -> Path:
    candidate = destination / source_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    idx = 1
    while True:
        new_name = f"{stem} ({idx}){suffix}"
        candidate = destination / new_name
        if not candidate.exists():
            return candidate
        idx += 1


def _normalize_extension(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if not text.startswith("."):
        text = f".{text}"
    return text


def _normalize_overrides_payload(raw: object) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for ext, value in raw.items():
        ext_key = _normalize_extension(str(ext))
        if not ext_key:
            continue
        if isinstance(value, dict):
            editor = str(value.get("editor", "")).strip()
            viewer = str(value.get("viewer", "")).strip()
        else:
            editor = ""
            viewer = ""
        normalized[ext_key] = {"editor": editor, "viewer": viewer}
    return normalized


def configure_open_routing(
    *,
    default_editor_executable: str,
    default_viewer_executable: str,
    overrides_json: str,
) -> None:
    global _default_editor_executable
    global _default_viewer_executable
    global _file_open_overrides
    _default_editor_executable = str(default_editor_executable or "").strip()
    _default_viewer_executable = str(default_viewer_executable or "").strip()
    try:
        parsed = json.loads(str(overrides_json or "{}"))
    except json.JSONDecodeError:
        parsed = {}
    _file_open_overrides = _normalize_overrides_payload(parsed)


def _resolve_launch_executable(executable: str) -> str:
    text = str(executable or "").strip()
    if not text:
        return ""
    candidate = Path(text)
    if candidate.is_absolute() or ("\\" in text or "/" in text):
        if candidate.exists():
            return str(candidate)
        raise RuntimeError(f"Configured executable does not exist: {text}")
    which_hit = shutil.which(text)
    if which_hit:
        return str(Path(which_hit))
    raise RuntimeError(f"Configured executable is unavailable: {text}")


def resolve_open_executable(path: Path, mode: Literal["edit", "view"]) -> str | None:
    extension = _normalize_extension(Path(path).suffix)
    override = _file_open_overrides.get(extension, {})
    if mode == "edit":
        candidate = str(override.get("editor", "") or _default_editor_executable).strip()
    else:
        candidate = str(
            override.get("viewer", "")
            or _default_viewer_executable
            or _default_editor_executable
        ).strip()
    if not candidate:
        return None
    return _resolve_launch_executable(candidate)


def _launch_file_with_executable(executable: str, path: Path) -> None:
    subprocess.Popen([str(executable), str(path)])


def open_with_default(path: Path) -> None:
    path = Path(path)
    configured = resolve_open_executable(path, "view")
    if configured:
        _launch_file_with_executable(configured, path)
        return

    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return

    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", str(path)])
        return

    if shutil.which("open"):
        subprocess.Popen(["open", str(path)])
        return

    raise RuntimeError("No default opener available on this platform")


def _resolve_text_editor_executable_fallback() -> str:
    if os.name == "nt":
        windir = Path(str(os.environ.get("WINDIR") or r"C:\Windows"))
        notepad = windir / "System32" / "notepad.exe"
        if notepad.exists():
            return str(notepad)
        discovered = shutil.which("notepad.exe")
        if discovered:
            return str(Path(discovered))
        raise RuntimeError("No text editor available. Configure one in Settings.")

    discovered = shutil.which("xdg-open") or shutil.which("open")
    if discovered:
        return str(Path(discovered))
    raise RuntimeError("No text editor available. Configure one in Settings.")


def open_in_text_editor(path: Path, editor_executable: str = "") -> None:
    path = Path(path)
    configured = str(editor_executable or "").strip()
    if configured:
        editor = _resolve_launch_executable(configured)
    else:
        editor = resolve_open_executable(path, "edit")
        if not editor:
            editor = _resolve_text_editor_executable_fallback()
    try:
        _launch_file_with_executable(editor, path)
    except OSError as exc:
        raise RuntimeError(f"Could not open text editor: {exc}") from exc


def rename_path(path: Path, new_name: str) -> Path:
    path = Path(path)
    target = path.with_name(new_name)
    return path.rename(target)


def create_folder(parent: Path, name: str = "New Folder") -> Path:
    parent = Path(parent)
    target = _safe_target(parent, name)
    target.mkdir(parents=False, exist_ok=False)
    return target


def copy_items(paths: Iterable[Path], destination: Path) -> list[Path]:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []

    for src in [Path(p) for p in paths]:
        target = _safe_target(destination, src.name)
        if src.is_dir():
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)
        copied.append(target)

    return copied


def move_items(paths: Iterable[Path], destination: Path) -> list[Path]:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    moved: list[Path] = []

    for src in [Path(p) for p in paths]:
        target = _safe_target(destination, src.name)
        moved.append(Path(shutil.move(str(src), str(target))))

    return moved


def paste_items(destination: Path) -> list[Path]:
    payload = get_clipboard()
    if payload is None:
        return []

    if payload.cut:
        moved = move_items(payload.paths, destination)
        clear_clipboard()
        return moved

    return copy_items(payload.paths, destination)


def delete_to_recycle_bin(paths: Iterable[Path]) -> None:
    for path in paths:
        send2trash(str(Path(path)))


def zip_create(sources: Iterable[Path], archive_path: Path) -> Path:
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source in [Path(p) for p in sources]:
            if source.is_dir():
                for entry in source.rglob("*"):
                    if entry.is_file():
                        zf.write(entry, arcname=str(entry.relative_to(source.parent)))
            elif source.exists():
                zf.write(source, arcname=source.name)

    return archive_path


def zip_extract(archive_path: Path, destination: Path) -> Path:
    archive_path = Path(archive_path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(destination)
    return destination


def open_terminal_here(path: Path) -> None:
    path = Path(path)
    if os.name == "nt":
        subprocess.Popen(
            ["powershell", "-NoExit", "-Command", "Set-Location", str(path)]
        )
        return
    if shutil.which("x-terminal-emulator"):
        subprocess.Popen(["x-terminal-emulator", "--working-directory", str(path)])
        return
    raise RuntimeError("No terminal launcher configured for this platform")


def compute_properties(path: Path) -> dict[str, str]:
    path = Path(path)
    size = 0
    file_count = 0

    if path.is_file():
        size = path.stat().st_size
        file_count = 1
    elif path.is_dir():
        for entry in path.rglob("*"):
            if entry.is_file():
                size += entry.stat().st_size
                file_count += 1

    return {
        "path": str(path),
        "type": "Folder" if path.is_dir() else "File",
        "size_bytes": str(size),
        "file_count": str(file_count),
    }
