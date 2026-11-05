"""Point d'entrée des rendus, lancé par Blender en arrière-plan :

    blender.exe -b --factory-startup -P render.py -- <variante> [preview|final]

Écrit design/renders/<variante>.png (et .blend pour l'ouvrir dans Blender).
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402

import cm_lib  # noqa: E402
import variants6  # noqa: E402

BUILDERS = variants6.BUILDERS

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
name = argv[0] if argv else "jj_fusion"
quality = argv[1] if len(argv) > 1 else "preview"

out_dir = HERE.parent / "renders" / ("" if quality == "final" else "preview")
out_dir.mkdir(parents=True, exist_ok=True)

t0 = time.time()
cm_lib.reset_scene()
BUILDERS[name]()
res, samples = ((768, 512), 24) if quality == "preview" else ((1500, 1000), 128)
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = res
if not name.endswith("_detail") and not bpy.context.scene.get("no_fit"):
    cm_lib.fit_camera()
if quality == "zoom":
    # zoom x,z,distance (mm) : gros plan de contrôle, caméra de face.
    from mathutils import Vector
    x, z, dist = (float(v) for v in argv[2].split(","))
    cam = bpy.context.scene.camera
    cam.location = Vector((x, -dist, z)) * cm_lib.MM
    cam.rotation_euler = (Vector((x, 0, z)) * cm_lib.MM - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.use_dof = False
    name = f"{name}_zoom"
    res, samples = (1200, 800), 32
cm_lib.render_settings(out_dir / f"{name}.png", res, samples)
bpy.ops.render.render(write_still=True)
if quality == "final":
    # Scène seule, sans l'interface (elle garde le dossier de l'explorateur de fichiers), et sortie
    # en relatif : aucun chemin du poste dans le .blend. Le tampon du chemin est de taille fixe : le
    # remplir d'abord, sinon la fin de l'ancien chemin reste derrière le nouveau.
    sc = bpy.context.scene
    sc.render.filepath = " " * 1023
    sc.render.filepath = f"//../../renders/{name}.png"
    bpy.data.libraries.write(str(HERE / "scenes" / f"{name}.blend"), {sc}, path_remap="NONE", compress=True)
print(f"RENDERED {name} {quality} in {time.time() - t0:.1f}s")
