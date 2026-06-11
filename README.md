# Asset Master — Collectionize

**Turn any selection or collection into a linked collection asset — in one click.**

Made by [Blue Moon Virtual](https://www.bm-3d.de) for real production work on
furnished interior scenes, where the same furniture groups get reused across
dozens of project files shared over a synced drive.

---

## Why

Blender's Asset Browser is great — but turning *existing scene content* into
clean, linked, re-usable collection assets is a chore:

- mark a collection as an asset, and it still lives inside your working file
- write it to a separate file by hand, and you lose the instance in your scene
- existing tools are either too complicated or don't handle **collection
  instances** properly

Collectionize does the whole round trip in one click:

1. **Select** objects (or just one object of a group) and press
   **Selection** or **Collection**.
2. The objects are written to their own `<Name>.asset.blend` inside an
   `asset_library/` folder **next to your project file** — so the assets
   travel with the project on Dropbox/Google Drive/NAS.
3. The originals in your scene are replaced by a **linked collection
   instance** — visually nothing changes, but your file gets lighter and the
   asset is reusable everywhere.
4. A **rendered thumbnail** is generated automatically and the project library
   is **auto-registered** in Blender's Asset Browser. Open the project on any
   machine and the assets are just *there*.

## Features

- **Selection → Asset** and **Collection → Asset** buttons
- **Pivot control** — bottom-center of the bounding box (assets "stand on the
  floor"), or exactly at the **3D cursor**
- **Dependency-safe** — objects referenced by Curve / Mirror / Boolean /
  Lattice / Armature modifiers, constraints, hooks and curve bevels are
  detected, copied along, and remapped so the asset never deforms wrong
- **Real rendered thumbnails** (Workbench studio lighting, transparent
  background, 128–512 px)
- **Texture packing** (optional) — assets keep working on every machine
- **Replace existing** — re-export an asset under the same name and every
  placed instance updates
- **Asset Library panel** — browse, refresh, open, and delete the asset files
  of the current project without leaving the viewport
- **Safe by design** — originals are kept in a hidden backup collection until
  you decide to purge them

## Installation

**Blender 4.2+**

1. Download the latest release `.zip`
2. `Edit → Preferences → Add-ons → Install from Disk…`
3. Pick the zip, enable **Asset Master Collectionize**

## Usage

Open the **N-panel → Asset Master** tab:

| Control | What it does |
| --- | --- |
| **Selection** | Converts the selected objects into one collection asset |
| **Collection** | Converts the whole collection of the active object (or the active Outliner collection) |
| **3D Cursor as Pivot** | Pivot at the cursor instead of bounding-box bottom center |
| **Asset Library** subpanel | Manage the project's asset folder and files |

Preferences (`Edit → Preferences → Add-ons`):

- **Library Name Prefix** — e.g. `BM - ` to group your studio's libraries
- **Thumbnail Size** — 128 / 256 / 512 px
- **Pack Textures** — embed images into asset files (portable, but larger)

## FAQ

**Where do the asset files go?**
Into `asset_library/` next to your `.blend` (configurable). The folder is
auto-registered as an asset library named after the project.

**What happens to my original objects?**
They are moved to a hidden `AM_Collectionize_Backups` collection. Delete it
whenever you're confident.

**Does it work with curves, modifiers, armatures inside groups?**
Yes — referenced helper objects are included and remapped automatically.

## License

GPL-3.0-or-later — like Blender itself. See [LICENSE](LICENSE).

---

© Blue Moon Virtual — [bm-3d.de](https://www.bm-3d.de)
