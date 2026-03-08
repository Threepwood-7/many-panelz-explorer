from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...window import ExplorerWindow


class WindowStatusCoordinator:
    def __init__(self, window: ExplorerWindow) -> None:
        self.window = window

    def update_pane_visuals(self) -> None:
        source_id = self.window._active_panel_id
        target_id = (
            self.window._resolve_target_panel_id(source_id) if source_id is not None else None
        )

        for panel_id, panel in self.window.panel_widgets.items():
            panel.set_role_visual_state(
                is_active=panel_id == source_id,
                is_target=panel_id == target_id,
            )
        self.set_persistent_path_status(source_id=source_id, target_id=target_id)

    def set_persistent_path_status(
        self, *, source_id: int | None, target_id: int | None
    ) -> None:
        source_path = self.panel_path_text(source_id)
        target_path = self.panel_path_text(target_id)

        self.window._source_path_label.setText(f"Source path: {source_path}")
        self.window._target_path_label.setText(f"Target path: {target_path}")

        self.window._source_path_label.setToolTip(
            "" if source_path == "(none)" else source_path
        )
        self.window._target_path_label.setToolTip(
            "" if target_path == "(none)" else target_path
        )

    def panel_path_text(self, panel_id: int | None) -> str:
        if panel_id is None:
            return "(none)"
        panel = self.window.panel_widgets.get(panel_id)
        if panel is None:
            return "(none)"
        return str(panel.current_path())

