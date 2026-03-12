from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtWidgets import QApplication

from ._operations.queue_manager import OperationQueueManager
from ._operations.types import OperationExecutionPreferences
from ._settings.manager import SettingsManager
from .operation_queue_widgets import OperationQueueTableModel
from .window import ExplorerWindow

if TYPE_CHECKING:
    from .app_controller import AppController


class _ControllerStub:
    def __init__(self) -> None:
        self.operation_queue_manager = OperationQueueManager(
            preferences=OperationExecutionPreferences()
        )
        self.operation_queue_model = OperationQueueTableModel(
            self.operation_queue_manager
        )

    def close_window(self, _window: ExplorerWindow) -> None:
        return

    def show_queue_floating_window(self) -> None:
        return None

    def broadcast_column_widths(self, *_args: object, **_kwargs: object) -> None:
        return


def _pump_events(app: QApplication, seconds: float) -> None:
    deadline = time.perf_counter() + max(0.0, float(seconds))
    while time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()


def generate_widget_map_image(
    output_path: Path,
    *,
    source_root: Path | None = None,
    size: tuple[int, int] = (1280, 760),
) -> Path:
    app_instance = QApplication.instance()
    owns_app = app_instance is None
    app = (
        cast("QApplication", app_instance)
        if app_instance is not None
        else QApplication([])
    )

    try:
        roots_dir = Path(source_root) if source_root is not None else Path.cwd()
        if not roots_dir.exists() or not roots_dir.is_dir():
            roots_dir = Path.home()

        settings = SettingsManager()
        window = ExplorerWindow(
            controller=cast("AppController", _ControllerStub()),
            settings=settings,
            window_id="widget-map-snapshot",
            initial_path=roots_dir,
            roots_provider=lambda _current: [roots_dir],
        )
        window.resize(*size)
        window.show()
        _pump_events(app, 0.2)

        panel = window.active_panel()
        if panel is None:
            raise RuntimeError("No active panel available for snapshot generation.")
        tab = panel.current_tab()
        if tab is None:
            raise RuntimeError("No active tab available for snapshot generation.")

        panel.show_filter_overlay(seed_text="map")
        window.toggle_show_widget_map(True)
        _pump_events(app, 0.2)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(output)):
            raise RuntimeError(f"Could not save snapshot to {output}.")

        window.close()
        _pump_events(app, 0.05)
        return output
    finally:
        if owns_app:
            app.quit()


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    output = Path(args[0]) if args else Path("docs") / "images" / "ui-04-widget-map.png"
    source_root = Path(args[1]) if len(args) > 1 else Path.cwd()
    try:
        generated = generate_widget_map_image(output, source_root=source_root)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Widget map image generated at: {generated}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    raise SystemExit(main())
