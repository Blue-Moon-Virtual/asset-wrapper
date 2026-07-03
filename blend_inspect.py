#!/usr/bin/env python3
"""Static .blend block-table + SDNA inspector. Reads only block headers and the
DNA1 block; never loads geometry/textures into memory. Safe for huge files."""
import sys, struct, collections

path = sys.argv[1]

with open(path, "rb") as f:
    header = f.read(12)
    assert header[:7] == b"BLENDER", "not a blend file (maybe compressed)"
    ptr_size = 8 if header[7:8] == b"-" else 4
    endian = "<" if header[8:9] == b"v" else ">"
    version = header[9:12].decode()
    bhead_size = 24 if ptr_size == 8 else 20

    by_code = collections.defaultdict(lambda: [0, 0])      # code -> [count, bytes]
    by_struct = collections.defaultdict(lambda: [0, 0])    # struct -> [count, bytes]
    raw_blocks = [0, 0]                                     # sdna==0: count, bytes
    big_blocks = []                                         # (bytes, code, sdna)
    dna_data = None
    total_blocks = 0

    while True:
        bh = f.read(bhead_size)
        if len(bh) < bhead_size:
            break
        code = bh[0:4].rstrip(b"\x00").decode("latin1")
        length = struct.unpack(endian + "i", bh[4:8])[0]
        # offset 8: old ptr (ptr_size). then SDNAnr, nr (int each)
        off = 8 + ptr_size
        sdna = struct.unpack(endian + "i", bh[off:off+4])[0]
        # nr = struct.unpack(endian + "i", bh[off+4:off+8])[0]
        if code == "ENDB":
            break
        total_blocks += 1
        by_code[code][0] += 1
        by_code[code][1] += length
        if sdna == 0:
            raw_blocks[0] += 1
            raw_blocks[1] += length
        if length >= 20 * 1024 * 1024:   # >=20 MB single block
            big_blocks.append((length, code, sdna))
        if code == "DNA1":
            pos = f.tell()
            dna_data = f.read(length)
        else:
            f.seek(length, 1)

# ---- parse SDNA to map sdna index -> struct type name ----
struct_names = {}
if dna_data:
    p = 0
    assert dna_data[p:p+4] == b"SDNA"; p += 4
    assert dna_data[p:p+4] == b"NAME"; p += 4
    n_names = struct.unpack(endian + "i", dna_data[p:p+4])[0]; p += 4
    for _ in range(n_names):
        e = dna_data.index(b"\x00", p); p = e + 1
    p = (p + 3) & ~3
    assert dna_data[p:p+4] == b"TYPE"; p += 4
    n_types = struct.unpack(endian + "i", dna_data[p:p+4])[0]; p += 4
    types = []
    for _ in range(n_types):
        e = dna_data.index(b"\x00", p); types.append(dna_data[p:e].decode("latin1")); p = e + 1
    p = (p + 3) & ~3
    assert dna_data[p:p+4] == b"TLEN"; p += 4
    p += n_types * 2
    p = (p + 3) & ~3
    assert dna_data[p:p+4] == b"STRC"; p += 4
    n_strc = struct.unpack(endian + "i", dna_data[p:p+4])[0]; p += 4
    for i in range(n_strc):
        type_idx = struct.unpack(endian + "h", dna_data[p:p+2])[0]; p += 2
        n_fields = struct.unpack(endian + "h", dna_data[p:p+2])[0]; p += 2
        p += n_fields * 4
        struct_names[i] = types[type_idx]

# re-walk? no — we need per-struct from first pass; redo aggregation by struct
# (we already have sdna per block only in first pass; redo lightweight)
with open(path, "rb") as f:
    f.seek(12)
    while True:
        bh = f.read(bhead_size)
        if len(bh) < bhead_size: break
        code = bh[0:4].rstrip(b"\x00").decode("latin1")
        length = struct.unpack(endian + "i", bh[4:8])[0]
        off = 8 + ptr_size
        sdna = struct.unpack(endian + "i", bh[off:off+4])[0]
        if code == "ENDB": break
        sname = struct_names.get(sdna, "?" if sdna else "(raw)")
        by_struct[sname][0] += 1
        by_struct[sname][1] += length
        f.seek(length, 1)

mb = lambda b: b / (1024*1024)
print(f"== {path}")
print(f"version=4.{version[1:]}  ptr={ptr_size}B  endian={endian}  total_blocks={total_blocks}")
print(f"raw(sdna=0) blocks: count={raw_blocks[0]:,}  bytes={mb(raw_blocks[1]):,.1f} MB")
print("\n-- top block CODES by total bytes --")
for code, (c, b) in sorted(by_code.items(), key=lambda x:-x[1][1])[:25]:
    print(f"  {code:6} count={c:>8,}  {mb(b):>10,.1f} MB")
print("\n-- top STRUCT types by total bytes --")
for s, (c, b) in sorted(by_struct.items(), key=lambda x:-x[1][1])[:30]:
    print(f"  {s:28} count={c:>8,}  {mb(b):>10,.1f} MB")
print("\n-- single blocks >= 20 MB --")
for b, code, sdna in sorted(big_blocks, reverse=True)[:30]:
    print(f"  {mb(b):>10,.1f} MB  code={code:6} struct={struct_names.get(sdna,'(raw)')}")
print(f"\n  (#blocks>=20MB = {len(big_blocks)})")
