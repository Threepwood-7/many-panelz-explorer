from many_panelz_explorer import widget_naming
from threep_commons.qt.widget_identity import object_name_for_id


def test_widget_id_contracts() -> None:
    assert widget_naming.window_widget_id("abc") == "window:abc"
    assert widget_naming.panel_widget_id(4) == "panel:4"
    assert (
        widget_naming.tab_widget_id(4, "abcd1234")
        == "panel:4:tab:abcd1234"
    )
    assert (
        widget_naming.file_list_widget_id(4, "abcd1234")
        == "panel:4:tab:abcd1234:file_list"
    )


def test_widget_alias_contracts() -> None:
    assert widget_naming.panel_alias(7) == "P7"
    assert widget_naming.tab_alias(7, "1234567890abcdef") == "P7.T12345678"
    assert (
        widget_naming.file_list_alias(7, "1234567890abcdef")
        == "P7.T12345678.file_list"
    )
    assert widget_naming.panel_control_alias(7, "address") == "P7.address"


def test_object_name_for_id_sanitizes_non_identifier_chars() -> None:
    widget_id = "panel:1:tab:abc123:file_list"
    assert object_name_for_id(widget_id) == "panel_1_tab_abc123_file_list"
