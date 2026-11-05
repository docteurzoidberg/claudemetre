# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Assemble maquette/claudometre.glb, le modèle de la page éclatée : `uv run pack.py`.

Lit l'export complet de Fusion et les ajouts de Blender dans design/fusion/web/ (voir maquette/README.md),
range les corps en pièces, chacune avec son déplacement à l'éclaté, sa couleur et le groupe de la liste
de la page. Positions en entiers 16 bits et normales en 8 bits (KHR_mesh_quantization).

Repère de Fusion, en mm : origine sur la façade, X à droite, Z en haut, +Y vers le mur. La coque ne bouge
pas à l'éclaté : tout le reste sort vers l'avant ou sur les côtés.
"""
import json
import struct
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "design" / "fusion" / "web"
OUT = HERE / "claudometre.glb"
AXE = np.array((0.866, 0.0, 0.5))              # axe du LP-16, 30° vers le haut et l'extérieur
FLANC = 45.0


def y(v):
    return (0.0, float(v), 0.0)


def lp16(d):
    return tuple(float(a) for a in np.array((FLANC, 0, 0)) + AXE * d)


# pièce : (déplacement à l'éclaté, groupe de la liste, visserie ?, arêtes dessinées ?)
PIECES = {
    "coque": (y(0), "coque", False, True),
    "inserts_coque": (y(0), "coque", True, False),
    "clips": (y(-34), "clips", False, True),
    "carte": (y(-58), "carte", False, False),
    "afficheur": (y(-86), "afficheur", False, False),
    "vis_afficheur": (y(-72), "afficheur", True, False),
    "temoin_fond": (y(-80), "temoin", False, True),
    "temoin_boite": (y(-92), "temoin", False, True),
    "platine": (y(-110), "platine", False, True),
    "inserts_platine": (y(-110), "platine", True, False),
    "vis_platine": (y(-136), "platine", True, False),
    "temoin_voile": (y(-116), "temoin", False, False),
    "temoin_masque": (y(-122), "temoin", False, False),
    "temoin_cadre": (y(-130), "temoin", False, True),
    "vis_temoin": (y(-150), "temoin", True, False),
    "plaquettes": (y(-124), "plaquettes", False, False),
    "vis_plaquettes": (y(-146), "plaquettes", True, False),
    "visiere": (y(-134), "visiere", False, True),
    "so45": (y(-152), "jauges", False, True),
    "vis_so45": (y(-178), "jauges", True, False),
    "cadrans": (y(-188), "cadrans", False, False),
    "aiguilles": (y(-200), "jauges", False, False),
    "vitres": (y(-214), "jauges", False, True),
    "plaque_bossage": ((FLANC, 0.0, 0.0), "plaques", False, True),
    "inserts_bossage": ((FLANC, 0.0, 0.0), "connecteur", True, False),
    "vis_bossage": ((70.0, 0.0, 0.0), "plaques", True, False),
    "plaque_flanc": ((-FLANC, 0.0, 0.0), "plaques", False, True),
    "vis_flanc": ((-70.0, 0.0, 0.0), "plaques", True, False),
    "lp16": (lp16(28), "connecteur", False, True),
    "vis_lp16": (lp16(46), "connecteur", True, False),
    "fiche": (lp16(64), "connecteur", False, False),
}

# matériau : (couleur sRGB, rugosité, métal)
MATERIAUX = {
    "kaki": ("#5c623c", 0.65, 0.0),
    "noir": ("#242321", 0.8, 0.0),
    "noir_pla": ("#1e1e1d", 0.8, 0.0),
    "blanc": ("#ece9de", 0.6, 0.0),
    "abs": ("#141414", 0.42, 0.0),
    "acier": ("#a4a4aa", 0.42, 0.9),
    "acier_fonce": ("#55555a", 0.5, 0.9),
    "oxyde": ("#26262a", 0.42, 0.7),
    "laiton": ("#e8bd6a", 0.32, 1.0),
    "or": ("#e4bb5c", 0.3, 1.0),
    "cadran": ("#161615", 0.8, 0.0),
    "zone": ("#e2461e", 0.55, 0.0),
    "rouge": ("#c8200f", 0.45, 0.0),
    "masque": ("#0f0f0f", 0.8, 0.0),
    "legende": ("#f4f4f0", 0.5, 0.0),
    "aff_face": ("#121214", 0.3, 0.0),
    "seg_off": ("#2c2822", 0.6, 0.0),
    "seg_on": ("#2c2208", 0.5, 0.0),
    "circuit": ("#2a2b28", 0.45, 0.0),
    "bornier": ("#2f9e4f", 0.5, 0.0),
    "blindage": ("#b9ae9b", 0.4, 0.7),
    "lp16": ("#161616", 0.55, 0.0),
    "cable": ("#1b1b1b", 0.55, 0.0),
    "verre": ("#dfe7ea", 0.05, 0.0),
}
EMISSION = {"seg_on": "#ffba18"}


def lineaire(hexa):
    c = np.array([int(hexa[k:k + 2], 16) / 255 for k in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).round(4).tolist()


def tailles(c):
    x0, y0, z0, x1, y1, z1 = c["bbox"]
    return sorted((x1 - x0, y1 - y0, z1 - z0))


def centre(c):
    x0, y0, z0, x1, y1, z1 = c["bbox"]
    return (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2


def visserie(c, sous):
    x, _, _ = centre(c)
    if sous.startswith("insert"):
        return ("inserts_bossage" if x > 100 else "inserts_coque" if abs(x) >= 85 else "inserts_platine"), "laiton"
    if sous.startswith("vis_FHC"):
        return ("vis_lp16" if x > 100 else "vis_platine" if abs(x) >= 85 else "vis_plaquettes"), "oxyde"
    if sous.startswith("vis_CHC_M3x12"):
        return "vis_so45", "oxyde"
    if abs(x) < 90:
        return "vis_afficheur", "acier"
    return ("vis_bossage" if x > 0 else "vis_flanc"), "oxyde"


def carte(c, chemin):
    """La carte n'a qu'une couleur dans Fusion : couleurs d'après sa photo, selon le sous-ensemble et la taille."""
    s = tailles(c)
    sous = "+".join(chemin[1:])
    if "Screw Terminal" in sous:
        return "bornier" if s[2] > 6 else "acier"
    if "USB-C" in sous:
        return "acier"
    if "Terminal Block" in sous:
        return "abs" if s[2] > 50 else "or"
    if "Штыревой" in sous:
        return "or" if s[2] > 5 else "abs"
    if chemin[1].startswith("MDR076A"):
        return "circuit" if s[2] > 50 else "or"
    if len(chemin) > 2 and chemin[2].startswith("ESP32-S3-WROOM-1"):
        if s[2] > 50:
            return "circuit"
        if s[1] > 12:
            return "circuit" if s[0] < 1.2 else "blindage"
        return "or"
    return "abs"


def classe(c):
    """Pièce et matériau d'un corps, None pour le laisser de côté."""
    chemin = c["occ"].split("+")
    top = chemin[0].rsplit(":", 1)[0]
    sous = chemin[1].rsplit(":", 1)[0] if len(chemin) > 1 else ""
    if top == "extra":
        n = c["body"]
        if n.startswith("aiguille_"):
            return "aiguilles", "rouge" if n.endswith("rouge") else "abs"
        if n.startswith("temoin_vis"):
            return "vis_temoin", "oxyde"
        if n.startswith("usb_cable"):
            return "fiche", "cable"
        if n.startswith("lp16_fiche"):
            return "fiche", "lp16"
        if "_vitre" in n:
            return "vitres", "verre"
        if "_moyeu" in n or "_pivot" in n:
            return "so45", "laiton"
        if "_etrier" in n:
            return "so45", "acier_fonce"
        return "so45", "abs"
    if top == "coque":
        return "coque", "kaki"
    if top == "visiere":
        return "visiere", "kaki"
    if top == "plaque_bossage":
        return "plaque_bossage", "kaki"
    if top == "plaque_flanc":
        return "plaque_flanc", "noir"
    if top == "platine":
        return "platine", "noir"
    if top.startswith("clip_"):
        return "clips", "noir"
    if top == "voltmetre_SO-45":
        return "so45", "abs" if c["app"] == "ABS (Black)" else "acier"
    if top == "connecteur_LP-16_2poles":
        return "lp16", "lp16"
    if top.startswith("plaquette_"):
        return "plaquettes", "noir_pla" if c["app"] == "PLA noir" else "blanc"
    if top == "visserie":
        return visserie(c, sous)
    if top == "mrd076a_esp32_s3":
        return "carte", carte(c, chemin)
    if top == "claude":
        return {"cadre": ("temoin_cadre", "kaki"), "masque": ("temoin_masque", "masque"),
                "voile": ("temoin_voile", "legende"), "boite": ("temoin_boite", "noir"),
                "fond": ("temoin_fond", "noir")}[sous]
    if top.startswith("fond-jauge-"):
        return "cadrans", {"fond": "cadran", "zone": "zone"}.get(sous, "blanc")
    if top == "afficheur_TM1637_056":
        if c["part"] == "bloc":
            return "afficheur", "abs"
        if c["part"] == "face":
            return "afficheur", "aff_face"
        if c["part"] == "segment":
            return "afficheur", c["etat"]
        x0, y0, z0, x1, y1, z1 = c["bbox"]
        if y1 < 4.8 and abs(x0) < 25.2 and abs(x1) < 25.2:
            return None                        # à l'intérieur du bloc de l'afficheur
        r, g, b = c["rgb"] or (120, 120, 120)
        cle = f"#{r:02x}{g:02x}{b:02x}"
        MATERIAUX.setdefault(cle, (cle, 0.5, 0.0))
        return "afficheur", cle
    raise KeyError(c["occ"])


def segments(corps, text="14:32"):
    """Allume les segments de `text` (mêmes règles que `_segments_allumes` de variants6.py)."""
    font = {"1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg"}
    digits = text.replace(":", "")
    for c in corps:
        if c["part"] != "segment":
            continue
        x0, _, z0, x1, _, z1 = c["bbox"]
        cx, cz, dx, dz = (x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0
        if dx < 2 and dz < 2:
            c["etat"] = "seg_on" if abs(cx) < 0.5 else "seg_off"
            continue
        k = round((cx + 18.6) / 12.4)
        if dx > 5:
            lettre = "a" if cz > 15 else "d" if cz < 6 else "g"
        else:
            lettre = ("b" if cz > 11 else "c") if cx > -18.6 + 12.4 * k else ("f" if cz > 11 else "e")
        c["etat"] = "seg_on" if lettre in font[digits[k]] else "seg_off"


def index(stem):
    return json.loads((SRC / f"{stem}.json").read_text(encoding="utf-8"))


def charge(stem):
    idx = index(stem)
    nv, ni = idx["nv"], idx["ni"]
    raw = (SRC / f"{stem}.bin").read_bytes()
    pos = np.frombuffer(raw, "<f4", nv * 3, 0).reshape(-1, 3)
    nor = np.frombuffer(raw, "<f4", nv * 3, nv * 12).reshape(-1, 3)
    tri = np.frombuffer(raw, "<u4", ni, nv * 24)
    for c in idx["corps"]:
        yield c, pos[c["v0"]:c["v0"] + c["nv"]], nor[c["v0"]:c["v0"] + c["nv"]], \
            tri[c["i0"]:c["i0"] + c["ni"]].astype(np.int64) - c["v0"]


def primitive(morceaux):
    """Fusionne des corps, quantifie, soude. Rend (position, normale, indices, centre, demi-taille)."""
    pos, nor, tri, base = [], [], [], 0
    for p, n, t in morceaux:
        pos.append(p)
        nor.append(n)
        tri.append(t + base)
        base += len(p)
    pos, nor, tri = np.concatenate(pos), np.concatenate(nor), np.concatenate(tri)
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    mid = (lo + hi) / 2
    half = max(float((hi - lo).max()) / 2, 1e-3)    # même échelle sur les 3 axes : les normales restent justes
    q = np.round((pos - mid) / half * 32767).astype(np.int16)
    n = np.round(np.clip(nor, -1, 1) * 127).astype(np.int8)
    rows, inv = np.unique(np.hstack([q.astype(np.int32), n.astype(np.int32)]), axis=0, return_inverse=True)
    tri = inv.reshape(-1)[tri].reshape(-1, 3)
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    return rows[:, :3].astype(np.int16), rows[:, 3:].astype(np.int8), tri.ravel(), mid, half


class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.views, self.accessors = [], []

    def vue(self, data, stride=None, target=34962):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data), "target": target}
        if stride:
            v["byteStride"] = stride
        self.bin += data
        self.views.append(v)
        return len(self.views) - 1

    def attributs(self, q, n, tri):
        pad = np.zeros((len(q), 4), np.int16)
        pad[:, :3] = q
        pos = self.vue(pad.tobytes(), 8)
        pad = np.zeros((len(n), 4), np.int8)
        pad[:, :3] = n
        nor = self.vue(pad.tobytes(), 4)
        ind, kind = (tri.astype(np.uint16), 5123) if len(q) < 65535 else (tri.astype(np.uint32), 5125)
        idx = self.vue(ind.tobytes(), None, 34963)
        a = len(self.accessors)
        self.accessors += [
            {"bufferView": pos, "componentType": 5122, "normalized": True, "count": len(q), "type": "VEC3",
             "min": q.min(axis=0).tolist(), "max": q.max(axis=0).tolist()},
            {"bufferView": nor, "componentType": 5120, "normalized": True, "count": len(n), "type": "VEC3"},
            {"bufferView": idx, "componentType": kind, "count": len(tri), "type": "SCALAR"},
        ]
        return a


def main():
    tout = list(charge("claudometre")) + list(charge("extras"))
    segments([c for c, *_ in tout])
    groupes = {}
    for c, p, n, t in tout:
        cle = classe(c)
        if cle is None:
            continue
        groupes.setdefault(cle, []).append((p, n, t))

    glb = Glb()
    noms = sorted({m for _, m in groupes})
    materials = []
    for m in noms:
        couleur, rugosite, metal = MATERIAUX[m]
        d = {"name": m, "pbrMetallicRoughness": {"baseColorFactor": [*lineaire(couleur), 0.05 if m == "verre" else 1.0],
                                                 "roughnessFactor": rugosite, "metallicFactor": metal}}
        if m == "verre":
            d["alphaMode"] = "BLEND"
        if m in EMISSION:
            d["emissiveFactor"] = [round(v * 0.85, 4) for v in lineaire(EMISSION[m])]
        materials.append(d)

    nodes = [{"name": "claudometre", "children": []}]
    meshes = []
    for piece, (offset, groupe, vis, aretes) in PIECES.items():
        enfants = []
        for (pc, m), morceaux in groupes.items():
            if pc != piece:
                continue
            q, n, tri, mid, half = primitive(morceaux)
            a = glb.attributs(q, n, tri)
            meshes.append({"primitives": [{"attributes": {"POSITION": a, "NORMAL": a + 1}, "indices": a + 2,
                                           "material": noms.index(m)}]})
            nodes.append({"mesh": len(meshes) - 1, "translation": [float(v) for v in mid], "scale": [half] * 3})
            enfants.append(len(nodes) - 1)
        if not enfants:
            raise SystemExit(f"pièce vide : {piece}")
        nodes.append({"name": piece, "children": enfants,
                      "extras": {"offset": list(offset), "groupe": groupe, "vis": vis, "aretes": aretes}})
        nodes[0]["children"].append(len(nodes) - 1)

    doc = {"asset": {"version": "2.0", "generator": "maquette/pack.py",
                     "extras": {"version": index("claudometre")["version"]}}, "scene": 0, "scenes": [{"nodes": [0]}],
           "extensionsUsed": ["KHR_mesh_quantization"], "extensionsRequired": ["KHR_mesh_quantization"],
           "nodes": nodes, "meshes": meshes, "materials": materials, "accessors": glb.accessors,
           "bufferViews": glb.views, "buffers": [{"byteLength": len(glb.bin)}]}
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    glb.bin += b"\0" * (-len(glb.bin) % 4)
    total = 12 + 8 + len(js) + 8 + len(glb.bin)
    with OUT.open("wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(glb.bin), 0x004E4942) + glb.bin)
    tris = sum(a["count"] for a in glb.accessors if a["type"] == "SCALAR") // 3
    print(f"{OUT.name} : {total / 1e6:.1f} Mo, {len(PIECES)} pièces, {len(meshes)} maillages, {tris} triangles")


if __name__ == "__main__":
    main()
