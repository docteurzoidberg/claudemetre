"""Exporte ce que la scène `jj_fusion` ajoute au modèle Fusion (aiguilles, équipage mobile, vitres, fiche,
câble, vis du témoin), pour la page éclatée :

    blender.exe -b scenes/jj_fusion.blend -P export_web.py -- <dossier de sortie>

Écrit extras.bin et extras.json, au même format que `design/fusion/scripts/export_blender.py` et dans son
repère (mm, origine sur la façade). `maquette/pack.py` les lit avec l'export de Fusion.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

out = Path(sys.argv[sys.argv.index("--") + 1])
PREFIXES = ("aiguille_", "lp16_fiche_", "usb_cable", "temoin_vis")
SO45 = ("_moyeu", "_pivot", "_etrier", "_vitre", "_zero", "_fente")
DEPTH = 40.0

dg = bpy.context.evaluated_depsgraph_get()
items, pos, nor, idx, base, i0 = [], [], [], [], 0, 0
for ob in bpy.data.objects:
    n = ob.name
    if ob.type not in {"MESH", "CURVE"} or not (n.startswith(PREFIXES) or (n.startswith("so45_") and any(s in n for s in SO45))):
        continue
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    corners = np.empty(len(me.corner_normals) * 3, dtype=np.float32)
    me.corner_normals.foreach_get("vector", corners)
    tri = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", tri)
    loops = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    m = np.array(ob.matrix_world)
    p = co.reshape(-1, 3)[tri] @ m[:3, :3].T + m[:3, 3]
    v = corners.reshape(-1, 3)[loops] @ np.linalg.inv(m[:3, :3])
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
    p = p * 1000 + (0, DEPTH, 0)
    pos.append(p.astype(np.float32))
    nor.append(v.astype(np.float32))
    idx.append(np.arange(base, base + len(p), dtype=np.uint32))
    items.append(dict(occ="extra", body=n, part="extra", app=None, rgb=None, v0=base, nv=len(p), i0=i0, ni=len(p),
                      bbox=[round(float(a), 3) for a in (*p.min(axis=0), *p.max(axis=0))]))
    base += len(p)
    i0 += len(p)
    ob.evaluated_get(dg).to_mesh_clear()

out.mkdir(parents=True, exist_ok=True)
with open(out / "extras.bin", "wb") as f:
    np.concatenate(pos).tofile(f)
    np.concatenate(nor).tofile(f)
    np.concatenate(idx).tofile(f)
(out / "extras.json").write_text(json.dumps(dict(nv=base, ni=i0, corps=items), ensure_ascii=False), encoding="utf-8")
print(f"EXPORTED {len(items)} objets, {i0 // 3} triangles")
