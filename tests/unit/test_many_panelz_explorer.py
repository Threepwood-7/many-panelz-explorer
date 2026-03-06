"""Tests for many_panelz_explorer."""

import importlib


def test_package_importable() -> None:
    assert importlib.import_module("many_panelz_explorer")
