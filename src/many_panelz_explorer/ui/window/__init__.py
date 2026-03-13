"""Window-level coordinators used by ExplorerWindow."""

from .actions import WindowUiComposer
from .layout import WindowLayoutCoordinator
from .operations import WindowOperationsCoordinator
from .panels import WindowPanelsCoordinator
from .persistence import WindowPersistenceCoordinator
from .status import WindowStatusCoordinator

__all__ = [
    "WindowLayoutCoordinator",
    "WindowOperationsCoordinator",
    "WindowPanelsCoordinator",
    "WindowPersistenceCoordinator",
    "WindowStatusCoordinator",
    "WindowUiComposer",
]
