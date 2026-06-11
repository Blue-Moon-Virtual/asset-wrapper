"""Build a release zip of the addon.

Usage:  python build_release.py
Creates dist/asset_master_collectionize-<version>.zip — installable via
Blender's "Install from Disk" (works both as legacy add-on and as an
extension thanks to the bundled blender_manifest.toml).
"""

import os
import re
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "asset_master_collectionize"
PACKAGE_DIR = os.path.join(ROOT, PACKAGE)
DIST = os.path.join(ROOT, "dist")

INCLUDE_EXTENSIONS = {".py", ".toml", ".md"}


def read_version():
    manifest = open(
        os.path.join(PACKAGE_DIR, "blender_manifest.toml"), encoding="utf-8"
    ).read()
    match = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.MULTILINE)
    if not match:
        raise SystemExit("version not found in blender_manifest.toml")
    return match.group(1)


def main():
    version = read_version()
    os.makedirs(DIST, exist_ok=True)
    zip_path = os.path.join(DIST, f"{PACKAGE}-{version}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for dirpath, dirnames, filenames in os.walk(PACKAGE_DIR):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() not in INCLUDE_EXTENSIONS:
                    continue
                full = os.path.join(dirpath, filename)
                relative = os.path.join(
                    PACKAGE, os.path.relpath(full, PACKAGE_DIR)
                )
                archive.write(full, relative)

    print(f"Built {zip_path}")


if __name__ == "__main__":
    main()
