"""Composite operation settings domain."""

from __future__ import annotations

from .ops_domain_backends import OpsBackendSettingsMixin
from .ops_domain_defaults import OpsDefaultSettingsMixin


class OpsSettingsDomain(OpsDefaultSettingsMixin, OpsBackendSettingsMixin):
    """Read and persist operation backend and execution preferences."""

    pass
