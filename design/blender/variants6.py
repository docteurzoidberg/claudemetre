"""La maquette à jour, d'après l'assemblage Fusion `claudometre`.

Plus de formes approchées : la géométrie vient du design Fusion, exporté corps par corps
(`design/fusion/scripts/export_blender.py`, fichiers dans `design/fusion/blender/`). Décor, lumière et
matériaux viennent de `cm_lib.py`. Ce que le modèle n'a pas est ajouté ici : aiguilles, équipage
mobile, vitres et vis du zéro des SO-45, fiche LP-16 et câble.

  jj_fusion          vue d'ensemble, côté connecteur
  jj_fusion_face     de face, cadrans lisibles
  jj_fusion_detail   gros plan de la plaque_bossage et de la fiche

Le voyant est animé dans la scène (images clés, `SEQUENCE`), au rythme du firmware
(`esphome/temoin.yaml`) : l'ambre respire, le rouge clignote. La vidéo sort de `anim.py`.

Repère des maquettes : mur en y = 0, avant vers -Y, Z vers le haut. Celui de Fusion a son origine sur
la façade : on passe de l'un à l'autre par y - DEPTH. Cotes en mm.
"""
import json
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import cm_lib as L

SESSION, SEMAINE, RESET = 62, 38, "14:32"

SRC = L.DESIGN / "fusion" / "blender"
DEPTH = 40.0
GAUGE_Z = 8.0
PLUG_LEN = 54.0
BRIDE = 3.5            # épaisseur de la bride du LP-16 : la fiche vient en butée dessus
NEEDLE_Y = -9.3        # plan de l'aiguille dans le repère Fusion, 1,5 au-dessus de la face du cadran
FLOOR_Y = -7.65        # fond plein de la fenêtre du modèle GrabCAD
GLOW = {"ambre": 2.2, "rouge": 1.5}   # luminance de la légende à 100 % : AgX délave le rouge s'il est plus fort

FONT7 = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg", "7": "abc",
         "8": "abcdefg", "9": "abcdfg"}

# Animation : (couleur, nombre de cycles, durée d'un cycle en s, fonction phase -> niveau de 0 à 1).
FPS = 25
SEQUENCE = (("ambre", 2, 3.2, lambda p: 0.675 + 0.325 * math.cos(2 * math.pi * p)),
            ("rouge", 3, 1.0, lambda p: 1.0 if p < 0.5 else 0.0))


def timeline():
    """Une entrée par image : (couleur, niveau)."""
    out = []
    for state, n, period, level in SEQUENCE:
        frames = round(period * FPS)
        out += [(state, level(k / frames)) for _ in range(n) for k in range(frames)]
    return out


def _srgb(rgb):
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (v / 255 for v in rgb))


# ------------------------------------------------------------ corps de Fusion

class Modele:
    """Index et tableaux de l'export ; `objet` construit un objet Blender à partir de corps."""

    def __init__(self):
        self.idx = json.loads((SRC / "claudometre.json").read_text(encoding="utf-8"))
        nv, ni = self.idx["nv"], self.idx["ni"]
        raw = (SRC / "claudometre.bin").read_bytes()
        self.pos = np.frombuffer(raw, "<f4", nv * 3, 0).reshape(-1, 3)
        self.nor = np.frombuffer(raw, "<f4", nv * 3, nv * 12).reshape(-1, 3)
        self.tri = np.frombuffer(raw, "<u4", ni, nv * 24)
        self.corps = self.idx["corps"]

    def pose(self, occ):
        """Pose d'une occurrence, en mm, dans le repère des maquettes."""
        m = Matrix([self.idx["poses"][occ][k:k + 4] for k in (0, 4, 8, 12)])
        m.translation = m.translation * 10 + Vector((0, -DEPTH, 0))
        return m

    def objet(self, name, corps, mat, parent):
        pos, nor, tri, base = [], [], [], 0
        for c in corps:
            pos.append(self.pos[c["v0"]:c["v0"] + c["nv"]])
            nor.append(self.nor[c["v0"]:c["v0"] + c["nv"]])
            tri.append(self.tri[c["i0"]:c["i0"] + c["ni"]].astype(np.int64) - c["v0"] + base)
            base += c["nv"]
        pos = (np.concatenate(pos) + (0, -DEPTH, 0)) * L.MM
        nor = np.concatenate(nor)
        tri = np.concatenate(tri)
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(pos))
        me.vertices.foreach_set("co", pos.ravel())
        me.loops.add(len(tri))
        me.loops.foreach_set("vertex_index", tri)
        me.polygons.add(len(tri) // 3)
        me.polygons.foreach_set("loop_start", np.arange(0, len(tri), 3))
        me.update(calc_edges=True)
        me.shade_smooth()
        me.normals_split_custom_set_from_vertices(nor.tolist())  # Fusion sépare les sommets à chaque arête vive
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        return L.link(ob, parent)


def _materiaux(M):
    """Palette de jj_base, avec le sens d'impression réel de chaque pièce : couches le long de Y pour
    la coque, posée sur le dos, et le long de X pour la plaque de flanc, posée sur sa face d'appui."""
    kaki, usure = (0.075, 0.085, 0.035), (0.22, 0.22, 0.15)
    M["kaki_y"] = L.mat_worn("kaki_y", kaki, usure, amount=0.25, layer_axis="Y")
    M["kaki_x"] = L.mat_worn("kaki_x", kaki, usure, amount=0.25, layer_axis="X")
    M["noir_y"] = L.mat_pla("noir_y", (0.012, 0.012, 0.012), rough=0.55, layer_axis="Y")
    M["noir_x"] = L.mat_pla("noir_x", (0.012, 0.012, 0.012), rough=0.55, layer_axis="X")
    M["cadran_fond"] = L.mat_basic("cadran_fond", _srgb((20, 20, 19)), rough=0.6)
    M["cadran_zone"] = L.mat_basic("cadran_zone", _srgb((226, 70, 30)), rough=0.55)
    M["cadran_clair"] = L.mat_basic("cadran_clair", _srgb((236, 234, 226)), rough=0.55)
    M["aff_face"] = L.mat_basic("aff_face", (0.012, 0.012, 0.013), rough=0.3)
    M["legende"] = L.mat_basic("legende", (0.10, 0.10, 0.095), rough=0.5, emission=(1, 1, 1), strength=0.0)
    M["seg_jaune"] = L.mat_basic("seg_jaune", (1.0, 0.42, 0.0), rough=0.4, emission=(1.0, 0.40, 0.0), strength=1.0)
    M["aiguille_rouge"] = L.mat_basic("aiguille_rouge", (0.75, 0.025, 0.012), rough=0.4)
    M["etrier"] = L.mat_basic("etrier", (0.16, 0.16, 0.17), metallic=1.0, rough=0.55)
    M["lp16"] = L.mat_basic("lp16", (0.006, 0.006, 0.006), rough=0.5)  # nylon mat, reflet faible
    next(n for n in M["lp16"].node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Specular IOR Level"].default_value = 0.3


def _groupes(modele):
    """Répartit les corps en (nom d'objet, clé de matériau) ; `None` : traité à part."""
    groupes = {}
    for c in modele.corps:
        top, _, sous = c["occ"].partition("+")
        racine = top.rsplit(":", 1)[0]
        app = c["app"]
        if racine == "afficheur_TM1637_056":
            key = {"bloc": ("aff_bloc", "black"), "face": ("aff_face", "aff_face")}.get(c["part"])
        elif racine in ("coque", "visiere"):
            key = (racine, "kaki_y")
        elif racine == "platine":
            key = (racine, "noir_y")
        elif racine == "plaque_flanc":
            key = (racine, "noir_x")
        elif racine == "plaque_bossage":
            key = (racine, "kaki_x")
        elif racine == "voltmetre_SO-45":
            key = (f"so45_{top[-1]}_{'corps' if app == 'ABS (Black)' else 'bornes'}",
                   "black" if app == "ABS (Black)" else "steel")
        elif racine == "connecteur_LP-16_2poles":
            key = ("lp16_embase", "lp16")  # le STEP est gris clair, la vraie embase est noire
        elif racine == "visserie":
            key = ("visserie", "black_oxide")
        elif racine.startswith("plaquette_"):
            key = (f"{racine}_fond", "noir_y") if app == "PLA noir" else (f"{racine}_texte", "cadran_clair")
        elif racine == "claude":
            piece = sous.rsplit(":", 1)[0]
            mat = {"cadre": "kaki_y", "voile": "legende"}.get(piece, "noir_y")
            key = (f"temoin_{piece}", mat)
        elif racine.startswith("fond-jauge-"):
            piece = sous.rsplit(":", 1)[0]
            mat = {"fond": "cadran_fond", "zone": "cadran_zone"}.get(piece, "cadran_clair")
            key = (f"{racine}_{piece}", mat)
        else:
            raise KeyError(c["occ"])
        if key:
            groupes.setdefault(key, []).append(c)
    return groupes


def _segments_allumes(corps, text):
    """Répartit les segments en allumés / éteints, d'après leur position. `text` : « HH:MM »."""
    digits = text.replace(":", "")
    on, off = [], []
    for c in corps:
        x0, _, z0, x1, _, z1 = c["bbox"]
        cx, cz, dx, dz = (x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0
        if dx < 2 and dz < 2:  # points : ceux du milieu font le deux-points, les autres sont les décimales
            (on if abs(cx) < 0.5 and ":" in text else off).append(c)
            continue
        k = round((cx + 18.6) / 12.4)
        centre = -18.6 + 12.4 * k
        if dx > 5:
            lettre = "a" if cz > 15 else "d" if cz < 6 else "g"
        else:
            lettre = ("b" if cz > 11 else "c") if cx > centre else ("f" if cz > 11 else "e")
        (on if lettre in FONT7[digits[k]] else off).append(c)
    return on, off


# ------------------------------------------------------------ pièces ajoutées

def _so45(M, root, x, pct, label):
    """Ce que le modèle GrabCAD n'a pas : équipage mobile, aiguille noire à pointe rouge (photo de face,
    design/references/so45/voltmetre_face.jpg), vitre et vis du zéro. Origine sur l'axe de la jauge."""
    axe = L.empty(f"so45_{label}", (x, -3 - DEPTH, GAUGE_Z), root)
    pz = L.SO45["pivot_z"]
    y0 = FLOOR_Y + 3            # le fond de la fenêtre, depuis l'origine
    L._ring(f"so45_{label}_moyeu", [(0, y0 - 1.2), (2.75, y0 - 1.2), (2.75, y0), (0, y0)], M["brass"], axe, seg=48,
            loc=(0, 0, pz))
    L._ring(f"so45_{label}_pivot", [(0, y0 - 2.0), (0.9, y0 - 2.0), (0.9, y0 - 1.2), (0, y0 - 1.2)], M["brass_old"], axe,
            seg=24, loc=(0, 0, pz))
    for sx, w in ((-7.4, 5.2), (7.2, 4.0)):
        L.box(f"so45_{label}_etrier{sx}", (w, 0.5, 5.0), M["etrier"], axe, (sx, y0 - 0.25, pz - 0.5), bevel_mm=0.15)
    pivot = L.empty(f"aiguille_{label}", (0, NEEDLE_Y + 3, pz), axe)
    ln = L.SO45["needle_len"]
    coude = 0.6 * ln
    w = 0.3 - 0.2 * coude / ln
    L.mesh_obj(f"aiguille_{label}_noir", [(-0.45, 0, -2.5), (0.45, 0, -2.5), (0.3, 0, 0), (w, 0, coude), (-w, 0, coude),
                                          (-0.3, 0, 0)], [(0, 1, 2, 3, 4, 5)], M["black"], pivot)
    L.mesh_obj(f"aiguille_{label}_rouge", [(w, 0, coude), (0.1, 0, ln), (-0.1, 0, ln), (-w, 0, coude)], [(0, 1, 2, 3)],
               M["aiguille_rouge"], pivot)
    sweep = L.SO45["sweep_deg"]
    pivot.rotation_euler = (0, math.radians(-sweep / 2 + sweep * pct / 100.0), 0)
    wr, rf = L.SO45["window_r"] - 0.02, -9.3
    vitre = L._outward(L.lathe(f"so45_{label}_vitre", [(0, rf + 0.6), (wr, rf + 0.6), (wr, rf + 1.1), (0, rf + 1.1)],
                               M["glass"], axe, seg=96, sharp_deg=60), 60)
    vitre.visible_shadow = False
    L._ring(f"so45_{label}_zero", [(0, rf - 0.5), (3.5, rf - 0.5), (3.8, rf - 0.2), (3.8, rf), (0, rf)], M["black"], axe,
            seg=48, loc=(0, 0, -17.2))
    L.place(L.box(f"so45_{label}_fente", (5.6, 0.3, 0.8), M["engrave"], axe), (0, rf - 0.45, -17.2), (0, 35, 0))


def _fiche_et_cable(modele, M, root):
    """Fiche LP-16 de la série 5 sur l'embase, dans son axe, ergot vers le haut, puis le câble : il part
    dans l'axe de la fiche, passe par-dessus et tombe le long de la planche."""
    p = modele.pose("connecteur_LP-16_2poles:1")
    ax, ay, az = (p.col[k].to_3d() for k in range(3))
    bout = p.translation + az * BRIDE
    e = L.empty("lp16_fiche_pose", parent=root)
    e.matrix_local = Matrix.Translation(bout * L.MM) @ Matrix((ax, -az, ay)).transposed().to_4x4()
    lp16_fiche("lp16_fiche", {**M, "black": M["lp16"]}, (0, 0, 0), e)
    fin = bout + az * PLUG_LEN
    r = 26.0                                  # rayon de courbure : 5 fois le Ø du câble
    centre = fin + az * 10 - ay * r
    pts = [fin, fin + az * 10]
    for a in (60, 30, 0):
        pts.append(centre + Vector((r * math.cos(math.radians(a)), 0, r * math.sin(math.radians(a)))))
    x, y, z = pts[-1]
    pts += [Vector(v) for v in ((x + 0.5, y + 3, z - 45), (x - 1.5, -10, z - 130), (x + 1, -7, z - 240), (x, -6, -340))]
    L.rod("usb_cable_lp16", [tuple(v) for v in pts], 2.5, M["cable"], root, smooth=True)


def _vis_temoin(M, root):
    """Les 2 FHC du cadre du témoin, pas encore dans le design Fusion (x = ±21, tête à fleur)."""
    for sx in (-21, 21):
        e = L.empty(f"temoin_vis{sx}", (sx, -5.5 - DEPTH, -26), root)
        L._ring(f"temoin_vis{sx}_tete", [(0, 0), (3.1, 0), (1.5, 1.6), (0, 1.6)], M["black_oxide"], e, seg=48)
        L.lathe(f"temoin_vis{sx}_six_pans", [(0, -0.02), (1.15, -0.02), (1.15, 0), (0, 0)], M["black"], e, seg=6,
                sharp_deg=20)


def _anime_voyant(M):
    """Images clés du voyant, une par image : la scène se joue telle quelle dans Blender."""
    b = next(n for n in M["legende"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    force, teinte = b.inputs["Emission Strength"], b.inputs["Emission Color"]
    for f, (state, level) in enumerate(timeline(), start=1):
        glow = L.LAMP_GLOW[state]
        force.default_value = GLOW[state] * level
        force.keyframe_insert("default_value", frame=f)
        teinte.default_value = (*glow, 1)
        teinte.keyframe_insert("default_value", frame=f)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, len(timeline())
    sc.render.fps = FPS
    sc.frame_set(1)


def _lobes(ob, n, depth, r_min=9.0):
    """Écrou de presse-étoupe : n creux arrondis au-delà du rayon r_min."""
    for v in ob.data.vertices:
        r = math.hypot(v.co.x, v.co.z) / L.MM
        if r > r_min:
            a = math.atan2(v.co.z, v.co.x)
            k = (r - depth * max(0.0, math.cos(n * a)) ** 2) / r
            v.co.x *= k
            v.co.z *= k
    ob.data.update()


def lp16_fiche(name, M, loc, parent):
    """Fiche à presse-étoupe, branchée : Ø 27,2, 54 de long, clip sur le dessus."""
    root = L.empty(name, loc, parent)
    blk = M["black"]
    L._ring(f"{name}_corps", [(0, 0), (12.9, 0), (13.6, -0.7), (13.6, -22.0), (12.9, -26.5), (11.6, -29.7),
                              (0, -29.7)], blk, root, seg=96)
    L._ring(f"{name}_col", [(0, -29.7), (10.7, -29.7), (10.7, -37.7), (0, -37.7)], blk, root)
    ecrou = L._ring(f"{name}_ecrou", [(0, -37.7), (11.4, -37.7), (12.0, -38.4), (12.0, -50.5), (10.6, -53.0),
                                      (5.0, -54.0), (0, -54.0)], blk, root, seg=96)
    _lobes(ecrou, 6, 1.5)
    L.box(f"{name}_clip", (11, 15, 2.6), blk, root, (0, -14.5, 14.3), bevel_mm=0.6)
    for sx in (-1, 1):
        L.box(f"{name}_rainure{sx}", (0.5, 20, 1.5), M["engrave"], root, (13.5 * sx, -15, 0))
    return root


def _lumiere(side=1):
    """La maquette est éclairée pour la façade, depuis la gauche : on passe la
    lumière principale du côté du flanc regardé."""
    def aim(name, loc, target):
        ob = bpy.data.objects[name]
        ob.location = Vector(loc)
        ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()
    aim("key", (0.55 * side, -0.48, 0.40), (0.10 * side, 0, 0))
    aim("fill", (0.35 * side, -0.6, -0.35), (0, 0, 0))  # à gauche, le verre des cadrans la reflète


# ------------------------------------------------------------ scènes

def _scene(name, session=SESSION, semaine=SEMAINE, reset=RESET, lumiere=1.0):
    M = L.materials()
    _materiaux(M)
    L.wall(M)
    root = L.device(name)
    modele = Modele()
    for (nom, mat), corps in _groupes(modele).items():
        modele.objet(nom, corps, M[mat], root)
    on, off = _segments_allumes([c for c in modele.corps if c["part"] == "segment"], reset)
    modele.objet("aff_segments_on", on, M["seg_jaune"], root)
    modele.objet("aff_segments_off", off, M["seg_off"], root)
    _so45(M, root, -58.0, session, "session")
    _so45(M, root, 58.0, semaine, "semaine")
    _fiche_et_cable(modele, M, root)
    _vis_temoin(M, root)
    _anime_voyant(M)
    L.lights_and_world(strength=lumiere)
    _lumiere(1)
    return M, root


def jj_fusion():
    _scene("jj_fusion")
    L.camera((0.50, -0.47, 0.09), (0.058, -0.03, -0.012), lens=85, fstop=16)
    bpy.context.scene["no_fit"] = True  # le câble compte dans le cadrage


def jj_fusion_face():
    _scene("jj_fusion_face")
    L.camera((0.13, -0.50, 0.08), (0.0, -0.04, -0.005), lens=60, fstop=8)


def jj_fusion_soir():
    _scene("jj_fusion_soir", lumiere=0.22)
    bpy.data.worlds["world"].node_tree.nodes["Background"].inputs["Strength"].default_value = 0.15
    L.camera((0.13, -0.50, 0.08), (0.0, -0.04, -0.005), lens=60, fstop=8)


def jj_fusion_detail():
    _scene("jj_fusion_detail")
    L.camera((0.40, -0.25, 0.05), (0.127, -0.02, -0.012), lens=70, fstop=11)


BUILDERS = {f.__name__: f for f in (jj_fusion, jj_fusion_face, jj_fusion_soir, jj_fusion_detail)}
