"""Vidéo du voyant, lancée par anim.sh :

    blender.exe -b --factory-startup -P anim.py -- <variante> [preview|final]

Cycles ne rend que trois images : voyant éteint, ambre à 100 %, rouge à 100 %. La lumière s'additionne,
donc image(t) = éteint + niveau(t) × (allumé − éteint), calculée en linéaire puis passée par la même
gestion des couleurs qu'un rendu. C'est le résultat d'un rendu image par image, sans son scintillement
de bruit, et en quelques minutes sur le processeur. Écrit design/renders/anim/<variante>/%04d.png.
"""
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import cm_lib  # noqa: E402
import variants6  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
name = argv[0] if argv else "jj_fusion_face"
quality = argv[1] if len(argv) > 1 else "preview"

t0 = time.time()
out = HERE.parent / "renders" / "anim" / name
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
cm_lib.reset_scene()
variants6.BUILDERS[name]()
sc = bpy.context.scene
res, samples = ((768, 512), 32) if quality == "preview" else ((1500, 1000), 192)
sc.render.resolution_x, sc.render.resolution_y = res
if not name.endswith("_detail") and not sc.get("no_fit"):
    cm_lib.fit_camera()
cm_lib.render_settings(out / "passe.exr", res, samples)
sc.cycles.seed = 1
sc.render.image_settings.file_format = "OPEN_EXR"
sc.render.image_settings.color_depth = "32"
tl = variants6.timeline()


def passe(label, frame):
    """Rend une image de la séquence et la relit en linéaire."""
    sc.frame_set(frame)
    path = out / f"{label}.exr"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(str(path))
    px = np.empty(res[0] * res[1] * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    path.unlink()
    print(f"RENDERED {label} {time.time() - t0:.0f}s")
    return px


def image_de(state, level):
    return next(k for k, e in enumerate(tl, start=1) if e == (state, level))


eteint = passe("eteint", image_de("rouge", 0.0))
allume = {s: passe(s, image_de(s, 1.0)) - eteint for s in ("ambre", "rouge")}

frame = bpy.data.images.new("frame", res[0], res[1], alpha=False, float_buffer=True)
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.color_depth = "8"
done = {}
for f, (state, level) in enumerate(tl, start=1):
    path = out / f"{f:04d}.png"
    key = (state, round(level, 4))
    if key in done:
        shutil.copyfile(done[key], path)
        continue
    px = eteint + np.float32(level) * allume[state]
    px[3::4] = 1.0
    frame.pixels.foreach_set(px)
    frame.save_render(str(path), scene=sc)
    done[key] = path
print(f"RENDERED {name} {len(tl)} images, dont {len(done)} différentes, en {time.time() - t0:.0f}s")
