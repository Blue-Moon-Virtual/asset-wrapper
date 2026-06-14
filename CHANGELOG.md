# Changelog

## 0.7.0 — 2026-06-14

### Added
- **Edit Asset** — a button in the Asset Library panel opens the selected asset
  in a separate Blender window for editing. The asset's collection is linked
  into view automatically, and a one-click **Render Thumbnail & Save** button
  refreshes the preview. Because assets are linked, saved edits apply to every
  project that uses the asset.
- **Reload Asset Libraries** (library ▾ menu) — pulls in edits made to asset
  files without reopening the project.

## 0.6.0 — 2026-06-14

### Added
- **Project tag** (per-scene). Set a Project name in the sidebar and new assets
  are saved as `<Project>_<name>` and filed under a `<Project>` catalogue in the
  Asset Browser. This stops several projects that share one `asset_library`
  folder from colliding on generic names (e.g. two "BED"s overwriting each
  other) — the root cause of cross-project asset mixing.
- Auto-managed `blender_assets.cats.txt`: catalogues are created on demand.

### Notes
- Leave the Project field empty for the previous behaviour (no prefix, no
  catalogue).

## 0.5.5 — 2026-06-12

### Added
- **Rename assets** — a pencil button in the Asset Library panel renames the
  selected asset: its `.blend` file, the collection inside it (so the Asset
  Browser updates), and any linked instances placed in the current scene, all
  in one step. The rendered thumbnail and asset metadata are preserved.
- **Batch rename** — from the library ▾ menu: find & replace, add prefix, or
  add suffix across every asset in the library, with a live preview of what
  will change.

### Notes
- Renames release the affected libraries first so the files can be rewritten
  reliably while still linked in the open scene, and clean up Blender's
  `.blend1` backups. Linked instances in *other* already-saved project files
  still reference the old name and would need re-pointing there.

## 0.5.4 — 2026-06-12

### Fixed
- **Add-on installed but did not appear in Preferences.** Blender builds the
  Add-ons list by parsing `bl_info` *without running the file* (AST), so the
  `"version": ADDON_VERSION` introduced in 0.5.3 was a non-literal it could not
  read (`malformed node or string`), and the add-on was skipped from the list.
  `bl_info` values are all plain literals again, and the version lives only in
  `bl_info` (single source of truth). Verified via `addon_utils.modules()` —
  the same discovery path the Preferences UI uses.
- Dropped `blender_manifest.toml` entirely: Asset Wrapper is a classic legacy
  add-on (works with the in-app updater and installs everywhere). An extension
  build, if ever needed for extensions.blender.org, is a separate concern.

## 0.5.3 — 2026-06-12

### Fixed
- **Manual install failed on Blender 4.2+/5.x** with `name 'bl_info' is not
  defined`. The release zip shipped `blender_manifest.toml`, so Blender treated
  it as an extension — and extensions strip `bl_info`, which `register()`
  referenced. The distributed zip is now a plain legacy add-on (no manifest),
  and `register()` no longer touches `bl_info` (uses `ADDON_VERSION`). Verified
  installing cleanly via Blender's own install operator on a fresh profile.

### Changed
- Rewrote the README: concise, clearer description, less studio-specific.

## 0.5.2 — 2026-06-12

### Fixed
- Updater now installs the **attached release .zip** instead of the GitHub
  source zipball. Because the addon lives in the `asset_wrapper/` subfolder of
  the repo, the zipball was not directly installable ("No __init__ file found
  in new source"); the attached zip built by `build_release.py` installs
  cleanly. Verified end-to-end (0.5.0 → 0.5.2 install) headless.

## 0.5.1 — 2026-06-12

### Changed
- Replaced the in-house updater with the established **CGCookie
  blender-addon-updater**, configured for GitHub releases of
  `Blue-Moon-Virtual/asset-wrapper`. Preferences now expose check-now,
  auto-check intervals, and install/revert; the sidebar shows an
  "update ready" notice when a newer release is found.
- First public release on GitHub.

## 0.5.0 — 2026-06-12

### Changed
- **Renamed to "Asset Wrapper"** (was "Asset Master Collectionize"). The
  Python package, panels, operators, and the auto-created backup collection
  use the new name. Backup collections from older versions are still
  recognized.

### Added
- **Built-in updater** in the add-on preferences: checks GitHub releases for a
  newer version and installs it in one click (threaded, non-blocking).
  Configurable repository and optional check-on-startup.
- Library actions consolidated into a single dropdown menu, plus a
  "Set Custom Folder" / "Use Default Folder" pair.

### UI
- Minimalist redesign: the main panel is just the two wrap buttons + pivot
  toggle; the Asset Library subpanel drops the stacked status lines and
  management buttons in favor of one action menu and the asset list.

## 0.4.0 — 2026-06-11

### Fixed
- **Broken visuals in instanced assets**: objects referenced by modifiers
  (Curve, Mirror, Boolean, Lattice, Armature, hooks, Geometry Nodes inputs),
  constraints, and curve bevel/taper settings are now detected, copied into
  the asset, and remapped. Previously they were pulled into the asset file at
  their old world positions, deforming the asset completely wrong.
- Parent hierarchies are rebased parents-first, fixing offset children.
- Pivot and thumbnail framing now expand nested collection instances instead
  of treating them as points.
- Viewport-hidden helper objects no longer show up in thumbnails.
- Asset file writes retry briefly if a background post-process still holds
  the file.

### Added
- Add-on preferences: library name prefix, thumbnail size (128/256/512),
  texture packing.
- Optional packing of external textures into asset files (portable assets).
- Operator report lists helper objects that were pulled into an asset.

### Changed
- UI polish across both panels; branding footer.
- Library naming prefix is configurable (was hardcoded).

## 0.3.0

- Asset Library manager panel: list/refresh/open/delete asset files,
  disconnect or delete the library folder.
- Replace-existing export mode, linked-library reload on re-export.
- Material duplication into asset files, alignment safety check.

## 0.2.0

- Two-button workflow (Selection / Collection), 3D-cursor pivot option,
  bounding-box bottom-center default pivot.
- Per-project `asset_library/` folder with auto-registration on file load.
- Crash-free synchronous thumbnail rendering; previews persisted into asset
  files via a background helper.

## 0.1.0

- Initial prototype.
