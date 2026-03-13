"""Window-level coordinators used by ExplorerWindow."""

from .actions import WindowUiComposer
from .layout import WindowLayoutCoordinator
from .operations import WindowOperationsCoordinator
from .panels import WindowPanelsCoordinator
from .persistence import WindowPersistenceCoordinator
from .preferences import WindowPreferencesCoordinator
from .status import WindowStatusCoordinator
from .views import WindowViewsCoordinator

__all__ = [
    "WindowLayoutCoordinator",
    "WindowOperationsCoordinator",
    "WindowPanelsCoordinator",
    "WindowPersistenceCoordinator",
    "WindowPreferencesCoordinator",
    "WindowStatusCoordinator",
    "WindowUiComposer",
    "WindowViewsCoordinator",
]
