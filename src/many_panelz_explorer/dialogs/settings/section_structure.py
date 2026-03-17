"""Shared section tree and row builders for the settings dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .section_models import RowEntry, SectionEntry, SubsectionEntry

if TYPE_CHECKING:
    from ..settings_dialog import SettingsDialog


def build_sections(dialog: SettingsDialog) -> None:
    """Build all settings sections, subsections, and rows."""

    from . import section_appearance_panels, section_operations_general

    build_top_level_sections(dialog)
    appearance_panel_tint_group, appearance_typography_group = (
        build_appearance_subsections(dialog)
    )
    behavior_context_defaults_group, behavior_scan_limits_group = (
        build_behavior_subsections(dialog)
    )
    (
        panels_visibility_group,
        panels_file_list_layout_group,
        panels_byte_display_group,
    ) = build_panels_subsections(dialog)
    (
        operations_defaults_queue_group,
        operations_open_tools_group,
        operations_terminal_tools_group,
        operations_backend_commands_group,
        operations_backend_args_group,
        operations_diagnostics_group,
    ) = build_operations_subsections(dialog)
    about_application_info_group = build_about_subsections(dialog)

    section_appearance_panels.build_appearance_rows(
        dialog,
        panel_tint_group=appearance_panel_tint_group,
        typography_group=appearance_typography_group,
    )
    section_appearance_panels.build_behavior_rows(
        dialog,
        context_defaults_group=behavior_context_defaults_group,
        scan_limits_group=behavior_scan_limits_group,
    )
    section_appearance_panels.build_panels_rows(
        dialog,
        visibility_group=panels_visibility_group,
        file_list_layout_group=panels_file_list_layout_group,
        byte_display_group=panels_byte_display_group,
    )
    section_operations_general.build_operations_rows(
        dialog,
        defaults_queue_group=operations_defaults_queue_group,
        open_tools_group=operations_open_tools_group,
        terminal_tools_group=operations_terminal_tools_group,
        backend_commands_group=operations_backend_commands_group,
        backend_args_group=operations_backend_args_group,
        diagnostics_group=operations_diagnostics_group,
    )
    section_operations_general.build_about_rows(
        dialog,
        application_info_group=about_application_info_group,
    )
    expand_all_section_items(dialog)
    dialog.scroll_layout.addStretch(1)


def build_top_level_sections(dialog: SettingsDialog) -> None:
    """Create the top-level sections shown in the settings tree."""

    add_section(dialog, key="appearance", title="Appearance", terms="appearance")
    add_section(dialog, key="behavior", title="Behavior", terms="behavior")
    add_section(dialog, key="panels", title="Panels", terms="panels")
    add_section(
        dialog,
        key="operations",
        title="Operations",
        terms="operations copy move delete queue backend",
    )
    add_section(dialog, key="about", title="About", terms="about")


def build_appearance_subsections(
    dialog: SettingsDialog,
) -> tuple[SubsectionEntry, SubsectionEntry]:
    """Create the appearance-related subsection groups."""

    appearance_panel_tint_group = add_subsection(
        dialog,
        section_key="appearance",
        key="appearance/panel_tint",
        title="Panel Tint",
        terms="panel tint color intensity opacity active target",
    )
    appearance_typography_group = add_subsection(
        dialog,
        section_key="appearance",
        key="appearance/typography",
        title="Typography",
        terms="font typography app file list navigation",
    )
    return appearance_panel_tint_group, appearance_typography_group


def build_behavior_subsections(
    dialog: SettingsDialog,
) -> tuple[SubsectionEntry, SubsectionEntry]:
    """Create the behavior-related subsection groups."""

    behavior_context_defaults_group = add_subsection(
        dialog,
        section_key="behavior",
        key="behavior/context_defaults",
        title="Context Defaults",
        terms="context defaults new mode home cwd clone active path",
    )
    behavior_scan_limits_group = add_subsection(
        dialog,
        section_key="behavior",
        key="behavior/scan_limits",
        title="Scan Limits",
        terms="scan limits context detection child cap",
    )
    return behavior_context_defaults_group, behavior_scan_limits_group


def build_panels_subsections(
    dialog: SettingsDialog,
) -> tuple[SubsectionEntry, SubsectionEntry, SubsectionEntry]:
    """Create the panel-related subsection groups."""

    panels_visibility_group = add_subsection(
        dialog,
        section_key="panels",
        key="panels/visibility",
        title="Visibility",
        terms=(
            "visibility show hide controls root dropdown buttons address "
            "navigation status"
        ),
    )
    panels_file_list_layout_group = add_subsection(
        dialog,
        section_key="panels",
        key="panels/file_list_layout",
        title="File List Layout",
        terms="file list layout column width align auto",
    )
    panels_byte_display_group = add_subsection(
        dialog,
        section_key="panels",
        key="panels/byte_display",
        title="Byte Display",
        terms="bytes byte format separators file list status bar properties",
    )
    return (
        panels_visibility_group,
        panels_file_list_layout_group,
        panels_byte_display_group,
    )


def build_operations_subsections(
    dialog: SettingsDialog,
) -> tuple[
    SubsectionEntry,
    SubsectionEntry,
    SubsectionEntry,
    SubsectionEntry,
    SubsectionEntry,
    SubsectionEntry,
]:
    """Create the operations-related subsection groups."""

    operations_defaults_queue_group = add_subsection(
        dialog,
        section_key="operations",
        key="operations/defaults_queue",
        title="Defaults and Queue",
        terms="defaults queue backend dispatch conflict shortcut behavior",
    )
    operations_open_tools_group = add_subsection(
        dialog,
        section_key="operations",
        key="operations/open_tools",
        title="Open Tools",
        terms="open tools editor viewer context extension overrides code git",
    )
    operations_terminal_tools_group = add_subsection(
        dialog,
        section_key="operations",
        key="operations/terminal_tools",
        title="Terminal Tools",
        terms=(
            "terminal tools command prompt comspec pwsh powershell windows "
            "powershell 5 7 launcher shell"
        ),
    )
    operations_backend_commands_group = add_subsection(
        dialog,
        section_key="operations",
        key="operations/backend_commands",
        title="Backend Commands",
        terms="backend commands executable teracopy unstoppable generic rimraf",
    )
    operations_backend_args_group = add_subsection(
        dialog,
        section_key="operations",
        key="operations/backend_args",
        title="Backend Args",
        terms="backend args robocopy delete shell cmd powershell",
    )
    operations_diagnostics_group = add_subsection(
        dialog,
        section_key="operations",
        key="operations/diagnostics",
        title="Diagnostics",
        terms="diagnostics resolved system commands path cmd robocopy",
    )
    return (
        operations_defaults_queue_group,
        operations_open_tools_group,
        operations_terminal_tools_group,
        operations_backend_commands_group,
        operations_backend_args_group,
        operations_diagnostics_group,
    )


def build_about_subsections(dialog: SettingsDialog) -> SubsectionEntry:
    """Create the about subsection group."""

    return add_subsection(
        dialog,
        section_key="about",
        key="about/application_info",
        title="Application Info",
        terms="application info about version settings file path",
    )


def expand_all_section_items(dialog: SettingsDialog) -> None:
    """Expand all tree items after section construction completes."""

    for item in dialog.section_tree_items.values():
        item.setExpanded(True)


def add_section(
    dialog: SettingsDialog,
    *,
    key: str,
    title: str,
    terms: str,
) -> SectionEntry:
    """Add one top-level section to the tree and registry."""

    entry = SectionEntry(
        key=key,
        title=title,
        terms=terms.casefold(),
        subsection_keys=[],
    )
    dialog.sections[key] = entry
    item = QTreeWidgetItem([title])
    item.setData(0, Qt.ItemDataRole.UserRole, ("section", key))
    dialog.section_tree.addTopLevelItem(item)
    dialog.section_tree_items[key] = item
    return entry


def add_subsection(
    dialog: SettingsDialog,
    *,
    section_key: str,
    key: str,
    title: str,
    terms: str,
) -> SubsectionEntry:
    """Add one subsection group to the tree and scroll area."""

    section = dialog.sections.get(section_key)
    if section is None:
        raise KeyError(f"Unknown section key: {section_key}")
    section.subsection_keys.append(key)

    group = QGroupBox(title, dialog.scroll_host)
    group_layout = QVBoxLayout(group)
    group_layout.setContentsMargins(10, 12, 10, 10)
    group_layout.setSpacing(8)
    group.setVisible(False)
    dialog.scroll_layout.addWidget(group)
    entry = SubsectionEntry(
        key=key,
        section_key=section_key,
        title=title,
        group=group,
        terms=terms.casefold(),
        rows=[],
    )
    dialog.subsections[key] = entry

    section_item = dialog.section_tree_items.get(section_key)
    if section_item is None:
        raise KeyError(f"Unknown section tree item: {section_key}")
    item = QTreeWidgetItem([title])
    item.setData(0, Qt.ItemDataRole.UserRole, ("subsection", key))
    section_item.addChild(item)
    dialog.subsection_tree_items[key] = item
    identity_key = key.replace("/", ":")
    dialog.assign_identity(
        group,
        f"settings_dialog:subsection:{identity_key}",
        f"settings.subsection.{identity_key}",
    )
    return entry


def add_row(
    dialog: SettingsDialog,
    *,
    section: SubsectionEntry,
    key: str,
    title: str,
    description: str,
    terms: str,
    controls: list[QWidget],
) -> None:
    """Add one searchable row to a subsection group."""

    row = QWidget(section.group)
    row_layout = QVBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(4)

    title_label = QLabel(title, row)
    title_label.setStyleSheet("font-weight: 600;")
    title_label.setWordWrap(True)
    row_layout.addWidget(title_label)

    description_label = QLabel(description, row)
    description_label.setWordWrap(True)
    row_layout.addWidget(description_label)

    controls_host = QWidget(row)
    controls_layout = QHBoxLayout(controls_host)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(8)
    for control in controls:
        if isinstance(control, QLineEdit):
            control.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
        controls_layout.addWidget(control)
    controls_host.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )
    row_layout.addWidget(controls_host)

    group_layout = section.group.layout()
    if group_layout is None:
        raise RuntimeError("Settings section group is missing its layout.")
    group_layout.addWidget(row)

    entry = RowEntry(
        key=key,
        widget=row,
        terms=f"{title} {description} {terms}".casefold(),
    )
    section.rows.append(entry)
    dialog.row_widgets_by_key[key] = row
    dialog.row_subsection_keys[key] = section.key
    dialog.assign_identity(row, f"settings_dialog:row:{key}", f"settings.row.{key}")
