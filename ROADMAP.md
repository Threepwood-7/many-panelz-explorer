# many-panelz-explorer — Functional Roadmap

This document tracks planned functional improvements. Items are categorized as
**Planned** (committed), **Backlog** (considered, not scheduled), or **Rejected**
(deliberately excluded to keep scope focused).

---

## Planned

### F001 — Bookmarks / Favorites

**Summary:** Allow users to pin frequently visited folders and access them from a
persistent sidebar or toolbar.

**Motivation:** Navigation to deeply nested or frequently used directories requires
repeated traversal. Without a bookmark system, users either rely on session
restoration (which restores the last state, not arbitrary favorites) or retype
paths manually. For power users managing projects across many locations, this is a
significant friction point.

**Scope:**
- Named bookmarks with user-defined labels
- Persist across sessions (stored in settings)
- Accessible via a sidebar panel (toggleable) or a dedicated toolbar dropdown
- Context menu on any folder to "Add to Bookmarks"
- Drag-and-drop reordering of bookmarks
- Optional folder icons/colors for visual grouping

**Notes:**
- Bookmarks are per-application, not per-window or per-panel.
- Should integrate with the existing `SessionSettingsDomain` or a new
  `BookmarksDomain` under `_settings/`.

---

### F002 — Dual-Panel Sync / Mirror Navigation

**Summary:** A toggleable mode where navigating in one panel automatically mirrors
the same path in a designated companion panel.

**Motivation:** Many file management workflows involve comparing or moving content
between two related directories (e.g., source vs. destination, local vs. archive).
Currently both panels navigate independently, requiring the user to manually keep
them in sync. A mirror mode eliminates this manual overhead.

**Scope:**
- Per-split-pair toggle: "Sync navigation" between two adjacent panels
- When active, navigating panel A auto-navigates panel B to the same path
- Bidirectional: navigating either panel syncs the other
- Visual indicator on both panels when sync mode is active
- Sync mode survives tab switches within the linked panel
- Sync mode is NOT persisted across sessions (it is a transient workflow state)

**Notes:**
- Synced panels should still allow independent tab management; only the active
  tab's navigation is mirrored.
- The binary-tree layout model (`PanelTreeModel`) will need a way to express
  sync relationships between sibling leaf nodes.

---

### F003 — Folder Size Calculation

**Summary:** On-demand (and optionally background) recursive size calculation for
folders in the file list, displayed inline in the Size column.

**Motivation:** The file list currently shows sizes for files but shows nothing (or
a placeholder) for directories. When managing disk space, users must leave the app
or open a separate tool (e.g., WinDirStat) to understand which folders are large.
Having inline folder sizes directly in the explorer dramatically speeds up cleanup
and organization workflows.

**Scope:**
- Right-click context menu action: "Calculate Size" on one or more selected folders
- Size displayed inline in the existing Size column once calculated
- Calculation runs in a background thread to avoid blocking the UI
- Progress indicator while calculating (spinner or animated label in the cell)
- Cached result shown until the tab refreshes or the user recalculates
- Optional: auto-calculate all folders in a directory on a configurable delay
- Sizes formatted consistently with file sizes (KB/MB/GB with appropriate units)

**Notes:**
- Background calculation should be cancellable (e.g., on tab navigation away).
- Cache is in-memory only; sizes are not persisted across sessions as they can
  become stale.

---

### F004 — Disk Usage / Free Space Indicator

**Summary:** Show available and used disk space for the drive of the currently
active path, visible directly in the panel without switching to another tool.

**Motivation:** The root/drive selector dropdown exists but shows only drive labels
and letters. There is no at-a-glance indication of how full a drive is. Users
frequently need this context when deciding where to copy files, which requires
alt-tabbing to Windows Explorer or running a separate command. Surfacing it
directly in the panel keeps the user in context.

**Scope:**
- Per-panel display: shows the free/total space for the drive of the current path
- Placement: status bar area within the panel, or as an augmented tooltip/label
  on the root dropdown
- Compact format: e.g., `238 GB free of 931 GB`
- Optional thin progress bar (used space ratio) alongside the label
- Updates when the panel navigates to a different drive
- Refresh on the same interval as the mount cache (currently 2-second TTL)
- Toggleable via preferences (on by default)

**Notes:**
- Data source: `QStorageInfo` already used in `mounts.py`; extend it to also
  expose `bytesAvailable()` and `bytesTotal()`.
- The indicator should update lazily (not on every keypress), only on path change.

---

### F005 — "Explorer Here" / "Commander Here" Context Actions

**Summary:** Context menu actions on any folder or file that open a new Windows
Explorer window or a new many-panelz-explorer window rooted at that location.

**Motivation:** Interoperability with the system shell is essential. Users often
need to hand off a location to another tool — to use Windows Explorer for
drag-and-drop to external apps, or to open a second independent many-panelz-explorer
instance focused on a subfolder. Without this, users must copy the path, open the
target application, and navigate manually.

**Scope:**

**Explorer Here:**
- Right-click on any folder (or the parent folder of a selected file): "Open in
  Explorer"
- Launches `explorer.exe` with the target path
- Works on both files (opens containing folder) and folders (opens that folder)

**Commander Here:**
- Right-click on any folder: "Open in Commander" (i.e., open a new
  many-panelz-explorer window)
- Launches a new `ExplorerWindow` routed through `AppController`, not a new
  process — so it shares the same session/settings
- The new window opens with the selected folder as its initial path
- Optional: "Open in Commander (new tab)" to open in a new tab in the active
  panel instead of a new window

**Notes:**
- "Explorer Here" uses `subprocess.Popen(['explorer.exe', path])` or
  `os.startfile(path)`.
- "Commander Here (new window)" should call the existing
  `AppController.open_new_window(initial_path=...)` (or equivalent); this method
  may need to be added or extended.
- Both actions should appear in the existing context menu in `explorer_tab.py`.
- The labels in the menu should use the application display name from
  `constants.py` (e.g., "Open in many-panelz-explorer") rather than hardcoding
  "Commander".

---

### F006 - Dynamic Context Menu - Folder Intelligence

**Summary:** Add a dynamic top-level **Context** menu in the main menubar that
adapts to the active folder (and immediate children) and surfaces mode-specific
actions.

**Motivation:** The current menu is static. Most high-value actions in real
workflows are contextual (Python/Git/Node/media/etc.). A dynamic menu reduces
tool switching and repetitive terminal command entry.

---

#### Phase 1 (Implemented)

**Scope:**
- Modes: **Python Project**, **Git Repository**, **Node / JS / TS Project**
- Detection scope: current folder + immediate child folders
- Detection triggers: active path change, active tab change, window activation
- Child scan cap: configurable in settings (default `33`)
- Per-root grouping: current and child matches are shown as separate root groups
- Top-level Context menu is hidden when no modes are detected

**Python mode (Phase 1):**
- Open project root in Code Editor (`code_editor`)
- Open terminal here (best-effort venv activation)
- Open `pyproject.toml` in Code Editor
- Disabled info row with detected Python version
- Runnable scripts submenu (lazy-loaded on submenu open):
  - `[project.scripts]`
  - `[tool.hatch.envs.*.scripts]`
  - `run_*.py`, `main.py`, `__main__.py`

**Git mode (Phase 1):**
- Open in Git GUI (`git_gui`)
- Open terminal here
- Copy remote origin URL
- Open remote URL in browser (GitHub/GitLab/Bitbucket only)
- Disabled info row with current branch

**Node mode (Phase 1):**
- Open project root in Code Editor (`code_editor`)
- Open terminal here
- Open `package.json` in Code Editor
- Runnable scripts submenu (lazy-loaded from `package.json["scripts"]`)
- Runner selection: `packageManager` field, then lockfile hints, else `npm`

**Context tool settings (Phase 1):**
- `context/tools/code_editor/exe_path`
- `context/tools/code_editor/args_template`
- `context/tools/git_gui/exe_path`
- `context/tools/git_gui/args_template`

**General behavior (Phase 1):**
- Missing tool paths show actions as disabled with a configuration hint
- Script parsing is asynchronous and shows `Loading...` while resolving
- Runnable scripts launch in a visible terminal

---

#### Deferred Phase 2+

The following parts remain planned and are intentionally deferred:
- Built-in modes: Docker, Media, Image, Subtitle/Release, Archive
- Custom user-defined modes (`custom_modes.json`)
- Extended context tool registry beyond `code_editor` and `git_gui`

---
## Backlog

### F007 — Filter / Search Within Current Folder

**Summary:** A live filter bar within the active tab that narrows the file list by
filename, extension, size range, or modification date — with optional regex support.

**Status:** Inline filtering infrastructure already partially exists. This item is
deferred until the planned items above are complete.

**Possible scope when scheduled:**
- Persistent filter bar (toggleable, not a popup)
- Filters: name substring, glob pattern, regex, extension, size range, date range
- Filter state shown visually (e.g., highlighted bar when active)
- Filter is per-tab and cleared on navigation

---

## Rejected (Out of Scope)

| Feature | Reason |
|---|---|
| Batch Rename | Out of scope for current focus; use external tools |
| File Preview Pane | Adds significant complexity; external viewers are sufficient |
| Keyboard Command Palette | Not aligned with target workflow |
| Archive Browse-in-Place | High complexity, low priority relative to other items |
| Operation History / Undo | Complex to implement correctly; send2trash covers the main safety need |
