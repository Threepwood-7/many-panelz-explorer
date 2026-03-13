"""Serializable binary split-tree model for panel layout state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

# Match Qt.Orientation numeric values without importing Qt in this pure model module.
ORIENTATION_HORIZONTAL = 1
ORIENTATION_VERTICAL = 2


@dataclass(slots=True)
class LeafNode:
    """Leaf node representing a single panel identifier."""

    panel_id: int


@dataclass(slots=True)
class SplitNode:
    """Split node representing two child branches and their ratio."""

    orientation: int
    ratio: float
    left: Node
    right: Node


Node = LeafNode | SplitNode


class RemoveLeafResult(TypedDict):
    """Structured result returned after removing a panel leaf."""

    removed: bool
    removed_last: bool
    remaining_panels: int
    remaining_panel_ids: list[int]


def _normalize_orientation(orientation: int | str) -> int:
    if isinstance(orientation, str):
        lowered = orientation.strip().lower()
        if lowered in {"horizontal", "h", "left-right", "left_right"}:
            return ORIENTATION_HORIZONTAL
        if lowered in {"vertical", "v", "top-bottom", "top_bottom"}:
            return ORIENTATION_VERTICAL
        raise ValueError(f"Unsupported orientation string: {orientation!r}")

    if int(orientation) in {ORIENTATION_HORIZONTAL, ORIENTATION_VERTICAL}:
        return int(orientation)
    raise ValueError(f"Unsupported orientation value: {orientation!r}")


def _orientation_name(orientation: int) -> str:
    normalized = _normalize_orientation(orientation)
    return "horizontal" if normalized == ORIENTATION_HORIZONTAL else "vertical"


class PanelTreeModel:
    """Serializable binary split tree used by the window layout."""

    def __init__(self, root: Node | None = None) -> None:
        self.root: Node | None = root if root is not None else LeafNode(panel_id=1)
        self._next_panel_id = self._compute_next_panel_id()

    def _compute_next_panel_id(self) -> int:
        leaf_ids = self.leaf_ids()
        return (max(leaf_ids) + 1) if leaf_ids else 1

    def leaf_ids(self) -> list[int]:
        ids: list[int] = []

        def visit(node: Node | None) -> None:
            if node is None:
                return
            if isinstance(node, LeafNode):
                ids.append(node.panel_id)
                return
            visit(node.left)
            visit(node.right)

        visit(self.root)
        return ids

    def split_leaf(self, panel_id: int, orientation: int | str) -> int:
        normalized = _normalize_orientation(orientation)
        new_panel_id = self._next_panel_id

        def visit(node: Node | None) -> tuple[Node | None, bool]:
            nonlocal new_panel_id
            if node is None:
                return None, False
            if isinstance(node, LeafNode):
                if node.panel_id != panel_id:
                    return node, False
                self._next_panel_id += 1
                split = SplitNode(
                    orientation=normalized,
                    ratio=0.5,
                    left=LeafNode(panel_id=node.panel_id),
                    right=LeafNode(panel_id=new_panel_id),
                )
                return split, True

            left, changed_left = visit(node.left)
            if changed_left:
                node.left = left if left is not None else node.left
                return node, True

            right, changed_right = visit(node.right)
            if changed_right:
                node.right = right if right is not None else node.right
                return node, True

            return node, False

        self.root, changed = visit(self.root)
        if not changed:
            raise KeyError(f"Panel {panel_id} does not exist")
        return new_panel_id

    def remove_leaf(self, panel_id: int) -> RemoveLeafResult:
        def visit(node: Node | None) -> tuple[Node | None, bool]:
            if node is None:
                return None, False
            if isinstance(node, LeafNode):
                if node.panel_id == panel_id:
                    return None, True
                return node, False

            left, removed_left = visit(node.left)
            right, removed_right = visit(node.right)
            removed = removed_left or removed_right
            if not removed:
                return node, False

            if left is None and right is None:
                return None, True
            if left is None:
                return right, True
            if right is None:
                return left, True

            node.left = left
            node.right = right
            return node, True

        self.root, removed = visit(self.root)
        remaining = self.leaf_ids()
        self._next_panel_id = self._compute_next_panel_id()
        return {
            "removed": removed,
            "removed_last": removed and not remaining,
            "remaining_panels": len(remaining),
            "remaining_panel_ids": remaining,
        }

    def to_dict(self) -> dict[str, Any]:
        def encode(node: Node | None) -> dict[str, Any] | None:
            if node is None:
                return None
            if isinstance(node, LeafNode):
                return {"type": "leaf", "panel_id": node.panel_id}
            return {
                "type": "split",
                "orientation": _orientation_name(node.orientation),
                "ratio": node.ratio,
                "left": encode(node.left),
                "right": encode(node.right),
            }

        return {"root": encode(self.root)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PanelTreeModel:
        def decode(node_data: dict[str, Any] | None) -> Node | None:
            if node_data is None:
                return None

            node_type = node_data.get("type")
            if node_type == "leaf":
                panel_id = int(node_data["panel_id"])
                return LeafNode(panel_id=panel_id)

            if node_type == "split":
                orientation = _normalize_orientation(node_data["orientation"])
                ratio = float(node_data.get("ratio", 0.5))
                left = decode(node_data.get("left"))
                right = decode(node_data.get("right"))
                if left is None or right is None:
                    raise ValueError("Split node requires both left and right children")
                return SplitNode(
                    orientation=orientation, ratio=ratio, left=left, right=right
                )

            raise ValueError(f"Unsupported node type: {node_type!r}")

        root = decode(data.get("root"))
        model = cls(root=root)
        model._next_panel_id = model._compute_next_panel_id()
        return model
