from many_panelz_explorer.panel_tree import (
    ORIENTATION_HORIZONTAL,
    ORIENTATION_VERTICAL,
    PanelTreeModel,
)


def test_split_remove_tree_validity() -> None:
    model = PanelTreeModel()
    assert model.leaf_ids() == [1]

    panel2 = model.split_leaf(1, ORIENTATION_HORIZONTAL)
    panel3 = model.split_leaf(panel2, ORIENTATION_VERTICAL)

    assert sorted(model.leaf_ids()) == [1, panel2, panel3]

    removed = model.remove_leaf(panel2)
    assert removed["removed"] is True
    assert removed["remaining_panels"] == 2
    assert sorted(model.leaf_ids()) == [1, panel3]

    removed = model.remove_leaf(panel3)
    assert removed["removed"] is True
    assert removed["remaining_panels"] == 1
    assert model.leaf_ids() == [1]


def test_serialization_roundtrip() -> None:
    model = PanelTreeModel()
    panel2 = model.split_leaf(1, ORIENTATION_HORIZONTAL)
    panel3 = model.split_leaf(1, ORIENTATION_VERTICAL)
    _ = panel2, panel3

    payload = model.to_dict()
    restored = PanelTreeModel.from_dict(payload)

    assert payload == restored.to_dict()
    assert sorted(model.leaf_ids()) == sorted(restored.leaf_ids())
