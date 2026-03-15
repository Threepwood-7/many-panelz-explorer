from __future__ import annotations

from pathlib import Path

from many_panelz_explorer.external_file_managers import expand_external_manager_args


def test_expand_external_manager_args_keeps_paths_with_spaces_as_single_tokens() -> (
    None
):
    source = Path(r"C:\Work Dir\alpha.txt")
    target = Path(r"D:\Target Dir\beta.txt")

    args = expand_external_manager_args(
        "/N /L={source} /R={target}",
        source=source,
        target=target,
    )

    assert args == [
        "/N",
        rf"/L={source}",
        rf"/R={target}",
    ]


def test_expand_external_manager_args_supports_split_flag_style() -> None:
    source = Path(r"C:\Root Folder")

    args = expand_external_manager_args(
        "-C -L {source}",
        source=source,
        target=None,
    )

    assert args == ["-C", "-L", str(source)]
