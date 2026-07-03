import bpy, sys, math

out = []
def log(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)
    print(s, flush=True)

log("== loaded:", bpy.data.filepath)
log("blender runtime:", bpy.app.version_string)

# ---- missing files / libraries ----
missing = []
for img in bpy.data.images:
    if img.packed_file is None and img.filepath:
        try:
            import os
            p = bpy.path.abspath(img.filepath)
            if img.source in {'FILE','SEQUENCE','MOVIE'} and not os.path.exists(p):
                missing.append(("IMG", img.name, img.filepath))
        except Exception as e:
            missing.append(("IMG-ERR", img.name, str(e)))
for lib in bpy.data.libraries:
    missing.append(("LIB", lib.name, lib.filepath))
log("\n-- missing/external refs --")
if missing:
    for t,n,p in missing[:50]:
        log(f"  {t}: {n}  ->  {p}")
    log(f"  (total {len(missing)})")
else:
    log("  none")

# ---- datablock counts ----
log("\n-- datablock counts --")
for attr in ("objects","meshes","materials","images","node_groups","collections",
             "brushes","textures","worlds","cameras","lights"):
    log(f"  {attr:14} {len(getattr(bpy.data, attr)):>6}")

# ---- asset-marked datablocks ----
def n_assets(coll):
    return sum(1 for d in coll if getattr(d, 'asset_data', None) is not None)
log("\n-- marked as ASSET --")
for attr in ("objects","materials","meshes","node_groups","collections","worlds","images"):
    log(f"  {attr:14} {n_assets(getattr(bpy.data, attr)):>6}")

# ---- mesh validation (the key 'nasty geometry' test) ----
log("\n-- mesh.validate() errors --")
bad = []
big = []
for me in bpy.data.meshes:
    try:
        had_err = me.validate(verbose=False, clean_customdata=False)
        vN = len(me.vertices); pN = len(me.polygons)
        big.append((vN, pN, me.name))
        # NaN / inf check on a sample of verts
        nan = False
        for v in me.vertices:
            x,y,z = v.co
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                nan = True; break
        if had_err or nan:
            bad.append((me.name, had_err, nan, vN, pN))
    except Exception as e:
        bad.append((me.name, "EXC:"+str(e), False, -1, -1))
if bad:
    for name, err, nan, vN, pN in bad[:80]:
        log(f"  BAD mesh '{name}'  validate_fixed={err} nan_coords={nan} verts={vN} polys={pN}")
    log(f"  (total problem meshes: {len(bad)})")
else:
    log("  no mesh validation errors, no NaN coords")

# ---- heaviest meshes ----
log("\n-- top 15 heaviest meshes (verts) --")
for vN, pN, name in sorted(big, reverse=True)[:15]:
    log(f"  verts={vN:>9,}  polys={pN:>9,}  {name}")

# ---- heaviest packed images ----
log("\n-- top 15 packed images by size --")
imgs = []
for img in bpy.data.images:
    sz = 0
    if img.packed_file:
        sz = img.packed_file.size
    imgs.append((sz, img.name, tuple(img.size), img.depth))
for sz, name, dim, depth in sorted(imgs, reverse=True)[:15]:
    log(f"  {sz/1024/1024:>8.1f} MB  {dim} depth={depth}  {name}")

log("\n== DONE ==")
