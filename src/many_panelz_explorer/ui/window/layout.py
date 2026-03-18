"""Layout state helpers for translating between rows and panel trees."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...panel_tab_positions import TAB_POSITION_MODE_DEFAULT
from ...panel_tree import (
    ORIENTATION_HORIZONTAL,
    ORIENTATION_VERTICAL,
    LeafNode,
    PanelTreeModel,
    SplitNode,
)

if TYPE_CHECKING:
    from ...window import ExplorerWindow
    from .state_types import PanelRows, PanelState, TabsState


class WindowLayoutCoordinator:
    """Build and normalize panel layout state for an explorer window."""

    def __init__(self, window: ExplorerWindow) -> None:
        self.window = window

    def new_panel_state(self, panel_id: int, seed_path: Path) -> PanelState:
        return {
            "panel_id": panel_id,
            "current_index": 0,
            "tabs": [{"path": str(seed_path)}],
            "tab_position_mode": TAB_POSITION_MODE_DEFAULT,
        }

    def default_panel_state(self, panel_id: int) -> PanelState:
        panel = self.window.panel_widgets.get(panel_id)
        path = panel.current_path() if panel is not None else Path.home()
        return self.new_panel_state(panel_id, path)

    def find_panel_position(
        self, panel_id: int, rows: PanelRows
    ) -> tuple[int | None, int | None]:
        for row_index, row in enumerate(rows):
            for col_index, row_panel_id in enumerate(row):
                if row_panel_id == panel_id:
                    return row_index, col_index
        return None, None

    def allocate_panel_id(self, rows: PanelRows, tabs_state: TabsState) -> int:
        ids = set(self.ordered_panel_ids(rows)) | set(tabs_state.keys())
        return (max(ids) + 1) if ids else 1

    @staticmethod
    def default_startup_rows() -> PanelRows:
        """Return the default row layout used for fresh windows."""

        return [[1, 2]]

    def default_startup_tree(self) -> PanelTreeModel:
        """Return the default panel tree used for fresh windows."""

        root = self.build_tree_root_from_rows(self.default_startup_rows())
        return PanelTreeModel(root=root)

    @staticmethod
    def ordered_panel_ids(rows: PanelRows) -> list[int]:
        ordered: list[int] = []
        for row in rows:
            ordered.extend(row)
        return ordered

    def normalize_rows(self, rows: PanelRows) -> PanelRows:
        normalized: PanelRows = []
        seen: set[int] = set()
        for row in rows:
            cleaned_row: list[int] = []
            for panel_id in row:
                panel_id_int = int(panel_id)
                if panel_id_int in seen:
                    continue
                cleaned_row.append(panel_id_int)
                seen.add(panel_id_int)
            if cleaned_row:
                normalized.append(cleaned_row)
        if not normalized:
            return [[1]]
        return normalized

    def append_missing_panel_ids(
        self, rows: PanelRows, panel_ids: list[int]
    ) -> PanelRows:
        normalized_rows = self.normalize_rows(rows)
        present = set(self.ordered_panel_ids(normalized_rows))
        missing = [
            int(panel_id) for panel_id in panel_ids if int(panel_id) not in present
        ]
        if missing:
            normalized_rows.append(missing)
        return self.normalize_rows(normalized_rows)

    def rows_from_tree(self, node: LeafNode | SplitNode | None) -> PanelRows:
        if node is None:
            return [[1]]

        def split_into_rows(
            tree_node: LeafNode | SplitNode,
        ) -> list[LeafNode | SplitNode]:
            if isinstance(tree_node, LeafNode):
                return [tree_node]
            if tree_node.orientation == ORIENTATION_VERTICAL:
                return split_into_rows(tree_node.left) + split_into_rows(
                    tree_node.right
                )
            return [tree_node]

        def flatten_row(tree_node: LeafNode | SplitNode) -> list[int]:
            if isinstance(tree_node, LeafNode):
                return [tree_node.panel_id]
            if tree_node.orientation != ORIENTATION_HORIZONTAL:
                raise ValueError("row contains vertical split")
            return flatten_row(tree_node.left) + flatten_row(tree_node.right)

        try:
            rows = [flatten_row(row_node) for row_node in split_into_rows(node)]
        except ValueError:
            rows = [self.window.panel_tree.leaf_ids()]
        return self.normalize_rows(rows)

    def sync_panel_tree_from_rows(self) -> None:
        self.window.layout_rows = self.normalize_rows(self.window.layout_rows)
        root = self.build_tree_root_from_rows(self.window.layout_rows)
        self.window.panel_tree = PanelTreeModel(
            root=root if root is not None else LeafNode(1)
        )

    def build_tree_root_from_rows(self, rows: PanelRows) -> LeafNode | SplitNode | None:
        if not rows:
            return None

        def build_row(row: list[int]) -> LeafNode | SplitNode:
            if len(row) == 1:
                return LeafNode(panel_id=row[0])
            return SplitNode(
                orientation=ORIENTATION_HORIZONTAL,
                ratio=1.0 / float(len(row)),
                left=LeafNode(panel_id=row[0]),
                right=build_row(row[1:]),
            )

        if len(rows) == 1:
            return build_row(rows[0])
        right = self.build_tree_root_from_rows(rows[1:])
        if right is None:
            return build_row(rows[0])
        return SplitNode(
            orientation=ORIENTATION_VERTICAL,
            ratio=1.0 / float(len(rows)),
            left=build_row(rows[0]),
            right=right,
        )
