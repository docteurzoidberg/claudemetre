"""Bibliothèque de la maquette Claudemètre : matériaux et composants aux cotes
réelles (estimées tant que les pièces ne sont pas mesurées).

Repère : le mur (planche PC) est le plan y = 0, face avant vers -Y ; Z vers le
haut ; unités en mètres, les helpers prennent des millimètres.
"""
import json
import math
import struct
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
DIALS = DESIGN / "dials"
TM1637 = DESIGN / "references" / "tm1637"
MM = 0.001
SO45 = json.loads((DIALS / "dial_so45_spec.json").read_text())

_font_cache = {}
_mat_cache = {}


# ---------------------------------------------------------------- scène

def reset_scene():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.lights,
                 bpy.data.cameras, bpy.data.materials):
        for item in list(coll):
            coll.remove(item)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    _font_cache.clear()
    _mat_cache.clear()
    DEVICE.clear()
    return sc


def link(ob, parent=None):
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    ob.location = Vector(loc) * MM
    ob.rotation_euler = [math.radians(a) for a in rot]
    return link(ob, parent)


DEVICE = []


def device(name, loc=(0, 0, 0)):
    """Racine de l'objet maquetté : c'est elle que le cadrage automatique vise."""
    root = empty(name, loc)
    DEVICE[:] = [root]
    return root


def fit_camera(fill=0.86, exclude=("usb_cable",)):
    """Recule ou avance la caméra (même direction) pour que l'objet remplisse
    `fill` du cadre ; met la mise au point au centre de l'objet. Les objets
    pendants (câble) ne comptent pas dans le cadrage."""
    sc = bpy.context.scene
    cam = sc.camera
    if not DEVICE or cam is None:
        return
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in DEVICE[0].children_recursive:
        if ob.type not in {"MESH", "CURVE", "FONT"} or any(ob.name.startswith(e) for e in exclude):
            continue
        if ob.type == "CURVE":
            # La boîte englobante d'une courbe n'est pas fiable en arrière-plan.
            for sp in ob.data.splines:
                cos = [bp.co for bp in sp.bezier_points] or [p.co.xyz for p in sp.points]
                pts += [ob.matrix_world @ Vector(c) for c in cos]
            continue
        ev = ob.evaluated_get(dg)
        pts += [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    if not pts:
        return
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2
    flat = [c for p in pts for c in p]
    loc, _ = cam.camera_fit_coords(dg, flat)
    cam.location = center + (Vector(loc) - center) / fill
    print(f"FIT center={tuple(round(c, 3) for c in center)} size={tuple(round(c, 3) for c in hi - lo)} "
          f"cam={tuple(round(c, 3) for c in cam.location)}")
    focus = bpy.data.objects.get("focus")
    if focus is not None:
        focus.location = center


def mesh_obj(name, verts_mm, faces, mat, parent=None, smooth=False, sharp_deg=35):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) * MM for v in verts_mm], [], faces)
    me.validate()
    me.update()
    if smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    return link(ob, parent)


def place(ob, loc_mm=(0, 0, 0), rot_deg=(0, 0, 0)):
    ob.location = Vector(loc_mm) * MM
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return ob


# ---------------------------------------------------------------- géométrie

def lathe(name, profile, mat, parent=None, seg=64, axis="Y", sharp_deg=35, close_ends=True):
    """Révolution d'un profil [(r, h) en mm] autour de l'axe (Y par défaut,
    l'objet regarde alors vers -Y si h diminue vers l'avant)."""
    verts, faces = [], []
    n = len(profile)
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        for r, h in profile:
            if axis == "Y":
                verts.append((r * ca, h, r * sa))
            else:  # Z
                verts.append((r * ca, r * sa, h))
    for i in range(seg):
        j = (i + 1) % seg
        for k in range(n - 1):
            a0, a1 = i * n + k, i * n + k + 1
            b0, b1 = j * n + k, j * n + k + 1
            if profile[k][0] == 0 and profile[k + 1][0] == 0:
                continue
            faces.append((a0, b0, b1, a1))
    ob = mesh_obj(name, verts, faces, mat, parent, smooth=True, sharp_deg=sharp_deg)
    # Fusionne les sommets confondus sur l'axe (r = 0).
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    ob.data.set_sharp_from_angle(angle=math.radians(sharp_deg))
    return ob


def box(name, size_mm, mat, parent=None, loc=(0, 0, 0), bevel_mm=0.0, bevel_seg=3, bake=False):
    """Pavé. bake=True met la position dans les sommets, pour que deux pièces
    du même matériau procédural n'aient pas le même motif."""
    sx, sy, sz = (s / 2 for s in size_mm)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    if bake:
        v = [(x + loc[0], y + loc[1], z + loc[2]) for x, y, z in v]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, v, f, mat, parent)
    if not bake:
        place(ob, loc)
    if bevel_mm > 0:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel_mm * MM
        m.segments = bevel_seg
        m.limit_method = "ANGLE"
        m.harden_normals = True
        ob.data.shade_smooth()
    return ob


def rod(name, pts_mm, radius_mm, mat, parent=None, smooth=False, res=6):
    """Fil rigide (laiton, câble…) passant par des points en mm."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius_mm * MM
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    if smooth:
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(pts_mm) - 1)
        for bp, p in zip(sp.bezier_points, pts_mm):
            bp.co = Vector(p) * MM
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts_mm) - 1)
        for pt, p in zip(sp.points, pts_mm):
            pt.co = (*(Vector(p) * MM), 1.0)
    ob = bpy.data.objects.new(name, cu)
    cu.materials.append(mat)
    return link(ob, parent)


# ---------------------------------------------------------------- matériaux

def _new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    return m, nt, bsdf


def mat_basic(name, color, metallic=0.0, rough=0.5, coat=0.0, emission=None, strength=0.0):
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    _mat_cache[name] = m
    return m


def _noise(nt, scale, detail=6.0, rough=0.6, stretch=(1, 1, 1), coord="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = stretch
    nt.links.new(tc.outputs[coord], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = rough
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    return nz, mp


def _ramp(nt, src, c0, c1, p0=0.3, p1=0.7):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position, r.color_ramp.elements[0].color = p0, (*c0, 1)
    r.color_ramp.elements[1].position, r.color_ramp.elements[1].color = p1, (*c1, 1)
    nt.links.new(src, r.inputs["Fac"])
    return r


def mat_metal(name, color, rough=0.28, tarnish=0.35, brushed_axis=None, tarnish_color=None):
    """Laiton / cuivre / acier : variation de rugosité et léger ternissement."""
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    b.inputs["Metallic"].default_value = 1.0
    stretch = {None: (1, 1, 1), "X": (0.02, 1, 1), "Z": (1, 1, 0.02)}[brushed_axis]
    if brushed_axis:
        stretch = {"X": (0.004, 1, 1), "Z": (1, 1, 0.004)}[brushed_axis]
    nz, _ = _noise(nt, 3000 if brushed_axis else 120, 8, 0.65, stretch)
    tc = tarnish_color or tuple(c * 0.45 for c in color)
    blot, _ = _noise(nt, 60, 4, 0.5)
    ramp = _ramp(nt, blot.outputs["Fac"], tc, color, 0.3, 0.6)
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["Factor"].default_value = 0.5 * tarnish
    col.inputs["A"].default_value = (*color, 1)
    nt.links.new(ramp.outputs["Color"], col.inputs["B"])
    nt.links.new(col.outputs["Result"], b.inputs["Base Color"])
    spread = (0.92, 1.08) if brushed_axis else (0.8, 1.25)
    rr = _ramp(nt, nz.outputs["Fac"], (rough * spread[0],) * 3, (rough * spread[1],) * 3, 0.35, 0.65)
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.015 if brushed_axis else 0.02
    bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    _mat_cache[name] = m
    return m


def mat_wood(name, dark, light, grain="X", scale=1.0, rough=0.5, coat=0.15, contrast=1.0, offset=(0, 0, 0)):
    """Bois procédural : stries étirées dans le sens du fil, figure large, pores."""
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    along = {"X": (0.035, 1, 1), "Z": (1, 1, 0.035)}[grain]
    streak, mp1 = _noise(nt, 90 * scale, 14, 0.66, along)
    mp1.inputs["Location"].default_value = offset
    streak.inputs["Distortion"].default_value = 0.15
    figure, mp2 = _noise(nt, 7 * scale, 4, 0.5, tuple(0.25 if a < 1 else 1 for a in along))
    mp2.inputs["Location"].default_value = offset
    pores, _ = _noise(nt, 420 * scale, 3, 0.5, tuple(0.02 if a < 1 else 1 for a in along))

    def madd(a, k, c):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "MULTIPLY_ADD"
        nt.links.new(a, n.inputs[0])
        n.inputs[1].default_value = k
        if isinstance(c, float):
            n.inputs[2].default_value = c
        else:
            nt.links.new(c, n.inputs[2])
        return n.outputs[0]

    f = madd(streak.outputs["Fac"], 0.6, 0.0)
    f = madd(figure.outputs["Fac"], 0.25, f)
    f = madd(pores.outputs["Fac"], 0.15, f)
    w = 0.13 / contrast
    col = _ramp(nt, f, dark, light, 0.5 - w, 0.5 + w)
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.3
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(pores.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    _mat_cache[name] = m
    return m


def mat_pla(name, color, silk=False, layer_axis="Y", rough=0.5):
    """PLA imprimé : lignes de couches de 0,2 mm le long de layer_axis et
    texture de plateau PEI sur les faces posées à plat. silk = PLA métallisé."""
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.3 if silk else rough
    if silk:
        b.inputs["Metallic"].default_value = 0.65
        b.inputs["Coat Weight"].default_value = 0.3
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = layer_axis
    wave.inputs["Scale"].default_value = 1570.0
    wave.inputs["Distortion"].default_value = 0.0
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    pei, _ = _noise(nt, 2600, 2, 0.5)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(wave.outputs["Fac"], mix.inputs["A"])
    nt.links.new(pei.outputs["Fac"], mix.inputs["B"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.00004
    nt.links.new(mix.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    _mat_cache[name] = m
    return m


def mat_worn(name, color, wear_color, rough=0.55, wear_metal=False, amount=1.0, layer_axis=None):
    """Surface peinte ou imprimée usée sur les arêtes (brossage à sec, peinture
    écaillée) : masque d'arête calculé par le nœud Bevel de Cycles."""
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    bev = nt.nodes.new("ShaderNodeBevel")
    bev.inputs["Radius"].default_value = 0.0015
    bev.samples = 8
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(bev.outputs["Normal"], dot.inputs[0])
    nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    edge = nt.nodes.new("ShaderNodeMath")
    edge.operation = "SUBTRACT"
    edge.inputs[0].default_value = 1.0
    nt.links.new(dot.outputs["Value"], edge.inputs[1])
    grit, _ = _noise(nt, 260, 6, 0.7)
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(edge.outputs[0], mul.inputs[0])
    nt.links.new(grit.outputs["Fac"], mul.inputs[1])
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.use_clamp = True
    k.inputs[1].default_value = 40.0 * amount
    nt.links.new(mul.outputs[0], k.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*color, 1)
    mix.inputs["B"].default_value = (*wear_color, 1)
    nt.links.new(k.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if wear_metal:
        nt.links.new(k.outputs[0], b.inputs["Metallic"])
    if layer_axis:
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = layer_axis
        wave.inputs["Scale"].default_value = 1570.0
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.2
        bump.inputs["Distance"].default_value = 0.00004
        nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    _mat_cache[name] = m
    return m


def mat_steel_raw(name="steel_raw"):
    """Tôle d'acier noircie (bleuissage à froid) puis vernie : taches sombres,
    reflets bleutés, calamine."""
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    b.inputs["Metallic"].default_value = 1.0
    blot, _ = _noise(nt, 18, 6, 0.55)
    col = _ramp(nt, blot.outputs["Fac"], (0.075, 0.075, 0.08), (0.17, 0.16, 0.15), 0.4, 0.62)
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    fine, _ = _noise(nt, 400, 6, 0.6)
    rr = _ramp(nt, fine.outputs["Fac"], (0.32,) * 3, (0.55,) * 3, 0.3, 0.7)
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    b.inputs["Coat Weight"].default_value = 0.4
    b.inputs["Coat Roughness"].default_value = 0.2
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    _mat_cache[name] = m
    return m


def mat_glass(name="glass"):
    if name in _mat_cache:
        return _mat_cache[name]
    m, nt, b = _new_mat(name)
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Roughness"].default_value = 0.0
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.49
    _mat_cache[name] = m
    return m


def materials():
    """Palette commune de la maquette."""
    return {
        "brass": mat_metal("brass", (0.80, 0.56, 0.22), rough=0.25, tarnish=0.25),
        "brass_old": mat_metal("brass_old", (0.72, 0.50, 0.20), rough=0.35, tarnish=0.6),
        "steel": mat_basic("steel", (0.62, 0.62, 0.64), metallic=1.0, rough=0.38),
        "black": mat_basic("black_plastic", (0.012, 0.012, 0.012), rough=0.38),
        "black_gloss": mat_basic("black_gloss", (0.005, 0.005, 0.005), rough=0.08, coat=0.6),
        "pcb": mat_basic("pcb_black", (0.015, 0.02, 0.02), rough=0.35, coat=0.3),
        "solder": mat_metal("solder", (0.75, 0.75, 0.76), rough=0.18, tarnish=0.0),
        "seg_off": mat_basic("seg_off", (0.014, 0.012, 0.010), rough=0.6),
        "seg_on": mat_basic("seg_on", (1.0, 0.30, 0.02), rough=0.4, emission=(1.0, 0.28, 0.015), strength=2.4),
        "engrave": mat_basic("engrave", (0.012, 0.008, 0.006), rough=0.85),
        "glass": mat_glass(),
        "cable": mat_basic("cable", (0.02, 0.02, 0.02), rough=0.55),
        "oak": mat_wood("oak", (0.16, 0.085, 0.035), (0.42, 0.26, 0.12), grain="Z", rough=0.6, coat=0.05,
                        scale=0.8, contrast=1.4),
        "steel_raw": mat_steel_raw(),
        "black_oxide": mat_basic("black_oxide", (0.02, 0.02, 0.022), metallic=1.0, rough=0.35),
        "smd_cap": mat_basic("smd_cap", (0.42, 0.28, 0.12), rough=0.5),
    }


# ---------------------------------------------------------------- composants

SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": "",
}


def _stl(path):
    """Sommets (mm) et triangles d'un STL binaire, sommets confondus fusionnés."""
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 80)[0]
    rec = np.frombuffer(data, dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count=n, offset=84)
    verts, idx = np.unique(rec["v"].reshape(-1, 3).round(4), axis=0, return_inverse=True)
    return verts.tolist(), idx.reshape(-1, 3).tolist()


def tm1637(name, M, text_="14:32", loc=(0, 0, 0), parent=None, color="seg_on", module=True):
    """Module TM1637 0,56" du commerce, d'après le STEP GrabCAD converti par
    design/references/tm1637/step_to_mesh.py : segments à leur forme exacte,
    allumés selon text_ ; module=False ne garde que l'afficheur (sans PCB ni
    composants). Origine au centre de la face avant, qui regarde vers -Y."""
    root = empty(name, loc, parent)
    parts = {"face": "black_gloss", "corps": "black", "pcb": "pcb", "noir": "black", "metal": "solder",
             "composants": "smd_cap"}
    for part, mat in parts.items():
        if module or part in ("face", "corps"):
            verts, faces = _stl(TM1637 / "mesh" / f"{part}.stl")
            mesh_obj(f"{name}_{part}", verts, faces, M[mat], root, smooth=True)
    spec = json.loads((TM1637 / "tm1637_segments.json").read_text())
    lit = [SEGMENTS.get(c, "") for c in text_ if c != ":"]
    polys = [(p, s in lit[k]) for k, d in enumerate(spec["digits"]) for s, p in d.items()]
    polys += [(p, ":" in text_) for p in spec["colon"]] + [(p, False) for p in spec["dp"]]
    y = spec["depth"] - 0.02    # juste devant le fond des alvéoles
    for on in (True, False):
        verts, faces = [], []
        for p, state in polys:
            if state == on:
                faces.append(tuple(range(len(verts), len(verts) + len(p))))
                verts += [(x, y, z) for x, z in p]
        if faces:
            mesh_obj(f"{name}_{'lit' if on else 'unlit'}", verts, faces, M[color if on else "seg_off"], root)
    return root


LAMP_GLOW = {"ambre": (1.0, 0.30, 0.0), "rouge": (1.0, 0.03, 0.01)}


def _outward(ob, sharp_deg=30):
    """Normales vers l'extérieur : le masque d'usure de mat_worn en dépend."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    ob.data.set_sharp_from_angle(angle=math.radians(sharp_deg))
    return ob


def _ring(name, profile, mat, parent, seg=64, sharp_deg=30, loc=(0, 0, 0)):
    """Pièce de révolution autour de Y, profil (r, y) fermé automatiquement."""
    ob = lathe(name, list(profile) + [profile[0]], mat, parent, seg=seg, sharp_deg=sharp_deg)
    ob.location = Vector(loc) * MM
    return _outward(ob, sharp_deg)


# ---------------------------------------------------------------- décor

def wall(M, width=900, height=600):
    """Planche murale du PC : lames de chêne verticales, plan y=0."""
    root = empty("wall")
    lame = 140.0
    n = int(width // lame) + 1
    for k in range(n):
        x = -width / 2 + lame * (k + 0.5)
        box(f"plank{k}", (lame - 0.6, 20.0, height), M["oak"], root, (x, 10.0, 0),
            bevel_mm=1.0, bake=True)
    return root


def lights_and_world(strength=1.0, warm=True):
    sc = bpy.context.scene
    world = bpy.data.worlds.new("world")
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
    bg.inputs["Strength"].default_value = 0.6
    sc.world = world

    def area(name, loc, target, power, size, color):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power * strength
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
        ld.color = color
        ob = bpy.data.objects.new(name, ld)
        link(ob)
        ob.location = Vector(loc)
        d = Vector(target) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return ob

    key = (1.0, 0.86, 0.70) if warm else (1, 1, 1)
    area("key", (-0.45, -0.55, 0.45), (0, 0, 0), 26, (0.5, 0.35), key)
    area("fill", (0.6, -0.5, 0.05), (0, 0, 0), 5, (0.6, 0.6), (0.85, 0.9, 1.0))
    area("graze", (0.0, -0.08, 0.6), (0, 0, -0.1), 12, (0.9, 0.08), key)


def camera(loc, target, lens=70, fstop=5.6, focus=None):
    for name in ("cam", "focus"):
        old = bpy.data.objects.get(name)
        if old is not None:
            bpy.data.objects.remove(old)
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    ob = bpy.data.objects.new("cam", cd)
    link(ob)
    ob.location = Vector(loc)
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    f = bpy.data.objects.new("focus", None)
    link(f)
    f.location = Vector(focus or target)
    cd.dof.focus_object = f
    bpy.context.scene.camera = ob
    return ob


def render_settings(path, res=(1536, 1024), samples=96):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(path)
    sc.view_settings.exposure = -0.25
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
