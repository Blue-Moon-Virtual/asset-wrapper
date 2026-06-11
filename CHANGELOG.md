# Changelog

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
