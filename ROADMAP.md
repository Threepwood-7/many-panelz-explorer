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

### F006 — Dynamic Context Menu — Folder Intelligence

**Summary:** The application's main menu gains a dynamic top-level **Context** menu
that is rebuilt whenever the active panel navigates to a new folder. The menu
reflects what kind of project or content lives in the current directory (or its
immediate children), surfacing relevant actions without the user having to seek
them out.

**Motivation:** A file explorer is used in wildly different situations — a Python
project root, a media dump folder, a Git repo, a Node app. The current menu is
static and generic. For a developer and media-heavy workflow, 80% of the most
useful actions are contextual. Surfacing them automatically eliminates repeated
"open terminal → type command" loops and reduces tool-switching.

---

#### Detection Behaviour

- Detection runs on every navigation event in the active panel (path change, tab
  switch, window focus change).
- **Scope:** the current folder itself AND its immediate children (one level deep).
  This means standing in `c:\projects` and having `my-app/pyproject.toml` a level
  down is enough to trigger Python mode.
- Multiple modes can be active simultaneously. All matching modes contribute
  their action groups to the Context menu, separated by a labelled section header
  per mode.
- Detection is fast and synchronous (filesystem stat calls only, no file parsing
  at detect time). Heavy parsing (e.g., reading `pyproject.toml` scripts) happens
  lazily when the menu is opened, not on every navigation.

---

#### Built-in Context Modes

**Python Project**
Triggered by: `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`,
`uv.lock`, `hatch.toml`, `.venv/`, `.python-version` — in current folder or any
immediate child folder.

Actions:
- Open project root in Code Editor (tool: `code_editor`)
- Open terminal here with venv auto-activated (detect `.venv/`, `uv`, `hatch`)
- **Runnable scripts submenu** — discovered from all of:
  - `[project.scripts]` in `pyproject.toml`
  - `[tool.hatch.envs.*.scripts]` in `pyproject.toml`
  - `run_*.py`, `main.py`, `__main__.py` globbed in the project root
  - Entries shown as "Run: <script-name>" with the resolved command
- Open `pyproject.toml` in Code Editor
- Show detected Python version (from `.python-version` or `pyproject.toml
  requires-python`)

**Git Repository**
Triggered by: `.git/` in current folder or any immediate child.

Actions:
- Open in configured Git GUI (tool: `git_gui`) — user sets path in settings
- Open terminal here
- Copy remote origin URL to clipboard (parsed from `.git/config`)
- Open remote URL in browser (if remote matches github.com / gitlab.com /
  bitbucket.org)
- Show current branch name inline as a disabled menu label (e.g.,
  `  Branch: main ✓` or `  Branch: feature/x *`)

**Node / JS / TS Project**
Triggered by: `package.json`, `bun.lockb`, `pnpm-lock.yaml`, `yarn.lock`,
`node_modules/` — in current folder or immediate child.

Actions:
- Open in Code Editor
- Open terminal here
- **npm/bun scripts submenu** — scripts parsed from `package.json["scripts"]`,
  shown as "Run: <script-name>"
- Open `package.json` in Code Editor

**Docker / Container Project**
Triggered by: `Dockerfile`, `docker-compose.yml`, `compose.yaml`,
`.dockerignore` — in current folder or immediate child.

Actions:
- Open terminal here
- `docker compose up` (in terminal)
- `docker compose down` (in terminal)
- Open `docker-compose.yml` in Code Editor

**Media Folder**
Triggered by: ≥30% of files in current folder (by count) are `.mp4`, `.mkv`,
`.avi`, `.mov`, `.wmv`, `.m4v`, `.webm`.

Actions:
- Play all in Default Media Player (tool: `default_media_player`)
- Play all in Alternative Media Player (tool: `alt_media_player`)
- Play selected file(s) in Default Media Player
- Play selected file(s) in Alternative Media Player
- Open ffmpeg terminal here (if `ffmpeg` found on PATH or configured)
- Show total media file count + total size (computed lazily)

**Image Folder**
Triggered by: ≥30% of files in current folder are `.jpg`, `.jpeg`, `.png`,
`.webp`, `.gif`, `.tiff`, `.bmp`, `.heic`, `.avif`.

Actions:
- Open slideshow in Default Image Viewer (tool: `default_image_viewer`)
- Open in Alternative Image Viewer (tool: `alt_image_viewer`)
- Open selected file(s) in Default Image Viewer
- Open selected file(s) in editor (tool: `default_image_editor`, optional)
- Show image count + total size (computed lazily)

**Subtitle / Release Folder** *(bonus for media workflows)*
Triggered by: presence of both a video file type AND `.srt` / `.ass` / `.sub` /
`.nfo` in the same folder.

Actions:
- Open `.nfo` in Default Editor
- Play in Default Media Player (passes the folder as playlist root)
- Play in Alternative Media Player

**Archive Folder**
Triggered by: ≥30% of files are `.zip`, `.7z`, `.rar`, `.tar`, `.gz`, `.xz`,
`.zst`.

Actions:
- Extract selected to subfolder
- Extract all here
- Open selected in configured archive tool (tool: `archive_tool`)

---

#### Extended Tool Registry

New named tools added to the settings system (extending existing
`OpsSettingsDomain` tool paths, or a new `ContextToolsDomain`):

| Key | Label in Settings | Used by |
|---|---|---|
| `code_editor` | Code Editor | Python, Node, Docker, Git |
| `default_media_player` | Default Media Player | Media, Subtitle |
| `alt_media_player` | Alternative Media Player | Media, Subtitle |
| `default_image_viewer` | Default Image Viewer | Image |
| `alt_image_viewer` | Alternative Image Viewer | Image |
| `default_image_editor` | Image Editor (optional) | Image |
| `pdf_viewer` | PDF Viewer | (future PDF mode) |
| `git_gui` | Git GUI | Git |
| `archive_tool` | Archive Tool | Archive |

Each tool entry has:
- `exe_path` — path to the executable (browsable in settings)
- `args_template` — optional launch arguments with placeholders (default
  reasonable per tool, user-overridable)

Placeholders available in `args_template`:
- `{folder}` — current folder path
- `{file}` — first selected file path
- `{files}` — all selected file paths, space-separated (quoted individually)
- `{project_root}` — detected project root (nearest ancestor with detection
  signal, e.g., where `pyproject.toml` lives)

---

#### User-Defined Custom Modes

Users can define additional context modes in a JSON file located at:
`%APPDATA%\ThreepSoftwz\many_panelz_explorer\custom_modes.json`

Each custom mode is a JSON object with three sections: `name`, `detect`, and
`actions`. The format is intentionally minimal.

```json
[
  {
    "name": "Blender Project",
    "detect": {
      "any_file_matches": ["*.blend"],
      "any_child_file_matches": ["*.blend"]
    },
    "actions": [
      {
        "label": "Open in Blender",
        "exe": "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
        "args": "{folder}"
      },
      {
        "label": "Render {file}",
        "exe": "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
        "args": "-b {file} -a",
        "requires": "single_file_selected"
      }
    ]
  },
  {
    "name": "Unity Project",
    "detect": {
      "any_child_folder_matches": ["Assets", "ProjectSettings"]
    },
    "actions": [
      {
        "label": "Open in Unity Hub",
        "exe": "C:\\Program Files\\Unity Hub\\Unity Hub.exe",
        "args": "--headless open --project {folder}"
      }
    ]
  }
]
```

**Detection keys:**

| Key | Meaning |
|---|---|
| `any_file_matches` | Any file in current folder matches glob |
| `any_child_file_matches` | Any file in any immediate child folder matches glob |
| `any_folder_matches` | Current folder name matches glob |
| `any_child_folder_matches` | Any immediate child folder name matches glob |

Multiple keys are ANDed (all must match for the mode to activate). To express OR
logic, define two separate mode entries with the same `name` — they merge in the
menu.

**Action keys:**

| Key | Required | Meaning |
|---|---|---|
| `label` | yes | Menu item text (supports `{file}` placeholder for display) |
| `exe` | yes | Path to executable, OR a registered tool key like `"tool:code_editor"` |
| `args` | no | Argument string with placeholders; omit to launch with no args |
| `requires` | no | `"single_file_selected"` or `"any_file_selected"` — greys out if not met |

**Referencing registered tools** — instead of a hardcoded `exe` path, a custom
mode can reference a tool already configured in settings:

```json
{ "label": "Edit in Code Editor", "exe": "tool:code_editor", "args": "{folder}" }
```

This keeps custom modes resilient to tool path changes made in the settings UI.

---

#### Architecture Notes

- A new module `_context/` under `src/many_panelz_explorer/` owns this feature:
  - `detector.py` — `ContextDetector` class; `detect(path) -> list[ContextMode]`
  - `modes/` — one file per built-in mode (`python_mode.py`, `git_mode.py`, etc.)
  - `custom_loader.py` — loads and validates `custom_modes.json`
  - `menu_builder.py` — takes active modes, builds `QMenu` structure
  - `tool_registry.py` — resolves tool keys to `(exe_path, args_template)` from
    settings
- `WindowUiComposer` (in `ui/window/actions.py`) gains a method
  `rebuild_context_menu(modes: list[ContextMode])` called on every navigation.
- The dynamic Context menu is a top-level `QMenu` in the main menubar, rebuilt
  in-place (not removed and re-added, to preserve menu bar layout stability).
- Script/config parsing (e.g., `pyproject.toml`, `package.json`) is done in a
  `QThreadPool` worker triggered when the menu is first opened (`aboutToShow`
  signal), with a loading placeholder item shown during parse.

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
