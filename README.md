# Asset Wrapper

Turn anything in your scene into a linked, reusable collection asset — one click, thumbnail included.

Blender's Asset Browser is great at *placing* assets and clumsy at *making* them from scenes you've already built. Asset Wrapper closes that gap: pick objects or a collection, click once, and they become a `.blend` collection asset with a rendered thumbnail — while the originals in your scene are swapped for a linked instance. Your file gets lighter, the asset is reusable everywhere, and nothing moves a millimetre.

## How it works

1. Select some objects (or just one object of a collection).
2. Click **Selection** or **Collection** in the sidebar.
3. Asset Wrapper writes a `<name>.asset.blend` into a per-project `asset_library/` folder, registers it with the Asset Browser, renders a thumbnail, and replaces your originals with a linked instance. The originals are tucked into a hidden backup collection — never deleted.

## Features

- **Selection → asset** and **collection → asset**, one click each
- **Pivot** at the bounding-box floor or exactly on the 3D cursor
- **Dependency-safe** — curve / mirror / boolean / lattice / armature targets, constraints, hooks and curve bevels travel with the asset, so it never comes in deformed
- **Rendered thumbnails**, not flat icons
- **Per-project library** that travels with the `.blend` (great over shared drives)
- **Texture packing** (optional) for fully portable assets
- **Re-wrap** under the same name to update every placed instance at once
- **In-viewport library browser** — list, open, and clean up project assets
- **One-click updates** from the add-on preferences

## Install

Blender 4.2+.

1. Download **`asset_wrapper-x.y.z.zip`** from the [latest release](https://github.com/Blue-Moon-Virtual/asset-wrapper/releases/latest) — the attached zip, **not** the green "Source code" archive.
2. `Edit → Preferences → Add-ons → Install from Disk…` and pick the zip.
3. Enable **Asset Wrapper**. It appears in the sidebar (`N`) under the **Asset Wrapper** tab.

## Usage

| Control | What it does |
| --- | --- |
| **Selection** | Wrap the selected objects into one collection asset |
| **Collection** | Wrap the whole collection of the active object (or the active Outliner collection) |
| **3D Cursor as Pivot** | Use the cursor as the asset pivot instead of the bounding-box floor |
| **Asset Library** ▾ menu | Set a custom folder, open it, refresh, disconnect, or delete |

Preferences let you set a library-name prefix, thumbnail resolution (128 / 256 / 512), texture packing, and update checking.

## Updates

`Edit → Preferences → Add-ons → Asset Wrapper → Check for Updates`. Updates download and install in place; restart Blender to finish.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). Built on the [CGCookie blender-addon-updater](https://github.com/CGCookie/blender-addon-updater).

---

An open-source Blender add-on by [Blue Moon Virtual](https://www.bm-3d.de).
