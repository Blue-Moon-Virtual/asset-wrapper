# Changelog

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
