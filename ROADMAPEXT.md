# many-panelz-explorer — Extended Feature Roadmap

Features gathered from Total Commander (Ghisler) forum and Double Commander
community (GitHub issues, SourceForge reviews, forum threads). Each entry is an
independent candidate — not yet triaged into Planned/Backlog. IDs are prefixed
`FR` to distinguish from the primary roadmap (`F` prefix).

Sources consulted:
- https://www.ghisler.ch/board/viewforum.php?f=14 (TC Suggestions, sorted by
  replies and views)
- https://github.com/doublecmd/doublecmd/issues
- https://doublecmd.sourceforge.io/forum/
- https://sourceforge.net/projects/doublecmd/reviews/

---

## FR001 — Per-Folder Persistent Sort Order and View Mode

**Community signal:** DC GitHub #605 (open, upvoted); TC forum multiple threads.

**Summary:** Each folder remembers the sort column, sort direction, and view mode
(details / thumbnails / brief) that were active when the user last visited it.
Navigating away and returning restores the previous state automatically.

**Motivation:** Power users typically sort `Downloads` by date descending,
project source folders by name ascending, and media folders by size. The current
global sort state forces repeated manual re-sorting when switching contexts.

**Scope:**
- Persist per-folder: sort column index, sort direction, and view mode
- Scope: per-tab (not per-panel or global)
- Storage: in-memory dict keyed by absolute path during session; optionally
  persisted to `SessionSettingsDomain` across sessions (opt-in setting)
- Maximum cache size: configurable (default 500 entries) to avoid unbounded growth
- Interacts with column width persistence already in `ExplorerTab`

**Technical notes:**
- `ExplorerTab` in `explorer_tab.py` already persists column widths via
  `_save_column_widths()` / `_restore_column_widths()`. The same lifecycle hooks
  (`_on_path_about_to_change`, `_on_path_changed`) can carry sort state.
- `FastDirModel` (extends `QFileSystemModel`) exposes `sort(column, order)`.
  Current sort state is readable via `sortColumn()` and `sortOrder()` on the
  `QTreeView`.
- View mode toggle is not yet implemented — this feature depends on or drives the
  view mode feature if one is added later.
- Sort state dict: `dict[str, tuple[int, Qt.SortOrder]]` — small, cheap to store.
- For cross-session persistence: add a `per_folder_sort` key to
  `SessionSettingsDomain`, serialised as JSON.

---

## FR002 — Recent Files Virtual Folder

**Community signal:** TC forum topic #72164 ("new or recent files", ~4k views).

**Summary:** A special navigation target — accessible as a bookmark or pinned tab
— that lists files recently created or modified across the filesystem without
performing a full scan. Uses the Windows Search index (via `ISearchQueryHelper` /
`SystemIndex` OLE DB provider) or the shell `KNOWNFOLDERID_Recent` API.

**Motivation:** After working across many folders, finding "what did I just touch?"
requires either memory or a separate search. A persistent recent-files view
accessible in one click eliminates that friction entirely.

**Scope:**
- Virtual folder entry displayable in the file list pane (not a real path)
- Configurable item count (default 100)
- Configurable scope: recent across all drives, or limited to specific root paths
- Sortable by date modified descending (default), name, size
- Double-clicking an entry navigates to the file's real parent folder with the
  file pre-selected (same as selection memory)
- Accessible via a bookmark entry and optionally via a dedicated toolbar button
- Marked with a special `[Recent]` label in the address bar

**Technical notes:**
- Windows Search index query via `win32com` or `subprocess` calling
  `wmic` / PowerShell `Get-Item` is an option; preferred approach is the
  `Windows.Storage.Search` WinRT API via `pythonwinrt` or direct COM
  (`ISearchQueryHelper`).
- Fallback (if index unavailable): `os.scandir` with mtime sort on user-specified
  roots — slower but functional.
- Virtual folder requires `ExplorerTab` to support a non-filesystem data source.
  `FastDirModel` would need a parallel `VirtualListModel(QAbstractItemModel)` for
  this mode, with the tab switching model based on the current path token.
- Address bar: treat `recent://` as a reserved virtual path token that triggers
  virtual model mode.
- Navigation from virtual result → real parent: reuse existing selection-memory
  mechanism in `ExplorerTab._selection_memory`.

---

## FR003 — Named Tab Sessions

**Community signal:** TC forum #77335 ("Auto-save tabs"); DC forum layout requests.

**Summary:** Save the complete set of open tabs across all panels and windows as a
named session. Sessions can be recalled by name at any time, independently of the
auto-restored startup session. Useful for distinct work contexts ("client A",
"media sorting", "release prep").

**Motivation:** The app already restores the last session on startup via
`SessionSettingsDomain`. The gap is: users often work in recurring, distinct
contexts. Having to manually re-open all tabs for each context is friction.

**Scope:**
- "Save session as…" action: prompts for a name and serialises all windows,
  panels, and tabs to a named slot
- "Open session…" action: lists saved sessions; opening one restores that layout
  in the current window (replaces current tabs) or in a new window (user choice)
- "Manage sessions…" dialog: rename, delete, view saved sessions
- Sessions stored as JSON files in the app data directory:
  `%LOCALAPPDATA%\ThreepSoftwz\many_panelz_explorer\sessions\<name>.json`
- Session format reuses the existing panel-tree and tab-state serialisation
  already in `WindowPersistenceCoordinator`
- Crash-safe: auto-save the working session to a `_autosave.json` slot every N
  minutes (configurable, default 5 min) — distinct from named sessions

**Technical notes:**
- `WindowPersistenceCoordinator` (`ui/window/persistence.py`) already implements
  `save_state()` / `restore_state()` against `SettingsManager`. Extend to accept
  an optional target path argument instead of always writing to the default key.
- Session JSON schema mirrors the existing `SessionSettingsDomain` window/panel
  structure — no new schema needed, just a different storage location.
- Auto-save timer: a `QTimer` owned by `AppController`, firing every N minutes,
  calling `save_state()` on each active window to the `_autosave` slot.
- "Open session in new window" reuses `AppController.open_new_window()`.
- Sessions menu: a dynamic `QMenu` under the main File or Window menu, rebuilt
  when the sessions directory changes (use `QFileSystemWatcher` on the sessions
  folder).

---

## FR004 — Breadcrumb Navigation Bar

**Community signal:** TC forum #12993, #22671, #22937, #47483 (multiple threads,
thousands of views); DC forum (addressed differently per version).

**Summary:** A clickable, segmented path bar where each folder in the current path
is a button. Clicking a segment navigates directly to that ancestor. Middle-click
on a segment opens it in a new tab. Replaces or toggles with the current address
bar.

**Motivation:** The address bar is great for typing but poor for mouse navigation
in deep hierarchies. Clicking through 6 levels of folders to go up 3 levels is
faster with a breadcrumb. It also makes the current path more readable than a
truncated text field.

**Scope:**
- Toggle between address bar mode and breadcrumb mode (per-panel preference,
  persisted)
- Each segment is a `QPushButton` or custom `QLabel` with a click handler
- Last segment (current folder) is non-clickable, shown in bold
- Separator chevron `›` between segments
- Overflow: if the path is too long for the bar width, leftmost segments are
  collapsed into a `…` menu button that expands them
- Middle-click on any segment → open that path in a new tab
- Right-click on any segment → context menu: "Open here", "Open in new tab",
  "Open in new window", "Copy path"
- Keyboard: `Alt+D` always focuses the address bar regardless of current mode
  (breadcrumb mode temporarily shows the editable field on `Alt+D`)

**Technical notes:**
- Breadcrumb widget lives in `panel_widget.py` alongside the existing address
  bar `QLineEdit`. Both are stacked in a `QStackedWidget`; a settings flag
  controls which is visible.
- Segment buttons generated by splitting `Path(current_path).parts` on each
  navigation event (`_on_path_changed` signal in `PanelWidget`).
- `QSizePolicy.Expanding` with a custom `sizeHint` based on text width per
  segment; overflow detection via `resizeEvent`.
- Overflow menu: a `QToolButton` with `setMenu()` containing the hidden segments.
- The breadcrumb widget does not replace toolbar logic — it is purely a path
  display/navigation widget layered above the file list.

---

## FR005 — Checkbox Selection Column

**Community signal:** TC forum #18268 ("File selection with checkbox"); DC
SourceForge reviews (touchscreen / single-click selection requests).

**Summary:** An optional leftmost column containing a checkbox per row. Clicking
the checkbox toggles that file's selection independently of keyboard modifiers.
Useful for non-contiguous multi-selection without holding Ctrl, and for
touch/stylus input.

**Motivation:** Ctrl+click for non-contiguous selection is muscle memory for some
users but a barrier for others — especially on touchscreens or for users who come
from GUI tools with checkbox lists. A checkbox column makes multi-selection
immediately discoverable.

**Scope:**
- Toggleable via View menu and/or column header right-click (persisted per-tab or
  globally — configurable)
- Column header checkbox: check all / uncheck all in current view
- Checkbox state is additive with existing keyboard selection (they represent the
  same underlying selection set)
- Checkboxes survive folder refresh (selected paths re-checked if still present)
- Narrow column (24px), no header label, always leftmost

**Technical notes:**
- Implemented as a custom `QStyledItemDelegate` on column 0 of the `QTreeView`
  in `ExplorerTab`, drawing a checkbox in the decoration area.
- Alternatively: a proxy model (`QSortFilterProxyModel` subclass) that injects a
  virtual column 0 with `Qt.CheckStateRole` data, leaving `FastDirModel` untouched.
  The proxy approach is cleaner as it avoids touching the filesystem model.
- The checkbox column is inserted at index 0 by shifting existing columns right
  via `QHeaderView.moveSection()` or via the proxy model.
- `selectionChanged` signal on `QItemSelectionModel` stays the source of truth;
  checkbox toggling simply calls `selectionModel().select()` with
  `QItemSelectionModel.Toggle`.
- Column visibility controlled by a `bool` flag in `UiPreferences` dataclass.

---

## FR006 — Tab Color Labels

**Community signal:** DC SourceForge reviews (2025); DC forum colored tab names.

**Summary:** Each tab in a panel can be assigned a background color (from a small
palette or a color picker). The tab label renders with that background, making it
immediately distinguishable visually when switching between many tabs.

**Motivation:** When juggling 6–8 tabs for different projects, all tabs look
identical. A color label lets users encode meaning visually ("red = urgent", "blue
= media drive", "green = active project").

**Scope:**
- Right-click tab label → "Set tab color…" → small color picker popup (16 preset
  swatches + "Custom…" option)
- Color is per-tab, stored in tab state alongside the path
- "Clear color" option to reset to default
- Color persisted in session state (survives app restart)
- Tab color also visible in named session previews (FR003)
- Color applied as `QTabBar` tab background via `setTabData` + custom
  `QProxyStyle` or `QTabBar::paintEvent` override

**Technical notes:**
- `PanelWidget` manages `QTabWidget`. Tab colors stored in a
  `dict[int, QColor]` (tab index → color), migrated to tab UUID keyed storage
  (since indices shift on close).
- `QTabBar` styling per-tab requires subclassing `QTabBar` and overriding
  `paintEvent`, calling `QTabBar.tabData(index)` to retrieve the stored color,
  then painting the background rect manually before calling the base
  `paintEvent` for text and close button.
- Alternatively use `QTabBar.setTabButton()` with a colored `QLabel` widget as
  the tab decoration — simpler but less native-looking.
- Color serialised as hex string in tab state JSON: `"color": "#e74c3c"`.
- Tab state in `SessionSettingsDomain` already stores path per tab; add optional
  `color` field.

---

## FR007 — Footer Aggregate Row

**Community signal:** TC forum ("New summarized value (e.g. mp3 duration sum)",
22 replies, 34,471 views); TC forum ("add a sum option in custom view", 15 replies,
11,347 views).

**Summary:** The panel's status bar (or a dedicated footer row) shows computed
aggregate values for the current selection: total size (likely already present),
file count by extension, and — for media files — total playback duration computed
via `ffprobe`.

**Motivation:** Knowing that 47 selected MKV files total 38 hours and 212 GB is
actionable information for disk management and media archival. Getting this
currently requires external tools or manual calculation.

**Scope:**
- Always-visible footer bar beneath the file list (or reuse existing status bar)
- Default aggregates shown for any selection:
  - File count / folder count
  - Total size (sum of selected file sizes)
- Media aggregates (shown only when selection contains video/audio files):
  - Total duration (HH:MM:SS) — computed via `ffprobe --print_format json
    --show_entries format=duration`
  - Computed asynchronously; shows "calculating…" then updates in-place
- Image aggregates (shown when selection contains images):
  - Image count
  - Combined pixel count (optional, low priority)
- Computation triggered on selection change, debounced 300 ms to avoid firing
  on every arrow-key press during keyboard selection
- `ffprobe` availability checked once at startup; media duration hidden if not
  found on PATH or in configured tool paths

**Technical notes:**
- Footer widget is a `QLabel` or `QStatusBar` child in `ExplorerTab`.
- `ffprobe` call: `subprocess.run(['ffprobe', '-v', 'quiet', '-print_format',
  'json', '-show_entries', 'format=duration', file], capture_output=True)` per
  file; batched into a `QThreadPool` worker.
- Worker posts results back via `QMetaObject.invokeMethod` or a `Signal(float)`
  on a `QObject` bridge — avoids UI thread blocking.
- Duration computation cancellable: if the selection changes before the worker
  finishes, the running tasks are flagged as stale and their results discarded.
- `ffprobe` path resolved from `OpsSettingsDomain` tool paths (or the new
  `ContextToolsDomain` from F006); fall back to PATH lookup.
- Extension count display: `Counter(Path(f).suffix for f in selected_files)`,
  rendered as e.g. `12 × .mkv, 3 × .srt`.

---

## FR008 — F2 Inline Rename: Base Name Only Selection

**Community signal:** TC forum ("Rename: Separate or hide extension in rename
field", 37 replies); DC GitHub #1057 ("Option to hide file extension in F2 inline
rename").

**Summary:** When pressing F2 to rename a file, the initial text selection covers
only the base name (everything before the last `.`), not the full filename
including extension. The extension remains visible but is not selected, preventing
accidental changes.

**Motivation:** This is standard behaviour in Windows Explorer, macOS Finder, and
most modern file managers. Accidentally overwriting an extension while renaming is
a common, annoying mistake. The fix is a one-liner once the rename delegate is
in place.

**Scope:**
- Applies to inline rename in the file list (`QTreeView`)
- For files with no extension (e.g., `Makefile`, `.gitignore`): select all
- For dotfiles where the dot is the first character (e.g., `.env`): select all
- For multiple extensions (e.g., `archive.tar.gz`): select up to the first dot
  (configurable: first dot vs. last dot)
- Does not affect the multi-rename tool (separate feature)

**Technical notes:**
- `QTreeView.edit()` opens the delegate editor. The rename delegate in
  `ExplorerTab` (or `FastDirModel`) returns a `QLineEdit` from
  `createEditor()`.
- Override `QAbstractItemDelegate.setEditorData()`: after calling `setText()`,
  call `lineEdit.setSelection(0, len(stem))` where `stem =
  Path(filename).stem`.
- Edge cases: `Path('.env').stem` returns `'.env'` (no extension) — guard with
  `if filename.startswith('.') and filename.count('.') == 1: select_all`.
- No model changes required — purely a delegate-level change.

---

## FR009 — Git Status Overlay Icons

**Community signal:** TC forum #48210 ("Git integration with TC") — active thread.

**Summary:** Files and folders within a Git repository receive overlay icons
indicating their Git status (modified, untracked, staged, ignored, clean).
The panel header or status bar shows the current branch name and dirty/clean
indicator. Complements the Git mode already planned in F006.

**Motivation:** Seeing which files are modified without switching to a terminal
or Git GUI is a natural fit for a developer-focused explorer. It brings the
spatial awareness of TortoiseGit into the file list without requiring a shell
extension.

**Scope:**

**Overlay icons:**
- `M` (yellow) — modified (tracked, changed)
- `+` (green) — staged / index-added
- `?` (grey) — untracked
- `!` (red) — conflict
- `-` (grey, dimmed) — ignored
- Clean files: no overlay (no visual noise)
- Folder overlays: aggregate status of children (any modified → show modified)

**Panel strip:**
- Branch name label in the panel toolbar area (right side)
- Dirty indicator: `*` suffix or a small dot icon
- Shown only when the current path is inside a Git repo

**Performance:**
- `git status --porcelain=v1 -z` run once per directory navigation, in a
  background thread
- Results cached per repo root with a 5-second TTL (invalidated on any file
  operation in the repo)
- Overlay rendering only for files returned by `git status` (dirty files);
  all others treated as clean (no overlay) — avoids O(n) model updates

**Technical notes:**
- Git status parsing: run `git -C <repo_root> status --porcelain=v1 -z` via
  `subprocess.run` in a `QRunnable`. Parse null-delimited output into a
  `dict[str, str]` (relative path → status code).
- Repo root detection: walk up from current path looking for `.git/` — cached
  per path in `ContextDetector` (F006).
- Overlay rendering: subclass `QStyledItemDelegate` for column 0; in
  `paint()`, after calling `super().paint()`, draw a small coloured badge in
  the top-right of the icon area using `painter.drawText()` or a small pixmap.
- `FastDirModel.data()` for `Qt.DecorationRole`: intercept and composite the
  overlay onto the base file icon.
- Branch label: a `QLabel` added to `PanelWidget`'s toolbar layout, updated
  from the same background worker result. Hidden when not in a Git repo.
- Overlay is opt-in: controlled by a `bool` flag in `UiPreferences`
  (`show_git_overlays`, default `False` to avoid cost on non-dev folders).

---

## FR010 — Export / Import All Settings

**Community signal:** TC forum ("Export / Import All Settings", 18 replies,
29,321 views); DC bug tracker item #736.

**Summary:** A built-in menu action that exports the entire application
configuration — preferences, tool paths, bookmarks, custom context modes,
column sets, key bindings — to a single portable JSON file. The same file can be
imported to restore the full configuration on another machine or after reinstall.

**Motivation:** Power users invest significant time configuring tool paths,
custom modes, and preferences. Today there is no safe way to back up or migrate
that configuration other than manually locating the INI file in `%APPDATA%`.
A first-class export/import flow removes that friction.

**Scope:**
- "Export Settings…" menu action: shows a save-file dialog, writes a
  `mpx-settings-export.json` file
- "Import Settings…" menu action: shows an open-file dialog, validates the
  file, prompts "Merge with current settings or replace entirely?", applies
- Export includes:
  - All `UiPreferences` fields
  - All `OpsSettingsDomain` fields (tool paths, backends, dispatch mode)
  - Bookmarks (F001, when implemented)
  - Named sessions (FR003, when implemented)
  - Custom context modes (`custom_modes.json` contents, F006)
  - Column sets / sort preferences (FR001, when implemented)
- Export excludes:
  - Current window/panel/tab session state (too machine-specific)
  - Absolute paths that would not exist on the target machine (flagged with
    a warning on import if the path does not exist)
- Version field in export JSON: `"schema_version": 1` for forward compatibility
- On import: unknown keys are ignored (forward-compat); missing keys use defaults

**Technical notes:**
- `SettingsManager.export_all() -> dict` — iterates all domain properties,
  collecting values into a nested dict keyed by domain and setting name.
- `SettingsManager.import_all(data: dict, merge: bool)` — for each known key,
  calls `set_value()`; unknown keys skipped; `merge=False` calls `reset_all()`
  first.
- JSON serialisation: `json.dumps(data, indent=2, ensure_ascii=False)` — human
  readable so users can version-control their config.
- Path validation on import: for every setting whose key ends in `_path` or
  `_exe`, check `Path(value).exists()` and collect warnings shown in a summary
  dialog before applying.
- `custom_modes.json` is included verbatim as a nested JSON value under
  `"custom_modes"` key in the export — no special handling needed.
- The export schema is the same format as `custom_modes.json` extended with
  top-level settings domains: `{"schema_version": 1, "ui": {...}, "ops": {...},
  "custom_modes": [...], "bookmarks": [...]}`.

---

## FR011 — Saved Searches as Bookmarks

**Community signal:** TC forum ("Feature request: Make saved searches available
in TC Bookmarks", 7 replies, 19,337 views).

**Summary:** A complex search query (root path, filename pattern, date range,
size range, content match) can be saved as a named bookmark. Opening the bookmark
re-runs the search and displays results as a virtual folder in the active tab.

**Dependency:** Requires F007 (Filter / Search Within Current Folder) to be
implemented first — specifically the search query model and result display.

**Scope:**
- "Save search as bookmark…" action in the search results toolbar
- Named entry stored alongside regular folder bookmarks (F001)
- Visually distinguished in the bookmarks list (search icon vs. folder icon)
- Opening a saved search bookmark: re-runs the query against the saved root path,
  displays results in the tab as a virtual folder (similar to FR002)
- Bookmark stores: root path, name pattern, optional date range, optional size
  range, optional content pattern, flags (recurse, case-sensitive, regex)

**Technical notes:**
- Search query serialised as a `SavedSearch` dataclass:
  `root: str, name_pattern: str, date_from: str | None, date_to: str | None,
  size_min: int | None, size_max: int | None, content: str | None,
  flags: int`.
- Stored in `BookmarksDomain` (F001) alongside `FolderBookmark` entries using
  a union type / discriminated field `"type": "folder" | "search"`.
- Re-running: instantiates the search engine from F007, injects the saved
  parameters, navigates the tab to a `search://` virtual path token.
- Address bar shows `search://<name>` when a saved search is active.

---

## FR012 — Video Thumbnail Previews

**Community signal:** TC forum #43727 ("Thumbnail Preview for Videos Files");
DC SourceForge reviews (2025).

**Summary:** A thumbnail view mode (toggle in View menu or toolbar) shows a grid
of file thumbnails. For video files, a representative frame is displayed using
either the Windows Shell thumbnail cache or `ffmpeg`/`ffprobe`. For images, the
file itself is decoded and scaled.

**Motivation:** Browsing a folder of 200 MKV files by name alone is opaque. Even
a single representative frame makes identification instant. This is standard in
Windows Explorer and every media manager.

**Scope:**
- Thumbnail view mode toggle (details ↔ thumbnails) in the View menu and a
  toolbar button
- Thumbnail grid: configurable tile size (64 / 128 / 256 px, persisted in
  `UiPreferences`)
- Sources (in priority order):
  1. Windows Shell thumbnail cache via `IShellItemImageFactory` (COM) — free,
     uses existing Windows-generated thumbs, works for videos, images, PDFs
  2. `ffmpeg -ss 00:00:05 -i <file> -vframes 1 -f image2pipe -` — fallback for
     files not in shell cache
  3. Default file type icon — fallback when neither source works
- Thumbnails generated in a background thread pool; placeholders shown until
  ready
- Thumbnail cache: in-memory LRU (max 500 entries); cleared on folder navigation

**Technical notes:**
- New `ThumbnailView(QWidget)` containing a `QListView` with a custom
  `QStyledItemDelegate` that paints scaled `QPixmap` thumbnails.
- `ExplorerTab` gains a `QStackedWidget` containing the existing `QTreeView`
  (details mode) and the new `ThumbnailView` (thumbnail mode).
- Windows Shell thumbnails via `win32com` / `ctypes`:
  `shell32.SHCreateItemFromParsingName()` → `IShellItemImageFactory`
  → `GetImage(size, flags)` → `HBITMAP` → `QPixmap.fromImage()`.
- `ffmpeg` fallback: `subprocess.run(['ffmpeg', '-ss', '5', '-i', path,
  '-vframes', '1', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'],
  capture_output=True)` → `QPixmap.loadFromData(result.stdout, 'PNG')`.
- Worker: `QRunnable` per file, posting result via `Signal(str, QPixmap)`
  (path, pixmap); `ThumbnailView` listens and updates the relevant tile.
- View mode persisted in `UiPreferences` as an enum:
  `ViewMode.DETAILS | ViewMode.THUMBNAILS`. Per-folder override via FR001.

---

## FR013 — EXIF Metadata Columns and Search

**Community signal:** TC forum ("Searching photos by Exif data in a human way",
50 replies, 37,618 views — the most-replied thread on TC suggestions page 1 at
time of research).

**Summary:** Optional file list columns for EXIF metadata: Date Taken, Camera
Make/Model, Resolution (WxH), GPS coordinates. Usable for sorting and (when
F007 search is available) for filtering.

**Dependency:** Column display is standalone. Search integration requires F007.

**Scope:**
- Opt-in columns added to the column chooser (right-click column header):
  - Date Taken (EXIF DateTimeOriginal)
  - Camera (Make + Model, concatenated)
  - Resolution (e.g., `4032 × 3024`)
  - GPS (decimal degrees, copyable to clipboard)
- Columns populated lazily: shown blank until the row is scrolled into view,
  then populated from a background EXIF read
- EXIF source: Python `Pillow` (`PIL.ExifTags`, `PIL.Image._getexif()`) — already
  a common indirect dependency; or `pyexiftool` for broader format support
- Columns visible only when at least one visible file has a recognised image
  extension (auto-hide in non-image folders, configurable)
- Search (F007 dependency): filter by date range, camera model substring,
  minimum resolution

**Technical notes:**
- `FastDirModel` custom columns: extend `columnCount()`, `headerData()`, and
  `data()` to support additional EXIF columns beyond the standard
  `QFileSystemModel` columns.
- Background EXIF loading: `ExifLoader(QRunnable)` reads EXIF for a single path,
  posts result to a `QObject` signal bridge. Model calls `dataChanged()` for
  the row once data arrives.
- EXIF cache: `dict[str, dict]` (path → exif dict), in-memory, max 2000 entries,
  LRU eviction.
- `Pillow` is not currently a dependency — add it, or use `ctypes` to call
  `WIC` (Windows Imaging Component) for zero-new-dependency EXIF access.
- Column state (visible/hidden, width) stored in `UiPreferences` alongside
  standard column state.

---

## Summary Table

| ID | Feature | Depends on | Complexity |
|---|---|---|---|
| FR001 | Per-folder persistent sort & view mode | — | Low |
| FR002 | Recent files virtual folder | — | Medium |
| FR003 | Named tab sessions | — | Medium |
| FR004 | Breadcrumb navigation bar | — | Medium |
| FR005 | Checkbox selection column | — | Low |
| FR006 | Tab color labels | — | Low |
| FR007 | Footer aggregate row (+ media duration) | ffprobe | Medium |
| FR008 | F2 rename: base name only selection | — | Very Low |
| FR009 | Git status overlay icons | F006 (Git mode) | Medium |
| FR010 | Export / Import all settings | — | Low–Medium |
| FR011 | Saved searches as bookmarks | F007 (search) | Medium |
| FR012 | Video thumbnail previews | ffmpeg / Shell COM | High |
| FR013 | EXIF metadata columns | Pillow or WIC | Medium |
