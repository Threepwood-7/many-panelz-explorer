"""Navigation coordination for a single explorer panel."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QPushButton, QSizePolicy
from threep_commons.fs_paths import (
    coerce_path,
    dedup_paths,
    display_path_text,
    is_drive_root,
    is_path_under_root,
    normalize_windows_path_text,
    path_key,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ...explorer_tab import ExplorerTab
    from ...panel_widget import PanelWidget


def _navigation_root_text(path: Path | str) -> str:
    candidate = coerce_path(path)
    if is_drive_root(candidate):
        return candidate.drive
    if os.name == "nt":
        name = candidate.name.strip()
        if name:
            return name
    return display_path_text(candidate)


class PanelNavigationCoordinator:
    """Drive root selection, history movement, and address-bar flow."""

    def __init__(
        self,
        panel: PanelWidget,
        *,
        is_hidden_or_system_entry: Callable[[os.DirEntry[str]], bool],
    ) -> None:
        self.panel = panel
        self._is_hidden_or_system_entry = is_hidden_or_system_entry

    def rebuild_root_controls(self, current_path: Path | None) -> None:
        roots = self.safe_roots(current_path)
        self.panel.set_root_paths(roots)
        self.rebuild_root_buttons(current_path, roots)
        self.rebuild_root_combo(current_path, roots)

    def rebuild_root_buttons(
        self, current_path: Path | None, roots: list[Path]
    ) -> None:
        while self.panel.root_buttons_layout.count():
            item = self.panel.root_buttons_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.panel.root_buttons = []
        for root_path in roots:
            button = QPushButton(_navigation_root_text(root_path))
            button.setFont(self.panel.navigation_font)
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            button.setToolTip(display_path_text(root_path))
            button.setCheckable(True)
            button.setChecked(
                current_path is not None and is_path_under_root(current_path, root_path)
            )
            button.clicked.connect(self._navigate_to_root_callback(root_path))
            button.installEventFilter(self.panel.focus_watcher)
            self.panel.root_buttons_layout.addWidget(button)
            self.panel.root_buttons.append(button)

        self.panel.root_buttons_layout.addStretch(1)

    def rebuild_root_combo(self, current_path: Path | None, roots: list[Path]) -> None:
        self.panel.root_combo.setVisible(self.panel.show_root_dropdown_enabled)
        if not self.panel.show_root_dropdown_enabled:
            return

        self.panel.root_combo.blockSignals(True)
        try:
            self.panel.root_combo.clear()
            for root_path in roots:
                self.panel.root_combo.addItem(
                    _navigation_root_text(root_path), str(root_path)
                )
                combo_idx = self.panel.root_combo.count() - 1
                self.panel.root_combo.setItemData(
                    combo_idx,
                    display_path_text(root_path),
                    Qt.ItemDataRole.ToolTipRole,
                )

            if current_path is None:
                return

            match_index = -1
            for index, root_path in enumerate(roots):
                if is_path_under_root(current_path, root_path):
                    match_index = index
                    break

            if match_index >= 0:
                self.panel.root_combo.setCurrentIndex(match_index)
        finally:
            self.panel.root_combo.blockSignals(False)

    def safe_roots(self, current_path: Path | None) -> list[Path]:
        try:
            provided_roots = [
                coerce_path(p) for p in self.panel.provided_roots(current_path)
            ]
        except Exception:
            provided_roots = []
        roots = self.existing_unique_paths(provided_roots)
        if not roots:
            roots = self.fallback_roots(current_path)
        return sorted(
            roots,
            key=lambda p: (
                _navigation_root_text(p).lower(),
                display_path_text(p).lower(),
            ),
        )

    def existing_unique_paths(self, paths: list[Path]) -> list[Path]:
        return dedup_paths(paths, require_existing=True)

    def fallback_roots(self, current_path: Path | None) -> list[Path]:
        candidates: list[Path] = []
        if current_path is not None:
            current = Path(current_path).expanduser()
            candidates.append(current)
            if current.anchor:
                candidates.append(Path(current.anchor))

        home = Path.home()
        candidates.append(home)
        if home.anchor:
            candidates.append(Path(home.anchor))

        root_path = Path(os.sep)
        candidates.append(root_path)

        fallback = self.existing_unique_paths(candidates)
        if fallback:
            return fallback
        return [home]

    def go_back(self) -> None:
        tab = self.panel.current_tab()
        if tab is not None:
            tab.navigation.go_back()

    def go_forward(self) -> None:
        tab = self.panel.current_tab()
        if tab is not None:
            tab.navigation.go_forward()

    def go_up(self) -> None:
        tab = self.panel.current_tab()
        if tab is not None:
            tab.navigation.go_up()

    def go_root(self) -> None:
        tab = self.panel.current_tab()
        if tab is None:
            return

        current_path = tab.navigation.path
        matches = [
            root
            for root in self.panel.root_paths
            if is_path_under_root(current_path, root)
        ]
        if matches:
            root_path = max(matches, key=lambda p: len(path_key(p)))
            tab.navigation.set_path(root_path)
            return

        if current_path.anchor:
            tab.navigation.set_path(Path(current_path.anchor))

    def refresh_current_path(self) -> None:
        tab = self.panel.current_tab()
        if tab is not None:
            tab.navigation.refresh()

    def on_address_submitted(self) -> None:
        tab = self.panel.current_tab()
        if tab is None:
            return

        text = self.panel.address_edit.text().strip()
        if not text:
            return
        self.panel.stop_address_completion_timer()
        self.hide_address_completion_popup()
        tab.navigation.set_path(coerce_path(normalize_windows_path_text(text)))

    def set_address_text_programmatically(self, text: str) -> None:
        self.panel.set_address_completions_enabled(False)
        try:
            self.panel.address_edit.setText(text)
        finally:
            self.panel.set_address_completions_enabled(True)
        self.panel.stop_address_completion_timer()
        self.panel.set_address_completion_suggestions([])
        self.hide_address_completion_popup()

    def schedule_address_completion_update(self, _text: str) -> None:
        if not self.panel.address_completions_enabled:
            return
        self.panel.start_address_completion_timer(
            self.panel.ADDRESS_COMPLETION_DEBOUNCE_MS
        )

    def refresh_address_completions(self) -> None:
        if (
            not self.panel.address_completions_enabled
            or not self.panel.address_edit.hasFocus()
        ):
            self.hide_address_completion_popup()
            return
        raw_text = self.panel.address_edit.text().strip()
        suggestions = self.collect_address_completion_paths(raw_text)
        self.panel.set_address_completion_suggestions(suggestions)
        if not suggestions:
            self.hide_address_completion_popup()
            return
        self.panel.show_address_completion_popup()

    def on_address_completion_activated(self, path_text: str) -> None:
        selected = str(path_text).strip()
        if not selected:
            return
        self.set_address_text_programmatically(selected)
        self.panel.address_edit.setFocus()
        self.panel.address_edit.setCursorPosition(len(selected))

    def hide_address_completion_popup(self) -> None:
        popup = self.panel.completion_popup()
        if popup is not None and popup.isVisible():
            popup.hide()

    def collect_address_completion_paths(self, raw_text: str) -> list[str]:
        context = self.resolve_address_completion_context(raw_text)
        if context is None:
            return []
        parent_dir, prefix = context
        if not parent_dir.exists() or not parent_dir.is_dir():
            return []

        prefix_cmp = prefix.casefold()
        suggestions: list[str] = []
        try:
            with os.scandir(parent_dir) as iterator:
                for entry in iterator:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    if not is_dir:
                        continue
                    if (
                        not self.panel.show_hidden_enabled
                        and self._is_hidden_or_system_entry(entry)
                    ):
                        continue
                    name = entry.name
                    if prefix_cmp and not name.casefold().startswith(prefix_cmp):
                        continue
                    suggestions.append(display_path_text(parent_dir / name))
        except OSError:
            return []
        return sorted(set(suggestions), key=str.casefold)

    def resolve_address_completion_context(
        self, raw_text: str
    ) -> tuple[Path, str] | None:
        text = normalize_windows_path_text(str(raw_text or "").strip())
        if not text:
            return None

        base_path = coerce_path(self.panel.current_path())
        expanded = normalize_windows_path_text(os.path.expanduser(text))
        has_trailing_separator = expanded.endswith(("\\", "/"))
        candidate = coerce_path(expanded)
        if has_trailing_separator:
            parent_dir = (
                candidate if candidate.is_absolute() else (base_path / candidate)
            )
            return parent_dir.expanduser(), ""

        prefix = candidate.name
        parent_part = candidate.parent
        if candidate.is_absolute():
            parent_dir = parent_part if str(parent_part) not in {"", "."} else candidate
        else:
            parent_dir = (
                base_path
                if str(parent_part) in {"", "."}
                else (base_path / parent_part)
            )
        return parent_dir.expanduser(), prefix

    def on_root_selected(self, index: int) -> None:
        root_paths = self.panel.root_paths
        if index < 0 or index >= len(root_paths):
            return
        self.navigate_to_root(root_paths[index])

    def navigate_to_root(self, root_path: Path) -> None:
        tab = self.panel.current_tab()
        if tab is None:
            return
        tab.navigation.set_path(root_path)

    def show_history_menu(self) -> None:
        tab = self.panel.current_tab()
        if tab is None:
            return

        history_entries = tab.navigation.history
        current_index = tab.navigation.history_index
        if not history_entries:
            return

        existing_menu = self.panel.take_history_menu()
        if existing_menu is not None:
            existing_menu.close()
            existing_menu.deleteLater()

        menu = QMenu(self.panel)
        for index in range(len(history_entries) - 1, -1, -1):
            entry = history_entries[index]
            action = menu.addAction(display_path_text(entry))
            action.setToolTip(display_path_text(entry))
            action.setCheckable(True)
            action.setChecked(index == current_index)
            action.triggered.connect(self._history_index_callback(tab, index))

        self.panel.set_history_menu(menu)
        menu.popup(
            self.panel.address_edit.mapToGlobal(
                self.panel.address_edit.rect().bottomLeft()
            )
        )

    def _navigate_to_root_callback(self, root_path: Path) -> Callable[[bool], None]:
        """Build a callback that navigates the active tab to a root path."""

        def _handle_clicked(_checked: bool = False) -> None:
            self.navigate_to_root(root_path)

        return _handle_clicked

    def _history_index_callback(
        self,
        tab: ExplorerTab,
        index: int,
    ) -> Callable[[bool], None]:
        """Build a callback that navigates to a fixed history index."""

        def _handle_triggered(_checked: bool = False) -> None:
            tab.navigation.go_to_history_index(index)

        return _handle_triggered
