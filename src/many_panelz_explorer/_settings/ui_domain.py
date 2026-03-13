"""Composite UI settings domain."""

from __future__ import annotations

from .ui_domain_appearance import UiAppearanceSettingsMixin
from .ui_domain_behavior import UiBehaviorSettingsMixin
from .ui_domain_bytes import UiByteFormatSettingsMixin


class UiSettingsDomain(
    UiBehaviorSettingsMixin,
    UiByteFormatSettingsMixin,
    UiAppearanceSettingsMixin,
):
    """Read and persist user-interface preferences."""

    pass
