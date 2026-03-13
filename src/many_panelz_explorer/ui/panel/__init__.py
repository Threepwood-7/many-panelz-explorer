"""Panel-level coordinators used by PanelWidget."""

from .chrome import (
    assign_panel_control_identities,
    build_panel_filter,
    build_panel_tabs,
    build_panel_toolbar,
    configure_panel_shortcuts_and_timers,
    finalize_panel_ui,
    install_panel_focus_watchers,
)
from .filter_overlay import PanelInlineFilterCoordinator
from .navigation import PanelNavigationCoordinator
from .presentation import PanelPresentationCoordinator
from .state import PanelStateCoordinator
from .widget_map import PanelWidgetMapCoordinator

__all__ = [
    "PanelInlineFilterCoordinator",
    "PanelNavigationCoordinator",
    "PanelPresentationCoordinator",
    "PanelStateCoordinator",
    "PanelWidgetMapCoordinator",
    "assign_panel_control_identities",
    "build_panel_filter",
    "build_panel_tabs",
    "build_panel_toolbar",
    "configure_panel_shortcuts_and_timers",
    "finalize_panel_ui",
    "install_panel_focus_watchers",
]
